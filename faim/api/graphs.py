# =============================================================================
# FAIM — GOLD EDITION (COMMERCIAL / INDUSTRIAL PRODUCTION)
# -----------------------------------------------------------------------------
# File: faim/api/graphs.py
# Purpose:
#   - Graph introspection endpoints for FAIM Lab UI (FIG view, inspector, metrics)
#   - Step-3 Retrieval Policy: retrieval preview endpoint (facts-first, noise-last)
#   - Step-4 UI-safe endpoints: stable Node schema + Galaxy views (additive, no breaks)
#
# HARD RULES:
#   1) DO NOT remove existing endpoints once shipped.
#   2) Additive evolution only (aliases/v2 endpoints), so old UI keeps working.
#   3) Snapshot endpoints MUST reflect real writes immediately (A-LIFE-1 strict evidence).
#
# Key Fix (why your A-LIFE-1 was failing):
#   - Your /snapshot (and /cluster_map) were returning an empty/invalid shape (often a bare list),
#     or reading from the wrong in-memory registry instead of the persistent store.
#   - This file makes the persistent store the SOURCE OF TRUTH for snapshot/cluster_map,
#     with a safe registry fallback only if the store is unavailable.
# =============================================================================

from __future__ import annotations

import importlib.util
import io
import re
import zipfile
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

# --- Shared API state (IMPORTANT):
# We import the module (not individual names) so this file survives slight state.py variants.
# expected to expose: NODE_STORE / iter_nodes_from_store / count_nodes_from_store / GRAPH_REGISTRY
from faim.api import state as S
from faim.api.auth import verify_graph_access
from faim.api.events import emit_fig_delta

# --- Models (stable API contract)
from faim.api.models import (
    GraphMetrics,
    GraphSubgraph,
    IngestFileResult,
    IngestResponse,
    LineageModel,
    NeighborInfo,
    NodeDetail,
    NodeScanItem,
    VectorStats,
)

# --- Engine views/adapters (existing surface — keep)
from faim.engine.adapter import (
    format_node_for_ui,
    format_subgraph_for_ui,
    virtual_degree_distribution,
    virtual_neighborhood,
    virtual_parent_lineage,
    virtual_scan_nodes,
    virtual_subgraph_bfs,
    virtual_vector_stats,
)
from faim.engine.interface import add_fragment, get_node_detail

# --- Retrieval debug
from faim.retrieve.context import naive_used_nodes

try:
    from faim.engine.adapter import virtual_compute_metrics as _virtual_compute_metrics
except Exception:
    _virtual_compute_metrics = None

router = APIRouter(prefix="/graphs", tags=["Graphs"], dependencies=[Depends(verify_graph_access)])

MAX_INGEST_BYTES = 20 * 1024 * 1024
DEFAULT_CHUNK_CHARS = 4000

# =============================================================================
# SECTION A — API SCHEMAS (Stable shapes for UI + Acceptance)
# =============================================================================


class GraphSnapshot(BaseModel):
    # NOTE: A-LIFE-1 expects a dict with keys: nodes + links (not a bare list).
    graph_id: str
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    links: List[Dict[str, Any]] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)


class AddFragmentPayload(BaseModel):
    text: Optional[str] = None


# =============================================================================
# SECTION B — HARDENED COERCION HELPERS (No 500s, deterministic)
# =============================================================================


def _clamp_int(v: Any, lo: int, hi: int, default: int) -> int:
    try:
        x = int(v)
    except Exception:
        return default
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def _as_str(v: Any) -> str:
    if v is None:
        return ""
    try:
        return str(v)
    except Exception:
        return ""


def _as_float(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return default
        try:
            return float(s)
        except Exception:
            return default
    try:
        return float(v)  # type: ignore[arg-type]
    except Exception:
        return default


def _as_int(v: Any, default: int = 0) -> int:
    if v is None:
        return default
    try:
        return int(v)
    except Exception:
        return default


def _coerce_neighbor(d: Dict[str, Any]) -> Dict[str, Any]:
    raw_id = d.get("id")
    raw_dist = d.get("distance", d.get("score", d.get("sim", d.get("weight"))))
    return {"id": _as_str(raw_id), "distance": _as_float(raw_dist, default=0.0)}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _chunk_text(text: str, max_chars: int) -> List[str]:
    if max_chars <= 0:
        return [text] if text else []
    parts = re.findall(r"\S+\s*", text)
    if not parts:
        return [text] if text else []
    out: List[str] = []
    buf = ""
    for p in parts:
        if buf and len(buf) + len(p) > max_chars:
            out.append(buf.strip())
            buf = p
        else:
            buf += p
    if buf.strip():
        out.append(buf.strip())
    return out


def _is_text_file(name: str, content_type: str) -> bool:
    if name.endswith((".txt", ".md", ".json")):
        return True
    return content_type.startswith("text/") or content_type == "application/json"


def _extract_docx_text(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        with zf.open("word/document.xml") as f:
            xml = f.read()
    try:
        from xml.etree import ElementTree as ET
    except Exception:
        return ""
    try:
        root = ET.fromstring(xml)
    except Exception:
        return ""

    texts: List[str] = []
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            texts.append(node.text)
    return "\n".join(texts)


def _extract_pdf_text(data: bytes) -> str:
    if importlib.util.find_spec("pypdf"):
        try:
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(data))
            return "\n".join([page.extract_text() or "" for page in reader.pages])
        except Exception:
            return ""
    if importlib.util.find_spec("pdfminer"):
        try:
            from pdfminer.high_level import extract_text

            return extract_text(io.BytesIO(data)) or ""
        except Exception:
            return ""
    return ""


# =============================================================================
# SECTION C — STORE + REGISTRY ACCESS (Source of truth = persistent store)
# =============================================================================


def _maybe_ensure_registry_loaded(graph_id: str) -> None:
    """
    Optional: if your state.py implements ensure_registry_loaded(), call it.
    This keeps any legacy registry-based views from returning empty.
    """
    try:
        fn = getattr(S, "ensure_registry_loaded", None)
        if callable(fn):
            fn(graph_id)  # type: ignore[misc]
    except Exception:
        return


def _iter_nodes_store(graph_id: str) -> Iterable[Any]:
    """
    Robustly iterate nodes from the persistent store if present.
    Works across multiple state.py variants.
    """
    # Preferred: iter_nodes_from_store(graph_id: str)
    try:
        fn = getattr(S, "iter_nodes_from_store", None)
        if callable(fn):
            return fn(graph_id)  # type: ignore[misc]
    except Exception:
        pass

    # Fallback: NODE_STORE.iter_nodes(_gid(graph_id))
    try:
        store = getattr(S, "NODE_STORE", None)
        gid_fn = getattr(S, "_gid", None)
        if store is not None and callable(getattr(store, "iter_nodes", None)) and callable(gid_fn):
            return store.iter_nodes(gid_fn(graph_id))  # type: ignore[misc]
    except Exception:
        pass

    # If store is not available, return empty (registry fallback handled separately)
    return []


def _count_nodes_store(graph_id: str) -> int:
    try:
        fn = getattr(S, "count_nodes_from_store", None)
        if callable(fn):
            return int(fn(graph_id))  # type: ignore[misc]
    except Exception:
        pass

    # Fallback: count by iter
    try:
        return int(sum(1 for _ in _iter_nodes_store(graph_id)))
    except Exception:
        return 0


def _registry_nodes(graph_id: str) -> List[Any]:
    """
    Registry is NOT the source of truth, but we keep it as a compatibility fallback.
    """
    try:
        reg = getattr(S, "GRAPH_REGISTRY", None)
        gid_fn = getattr(S, "_gid", None)
        if reg is None or not callable(getattr(reg, "get", None)) or not callable(gid_fn):
            return []
        g = reg.get(gid_fn(graph_id))  # type: ignore[misc]
        if g is None:
            return []
        nodes_map = getattr(g, "nodes", {}) or {}
        return list(nodes_map.values())
    except Exception:
        return []


# =============================================================================
# SECTION D — NODE FIELD NORMALIZATION (Works with multiple NodeRecord shapes)
# =============================================================================


def _node_id_any(n: object) -> str:
    # NodeRecord variants: .id, .node_id
    return _as_str(getattr(n, "id", None) or getattr(n, "node_id", None))


def _ensure_compound_id(graph_id: str, nid: str) -> str:
    """
    Acceptance uses compound ids like: U:<hash>:<seq>:<hash8>
    If some store variant gives only the suffix, prefix it deterministically.
    """
    s = (nid or "").strip()
    if not s:
        return ""
    if s.startswith(f"{graph_id}:"):
        return s
    # If it already looks like a compound id from another graph, keep it as-is.
    if ":" in s and s.startswith(("U:", "MAIN:", "G:", "P:", "S:")):
        return s
    return f"{graph_id}:{s}"


def _children_any(n: object) -> List[str]:
    ch = getattr(n, "children", None) or []
    out: List[str] = []
    if isinstance(ch, list):
        for x in ch:
            sx = _as_str(x)
            if sx:
                out.append(sx)
    return out


def _parents_any(n: object) -> List[Tuple[str, float]]:
    """
    parents may be list[ParentRef] or list[dict] depending on version.
    Normalize to (parent_id, fraction).
    """
    pp = getattr(n, "parents", None) or []
    out: List[Tuple[str, float]] = []
    if not isinstance(pp, list):
        return out

    for p in pp:
        if p is None:
            continue

        if isinstance(p, dict):
            pid = _as_str(p.get("parent_id") or p.get("id") or "")
            w = _as_float(p.get("fraction", 1.0), default=1.0)
        else:
            pid = _as_str(getattr(p, "parent_id", None) or getattr(p, "id", None) or "")
            w = _as_float(getattr(p, "fraction", 1.0), default=1.0)

        if pid:
            out.append((pid, w))
    return out


def _node_label_any(n: object, fallback: str) -> str:
    # Try common fields; keep deterministic
    for attr in ("label", "title", "text", "value"):
        v = getattr(n, attr, None)
        sv = _as_str(v).strip()
        if sv:
            return sv
    return fallback


def _node_kind_any(n: object) -> str:
    # Try common fields; keep deterministic
    for attr in ("kind", "type"):
        v = getattr(n, attr, None)
        sv = _as_str(v).strip()
        if sv:
            return sv
    # Some builds may store flags dict
    flags = getattr(n, "flags", None)
    if isinstance(flags, dict):
        k = _as_str(flags.get("kind")).strip()
        if k:
            return k
    return "node"


# =============================================================================
# SECTION E — SNAPSHOT BUILDER (This is what fixes A-LIFE-1)
# =============================================================================


def _build_snapshot_from_store(graph_id: str) -> GraphSnapshot:
    """
    Store-backed snapshot (SOURCE OF TRUTH).
    Always returns {graph_id,nodes,links,meta} with deterministic ordering.
    """
    nodes_raw = list(_iter_nodes_store(graph_id))

    # Deterministic ordering by normalized id
    nodes_raw.sort(key=lambda n: _ensure_compound_id(graph_id, _node_id_any(n)))

    out_nodes: List[Dict[str, Any]] = []
    out_links: List[Dict[str, Any]] = []

    for n in nodes_raw:
        nid_raw = _node_id_any(n)
        nid = _ensure_compound_id(graph_id, nid_raw)
        if not nid:
            continue

        parents = _parents_any(n)
        children = _children_any(n)

        out_nodes.append(
            {
                "id": nid,
                "label": _node_label_any(n, nid),
                "kind": _node_kind_any(n),
                "degree": int(len(parents) + len(children)),
                "created_at": _as_float(getattr(n, "created_at", None), default=0.0),
                "last_used_at": _as_float(getattr(n, "last_used_at", None), default=0.0),
                "use_count": int(getattr(n, "use_count", 0) or 0),
                "preview": _as_str(getattr(n, "preview", "")),
            }
        )

        # Parent inheritance edges
        for pid_raw, w in parents:
            pid = _ensure_compound_id(graph_id, pid_raw)
            if pid:
                out_links.append(
                    {"source": pid, "target": nid, "rel": "inherits", "weight": float(w)}
                )

        # Child edges
        for cid_raw in children:
            cid = _ensure_compound_id(graph_id, cid_raw)
            if cid:
                out_links.append({"source": nid, "target": cid, "rel": "child", "weight": 1.0})

    # Deterministic link order + de-dupe
    out_links.sort(
        key=lambda e: (_as_str(e.get("source")), _as_str(e.get("target")), _as_str(e.get("rel")))
    )
    seen: set[Tuple[str, str, str]] = set()
    deduped: List[Dict[str, Any]] = []
    for e in out_links:
        k = (_as_str(e.get("source")), _as_str(e.get("target")), _as_str(e.get("rel")))
        if not k[0] or not k[1] or not k[2]:
            continue
        if k in seen:
            continue
        seen.add(k)
        deduped.append(e)

    return GraphSnapshot(
        graph_id=graph_id,
        nodes=out_nodes,
        links=deduped,
        meta={"source": "store", "node_count": len(out_nodes), "link_count": len(deduped)},
    )


def _build_snapshot(graph_id: str) -> GraphSnapshot:
    """
    Primary snapshot used by /snapshot and /cluster_map.
    - Prefer STORE (fixes A-LIFE-1).
    - If store has nothing but registry might, fallback (compat only).
    """
    _maybe_ensure_registry_loaded(graph_id)

    snap = _build_snapshot_from_store(graph_id)
    if snap.nodes or snap.links:
        return snap

    # Registry fallback (only if store truly empty/unavailable)
    reg_nodes = _registry_nodes(graph_id)
    if not reg_nodes:
        return GraphSnapshot(graph_id=graph_id, nodes=[], links=[], meta={"source": "empty"})

    # Build minimal from registry
    nodes_out: List[Dict[str, Any]] = []
    links_out: List[Dict[str, Any]] = []

    reg_nodes.sort(key=lambda n: _ensure_compound_id(graph_id, _node_id_any(n)))
    for n in reg_nodes:
        nid = _ensure_compound_id(graph_id, _node_id_any(n))
        if not nid:
            continue
        children = _children_any(n)
        nodes_out.append({"id": nid, "label": _node_label_any(n, nid), "kind": _node_kind_any(n)})
        for c in sorted(children):
            cid = _ensure_compound_id(graph_id, c)
            if cid:
                links_out.append({"source": nid, "target": cid, "rel": "child", "weight": 1.0})

    links_out.sort(
        key=lambda e: (_as_str(e.get("source")), _as_str(e.get("target")), _as_str(e.get("rel")))
    )
    return GraphSnapshot(
        graph_id=graph_id,
        nodes=nodes_out,
        links=links_out,
        meta={"source": "registry", "node_count": len(nodes_out), "link_count": len(links_out)},
    )


# =============================================================================
# SECTION F — UI STABLE NODE SHAPE (Step-4 additive endpoints)
# =============================================================================


def _stable_node_from_detail(d: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": _as_str(d.get("id", "")),
        "label": _as_str(d.get("label", "")),
        "kind": _as_str(d.get("kind", "memory")) or "memory",
        "degree": int(d.get("degree", 0) or 0),
        "created_at": d.get("created_at", None),
        "last_used_at": d.get("last_used_at", None),
        "use_count": int(d.get("use_count", 0) or 0),
        "preview": _as_str(d.get("preview", "")),
    }


def _galaxy_of_kind(kind: str) -> str:
    k = (kind or "").strip().lower()
    if k == "fact":
        return "facts"
    if k in ("doc", "document"):
        return "documents"
    if k in ("user_chat", "chat_user"):
        return "user"
    if k in ("assistant_chat", "chat_assistant"):
        return "assistant"
    return "memory"


def _scan_nodes_any(graph_id: str, limit: int, order: str) -> List[Any]:
    """
    Prefer virtual_scan_nodes (fast index if present),
    but fallback to STORE (source of truth) if virtual returns empty.
    """
    lim = _clamp_int(limit, 1, 1000, 250)
    ord_norm = (order or "id").strip().lower()

    # 1) Try virtual
    try:
        out = virtual_scan_nodes(graph_id, lim, ord_norm)
        if out:
            return out
    except Exception:
        pass

    # 2) Store fallback
    try:
        nodes = list(_iter_nodes_store(graph_id))
        if ord_norm == "recent":
            nodes.sort(
                key=lambda n: _as_float(getattr(n, "last_used_at", 0.0), default=0.0), reverse=True
            )
        else:
            nodes.sort(key=lambda n: _ensure_compound_id(graph_id, _node_id_any(n)))
        return nodes[:lim]
    except Exception:
        return []


# =============================================================================
# SECTION G — ENDPOINTS (KEEP SURFACE, FIX SNAPSHOT SHAPE)
# =============================================================================


# -----------------------------------------------------------------------------
# 0) RETRIEVAL PREVIEW (Step-3 debug endpoint) — KEEP COMPAT
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/retrieve_preview")
def api_retrieve_preview(
    graph_id: str,
    query: str = Query(
        ...,
        min_length=1,
        max_length=800,
        description="Preview retrieval policy (facts-first, noise-last) without calling LLM",
    ),
    k: int = Query(8, ge=1, le=64),
):
    q = (query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="query is required")
    kk = _clamp_int(k, 1, 64, 8)
    used_nodes, ctx_text = naive_used_nodes(graph_id, q, k=kk)
    return {
        "graph_id": graph_id,
        "query": q,
        "k": kk,
        "used_nodes": used_nodes,
        "ctx_text": ctx_text,
    }


# -----------------------------------------------------------------------------
# 1) SUBGRAPH (centered view) — ORIGINAL (DO NOT BREAK)
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/subgraph/{node_id}", response_model=GraphSubgraph)
def api_subgraph(graph_id: str, node_id: str, depth: int = 2):
    sg = virtual_subgraph_bfs(graph_id, node_id, depth)
    formatted = format_subgraph_for_ui(sg, mode="A")  # A = minimal nodes for FIG
    return GraphSubgraph(**formatted)


@router.get("/{graph_id}/recent-used-nodes")
def recent_used_nodes(graph_id: str, limit: int = 20):
    # keep existing surface
    from faim.engine.interface import get_recent_used_nodes

    return get_recent_used_nodes(graph_id, limit)


# -----------------------------------------------------------------------------
# 2) GLOBAL NODE SCAN — ORIGINAL (DO NOT BREAK)
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/nodes", response_model=list[NodeScanItem])
def api_scan_nodes(graph_id: str, limit: int = 250, order: str = "id"):
    nodes = _scan_nodes_any(graph_id, limit, order)
    out: List[NodeScanItem] = []
    for n in nodes:
        nid = _ensure_compound_id(graph_id, _node_id_any(n))
        if not nid:
            continue
        deg = int(len(_parents_any(n)) + len(_children_any(n)))
        out.append(NodeScanItem(id=nid, degree=deg))
    return out


# -----------------------------------------------------------------------------
# 2A) SNAPSHOT — CRITICAL (A-LIFE-1 strict evidence)  ✅ FIXED
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/snapshot", response_model=GraphSnapshot)
def api_snapshot(graph_id: str) -> GraphSnapshot:
    # Always store-backed shape: {graph_id, nodes, links, meta}
    return _build_snapshot(graph_id)


# -----------------------------------------------------------------------------
# 2B) GLOBAL NODE LIST (Step-4 stable UI objects) — NEW (ADDITIVE)
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/nodes_ui")
def api_nodes_ui(
    graph_id: str,
    limit: int = Query(250, ge=1, le=1000),
    order: str = Query("id", min_length=1, max_length=32),
    galaxy: Optional[str] = Query(None, description="facts|documents|user|assistant|memory"),
):
    lim = _clamp_int(limit, 1, 1000, 250)
    raw_nodes = _scan_nodes_any(graph_id, lim, order)

    out_nodes: List[Dict[str, Any]] = []
    dropped_missing = 0
    galaxy_norm = (galaxy or "").strip().lower() or None

    for n in raw_nodes:
        nid = _ensure_compound_id(graph_id, _node_id_any(n))
        if not nid:
            continue

        # Prefer engine detail (richer), fallback to store record fields
        detail = None
        try:
            detail = get_node_detail(graph_id, nid)
        except Exception:
            detail = None

        if detail is None:
            # fallback: build minimal stable from the record
            parents = _parents_any(n)
            children = _children_any(n)
            sn = {
                "id": nid,
                "label": _node_label_any(n, nid),
                "kind": _node_kind_any(n),
                "degree": int(len(parents) + len(children)),
                "created_at": _as_float(getattr(n, "created_at", None), default=0.0),
                "last_used_at": _as_float(getattr(n, "last_used_at", None), default=0.0),
                "use_count": int(getattr(n, "use_count", 0) or 0),
                "preview": _as_str(getattr(n, "preview", "")),
            }
        else:
            sn = _stable_node_from_detail(detail)

        if galaxy_norm is not None and _galaxy_of_kind(_as_str(sn.get("kind", ""))) != galaxy_norm:
            continue

        out_nodes.append(sn)

    return {
        "graph_id": graph_id,
        "nodes": out_nodes,
        "meta": {
            "limit": lim,
            "order": order,
            "galaxy": galaxy_norm,
            "dropped_missing": dropped_missing,
        },
    }


# -----------------------------------------------------------------------------
# 3) NODE DETAIL — ORIGINAL (DO NOT BREAK)
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/node/{node_id}", response_model=NodeDetail)
def api_node_detail(graph_id: str, node_id: str):
    raw = get_node_detail(graph_id, node_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="Node not found")
    formatted = format_node_for_ui(raw, mode="B")  # B = inspector
    return NodeDetail(**formatted)


# -----------------------------------------------------------------------------
# 3B) NODE DETAIL UI — NEW (ADDITIVE)
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/node_ui/{node_id}")
def api_node_detail_ui(graph_id: str, node_id: str, lineage_depth: int = 10):
    raw = get_node_detail(graph_id, node_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="Node not found")
    lineage = virtual_parent_lineage(graph_id, node_id, depth=_clamp_int(lineage_depth, 1, 100, 10))
    return {**raw, "stable": _stable_node_from_detail(raw), "lineage": lineage}


# -----------------------------------------------------------------------------
# 4) METRICS — ORIGINAL (but now consistent with store)
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# 4) METRICS — ENGINE-SOURCE (Golden Edition)
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/metrics", response_model=GraphMetrics)
def api_metrics(graph_id: str):
    """
    Golden Edition:
    - Reads metrics from the canonical FAIM engine store (not state.py shims).
    - Keeps the endpoint contract identical.
    - Produces stable numbers for UI + REST refresh loops.
    """
    try:
        # Import locally to avoid circular-import risks.
        from faim.engine.interface import get_metrics as _engine_get_metrics  # type: ignore

        m = _engine_get_metrics(graph_id) or {}
    except Exception:
        m = {}

    # ---- Normalize fields (robust across versions) --------------------------
    def _num(x, default=0.0):
        try:
            return float(x)
        except Exception:
            return float(default)

    node_count = int(_num(m.get("node_count", m.get("nodes", 0)), 0))
    edge_count = int(_num(m.get("edge_count", 0), 0))

    compression_ratio = _num(m.get("compression_ratio", m.get("cr", 0.0)), 0.0)
    redundancy = _num(m.get("redundancy", 0.0), 0.0)
    drift = _num(m.get("drift", 0.0), 0.0)

    raw_bytes = int(_num(m.get("raw_bytes", m.get("raw", 0.0)), 0.0))
    faim_bytes = int(
        _num(
            m.get("faim_bytes", m.get("vector_bytes", m.get("processed_bytes", 0.0))),
            0.0,
        )
    )

    lat = m.get("latency") or {}

    # Backend can evolve; accept any of these:
    # - retrieve_p50_ms / retrieve_p95_ms (flat)
    # - latency.retrieve_p50_ms / latency.retrieve_p95_ms
    # - latency.p50 / latency.p95
    retrieve_p50_ms = _num(
        m.get(
            "retrieve_p50_ms", lat.get("retrieve_p50_ms", lat.get("p50", lat.get("p50_ms", 0.0)))
        ),
        0.0,
    )
    retrieve_p95_ms = _num(
        m.get(
            "retrieve_p95_ms", lat.get("retrieve_p95_ms", lat.get("p95", lat.get("p95_ms", 0.0)))
        ),
        0.0,
    )

    return GraphMetrics(
        node_count=node_count,
        edge_count=edge_count,
        compression_ratio=compression_ratio,
        redundancy=redundancy,
        drift=drift,
        retrieve_p50_ms=retrieve_p50_ms,
        retrieve_p95_ms=retrieve_p95_ms,
        raw_bytes=raw_bytes,
        faim_bytes=faim_bytes,
    )


# -----------------------------------------------------------------------------
# 5) VECTOR STATS — ORIGINAL
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/node/{node_id}/vector_stats", response_model=VectorStats)
def api_vector_stats_route(graph_id: str, node_id: str):
    stats = virtual_vector_stats(graph_id, node_id)
    if not isinstance(stats, dict):
        raise HTTPException(status_code=404, detail="Vector missing")

    required = ("norm", "mean", "std", "min", "max")
    if any(k not in stats or stats[k] is None for k in required):
        raise HTTPException(status_code=404, detail="Vector missing")

    try:
        return VectorStats(
            norm=float(stats["norm"]),
            mean=float(stats["mean"]),
            std=float(stats["std"]),
            min=float(stats["min"]),
            max=float(stats["max"]),
        )
    except Exception as err:
        raise HTTPException(status_code=404, detail="Vector stats unavailable") from err


# -----------------------------------------------------------------------------
# 6) ANN NEIGHBORS — ORIGINAL
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/node/{node_id}/neighbors", response_model=list[NeighborInfo])
def api_neighbors(graph_id: str, node_id: str, k: int = 10):
    kk = _clamp_int(k, 1, 256, 10)

    try:
        neighbors_raw = virtual_neighborhood(graph_id, node_id, kk)
    except Exception:
        neighbors_raw = []

    if not neighbors_raw:
        return []

    out: List[NeighborInfo] = []
    for item in neighbors_raw:
        if not isinstance(item, dict):
            continue
        nn = _coerce_neighbor(item)
        if not nn["id"]:
            continue
        out.append(NeighborInfo(**nn))
    return out


# -----------------------------------------------------------------------------
# 7) LINEAGE TRACE — ORIGINAL
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/node/{node_id}/lineage", response_model=LineageModel)
def api_lineage(graph_id: str, node_id: str, depth: int = 10):
    dd = _clamp_int(depth, 1, 200, 10)
    lineage = virtual_parent_lineage(graph_id, node_id, dd)
    return LineageModel(lineage=lineage)


# -----------------------------------------------------------------------------
# 8) DEGREE DISTRIBUTION — ORIGINAL
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/degree_distribution")
def api_degree_distribution(graph_id: str):
    return virtual_degree_distribution(graph_id)


# -----------------------------------------------------------------------------
# 9) CLUSTER MAP — ORIGINAL NAME (keep) ✅ now returns correct shape
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/cluster_map", response_model=GraphSnapshot)
def api_cluster_map(graph_id: str) -> GraphSnapshot:
    # For P1/P2: cluster_map is the full snapshot (store-backed).
    return _build_snapshot(graph_id)


# -----------------------------------------------------------------------------
# 9A) CLUSTER GRAPH — LEGACY ALIAS (DO NOT REMOVE if older UI uses it)
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/cluster_graph")
def api_cluster_graph(graph_id: str) -> Dict[str, Any]:
    snap = _build_snapshot(graph_id)
    return snap.model_dump()


# -----------------------------------------------------------------------------
# 9B) GALAXIES — NEW (ADDITIVE)
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/galaxies")
def api_galaxies(graph_id: str, sample: int = Query(600, ge=50, le=5000)):
    samp = _clamp_int(sample, 50, 5000, 600)

    raw_nodes = _scan_nodes_any(graph_id, samp, "id")
    counts: Dict[str, int] = {"facts": 0, "documents": 0, "user": 0, "assistant": 0, "memory": 0}

    for n in raw_nodes:
        nid = _ensure_compound_id(graph_id, _node_id_any(n))
        if not nid:
            continue
        d = None
        try:
            d = get_node_detail(graph_id, nid)
        except Exception:
            d = None
        if not isinstance(d, dict):
            continue
        g = _galaxy_of_kind(_as_str(d.get("kind", "memory")))
        counts[g] = counts.get(g, 0) + 1

    galaxies = [
        {"id": k, "label": k.title(), "count": int(v)} for k, v in counts.items() if int(v) > 0
    ]
    galaxies.sort(key=lambda x: _as_int(x.get("count"), default=0), reverse=True)
    return {"graph_id": graph_id, "galaxies": galaxies, "meta": {"sample": samp}}


# -----------------------------------------------------------------------------
# 10) INGEST UPLOADS (additive)
# -----------------------------------------------------------------------------
@router.post("/{graph_id}/ingest", response_model=IngestResponse)
async def api_ingest(
    graph_id: str,
    files: List[UploadFile] = File(...),
    chunk_chars: int = Query(DEFAULT_CHUNK_CHARS, ge=500, le=20000),
    dedupe: bool = Query(True),
):
    if not files:
        raise HTTPException(status_code=400, detail="files are required")

    seen: set[str] = set()
    results: List[IngestFileResult] = []
    nodes_created = 0
    created_nodes: List[str] = []

    for f in files:
        name = (f.filename or "upload").strip()
        content_type = f.content_type or ""
        data = await f.read()
        await f.close()

        if not data:
            results.append(
                IngestFileResult(
                    filename=name,
                    size_bytes=0,
                    content_type=content_type or None,
                    chunks=0,
                    skipped=True,
                    note="Empty file.",
                )
            )
            continue

        if len(data) > MAX_INGEST_BYTES:
            results.append(
                IngestFileResult(
                    filename=name,
                    size_bytes=len(data),
                    content_type=content_type or None,
                    chunks=0,
                    skipped=True,
                    note="File too large (limit 20 MB).",
                )
            )
            continue

        raw = ""
        note: Optional[str] = None
        try:
            if _is_text_file(name.lower(), content_type.lower()):
                raw = data.decode("utf-8", errors="replace")
            elif name.lower().endswith(".docx") or content_type == (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ):
                raw = _extract_docx_text(data)
                if not raw:
                    note = "DOCX extraction failed."
            elif name.lower().endswith(".pdf") or content_type == "application/pdf":
                raw = _extract_pdf_text(data)
                if not raw:
                    note = "PDF extraction unavailable or empty."
            else:
                results.append(
                    IngestFileResult(
                        filename=name,
                        size_bytes=len(data),
                        content_type=content_type or None,
                        chunks=0,
                        skipped=True,
                        note="Unsupported file type.",
                    )
                )
                continue
        except Exception:
            results.append(
                IngestFileResult(
                    filename=name,
                    size_bytes=len(data),
                    content_type=content_type or None,
                    chunks=0,
                    skipped=True,
                    note="Failed to extract text.",
                )
            )
            continue

        cleaned = _normalize_text(raw)
        if not cleaned:
            results.append(
                IngestFileResult(
                    filename=name,
                    size_bytes=len(data),
                    content_type=content_type or None,
                    chunks=0,
                    skipped=True,
                    note=note or "No extractable text.",
                )
            )
            continue

        chunks = _chunk_text(cleaned, chunk_chars)
        created = 0
        deduped = 0

        for chunk in chunks:
            c = chunk.strip()
            if not c:
                continue
            key = c.lower()
            if dedupe and key in seen:
                deduped += 1
                continue
            if dedupe:
                seen.add(key)
            nid = add_fragment(graph_id, c)
            created_nodes.append(nid)
            created += 1
            nodes_created += 1

        if created == 0:
            results.append(
                IngestFileResult(
                    filename=name,
                    size_bytes=len(data),
                    content_type=content_type or None,
                    chunks=0,
                    skipped=True,
                    note=note or "All chunks were deduplicated.",
                )
            )
            continue

        note_out = note
        if deduped > 0:
            note_out = (note_out + " " if note_out else "") + f"Deduped {deduped} chunk(s)."

        results.append(
            IngestFileResult(
                filename=name,
                size_bytes=len(data),
                content_type=content_type or None,
                chunks=created,
                skipped=False,
                note=note_out,
            )
        )

    if created_nodes:
        try:
            await emit_fig_delta(
                graph_id,
                {
                    "nodes_added": [{"id": nid} for nid in created_nodes],
                    "links_added": [],
                    "nodes_removed": [],
                    "links_removed": [],
                },
            )
        except Exception:
            pass

    return IngestResponse(
        status="ok",
        graph_id=graph_id,
        files=results,
        nodes_created=nodes_created,
        source="ingest",
        note="chunks+dedupe" if dedupe else "chunks",
    )


# -----------------------------------------------------------------------------
# 11) ADD MEMORY FRAGMENT — ORIGINAL (hardened)
# -----------------------------------------------------------------------------
@router.post("/{graph_id}/add")
def api_add_fragment_route(
    graph_id: str,
    text: Optional[str] = Query(None),
    payload: Optional[AddFragmentPayload] = Body(None),
):
    text_raw = payload.text if payload and payload.text is not None else text
    text2 = (text_raw or "").strip()
    if not text2:
        raise HTTPException(status_code=400, detail="text is required")
    if len(text2) > 20000:
        raise HTTPException(status_code=413, detail="text too large")
    nid = add_fragment(graph_id, text2)
    return {
        "status": "ok",
        "created_nodes": 1,
        "node_ids": [nid] if nid else [],
    }


# -----------------------------------------------------------------------------
# LEGACY: node_count endpoint (present in earlier builds) — keep additive
# -----------------------------------------------------------------------------
@router.get("/{graph_id}/node_count")
def api_node_count(graph_id: str) -> Dict[str, Any]:
    return {"graph_id": graph_id, "node_count": int(_count_nodes_store(graph_id))}
