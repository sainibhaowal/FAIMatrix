# =============================================================================
# FAIM — GOLD EDITION (COMMERCIAL / PRODUCTION)
# -----------------------------------------------------------------------------
# File: faim/engine/adapter.py
# Purpose:
#   - UI-facing adapter + virtual graph functions for FAIM Lab / FIG UI
#   - JSON safety everywhere (no numpy arrays, bytes, or non-serializable objects)
#   - Stable UI node/link contracts for frontend
#   - Galaxy view (derived clusters) WITHOUT touching faim/core/*
#
# Hard rules:
#   - Do NOT modify faim/core/* logic.
#   - Prefer faim/engine/interface.py for payload decode + meta tracking.
#   - Never raise in UI formatting functions; return empty structures instead.
#
# Step-4 Contract (locked):
#   Node: {id,label,kind,degree,created_at,last_used_at,use_count,preview}
#   Link: {source,target,rel,weight}
#
# HARDENING (critical):
#   - virtual_neighborhood() MUST NEVER 500.
#   - virtual_vector_stats() MUST NEVER 500.
#   - Any error => degrade gracefully (empty list / None), never throw.
# =============================================================================

from __future__ import annotations

import hashlib
import heapq
import math
import time
from collections import Counter, deque
from collections.abc import Iterable as _Iterable
from collections.abc import Sized
from hashlib import sha256
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Literal,
    Mapping,
    Optional,
    Tuple,
    cast,
)

from . import interface as iface
from faim.core.engine import FAIMEngine
from faim.core.types import GraphId, NodeId

# Keep direct references (clean + consistent), but resolved via module:
decode_payload_text = iface.decode_payload_text
get_node_detail = iface.get_node_detail
infer_kind = iface.infer_kind
label_from_payload = iface.label_from_payload
preview_from_payload = iface.preview_from_payload
record_node_used = iface.record_node_used

# =============================================================================
# ENGINE (lazy initialization to avoid import-time failures)
# =============================================================================
import threading as _threading

_engine: Optional[FAIMEngine] = None
_engine_lock = _threading.Lock()


def _get_engine() -> FAIMEngine:
    """Lazy initialization of FAIMEngine with PostgresStore."""
    global _engine
    if _engine is not None:
        return _engine

    with _engine_lock:
        if _engine is not None:
            return _engine

        try:
            from faim.data.storage.postgres_store import PostgresStore

            store = PostgresStore()
            _engine = FAIMEngine(store=store)
        except Exception as e:
            import logging

            logging.warning(f"Failed to initialize FAIMEngine: {e}")
            raise RuntimeError(f"Cannot initialize FAIMEngine: {e}") from e

        return _engine


# =============================================================================
# JSON-SAFE PRIMITIVES (never raise)
# =============================================================================
def _as_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _safe_str(v: Any) -> str:
    try:
        return "" if v is None else str(v)
    except Exception:
        return ""


def _json_safe_scalar(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return v
    return _safe_str(v)


def _stable_hash_text(s: str) -> str:
    return sha256((s or "").encode("utf-8", errors="replace")).hexdigest()


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        if v is None:
            return default
        return int(v)
    except Exception:
        return default


def _scalar_float(x: Any) -> float:
    """
    Convert numpy/torch/python scalar to float without raising on common tensor types.
    """
    if x is None:
        raise ValueError("scalar is None")
    # torch / numpy 0-d scalars often have .item()
    if hasattr(x, "item") and callable(x.item):
        return float(x.item())  # type: ignore[misc]
    return float(x)


def _vector_to_float_list(vec: Any, max_n: int = 4096) -> List[float]:
    """
    Convert a vector (numpy/torch/list) into a plain Python list[float] safely.
    - Pylance-clean (no attribute access on `object`)
    - Never raises
    - Handles torch tensors (detach/cpu), numpy arrays, and Python sequences
    - Flattens common nested list shapes (e.g. [[...]] or [[...],[...]] best-effort)
    """
    try:
        v: Any = vec
        if v is None:
            return []

        # torch: detach -> cpu (best-effort; guarded)
        det = getattr(v, "detach", None)
        if callable(det):
            try:
                v = det()
            except Exception:
                pass

        cpu = getattr(v, "cpu", None)
        if callable(cpu):
            try:
                v = cpu()
            except Exception:
                pass

        raw_list: List[Any]

        tolist = getattr(v, "tolist", None)
        if callable(tolist):
            try:
                raw_any = tolist()
                # numpy/torch commonly return list/float/etc
                if isinstance(raw_any, list):
                    raw_list = raw_any
                elif isinstance(raw_any, tuple):
                    raw_list = list(raw_any)
                else:
                    raw_list = [raw_any]
            except Exception:
                raw_list = []
        else:
            # fallback: only try list() if actually iterable
            if isinstance(v, (str, bytes, bytearray, dict)):
                return []
            if isinstance(v, _Iterable):
                try:
                    raw_list = list(v)
                except Exception:
                    raw_list = []
            else:
                return []

        # flatten one level if nested lists/tuples (common for (1,D) or (D,1))
        if raw_list and isinstance(raw_list[0], (list, tuple)):
            flat: List[Any] = []
            for row in raw_list:
                if isinstance(row, (list, tuple)):
                    flat.extend(list(row))
                else:
                    flat.append(row)
            raw_list = flat

        out: List[float] = []
        lim = max(0, int(max_n))
        for it in raw_list[:lim]:
            try:
                out.append(_scalar_float(it))
            except Exception:
                # skip non-numeric items deterministically
                continue
        return out
    except Exception:
        return []


def _stats_from_list(xs: List[float]) -> Optional[Dict[str, float]]:
    """
    Deterministic stats for VectorStats: norm, mean, std, min, max.
    Uses population std (divide by N) for stability.
    """
    if not xs:
        return None
    n = len(xs)
    s = float(sum(xs))
    mean = s / float(n)

    # population variance
    var = float(sum((x - mean) * (x - mean) for x in xs)) / float(n)
    std = math.sqrt(var)

    mn = float(min(xs))
    mx = float(max(xs))
    norm = math.sqrt(float(sum(x * x for x in xs)))

    return {"norm": norm, "mean": mean, "std": std, "min": mn, "max": mx}


def _cosine_sim_lists(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    if n <= 0:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for i in range(n):
        xa = a[i]
        xb = b[i]
        dot += xa * xb
        na += xa * xa
        nb += xb * xb
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return float(dot / math.sqrt(na * nb))


def _safe_float_opt(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        # bool is an int subclass; do not treat it as numeric.
        if isinstance(v, bool):
            return None
        return float(v)
    except Exception:
        return None


def _safe_len(x: Any) -> int | None:
    try:
        if isinstance(x, Sized):
            return len(x)
        return None
    except Exception:
        return None


def _payload_hash(payload: str) -> str:
    try:
        b = (payload or "").encode("utf-8", errors="replace")
        return hashlib.sha256(b).hexdigest()
    except Exception:
        return ""


def _iter_ann_pairs(x: Any) -> Iterator[Tuple[Any, float]]:
    """
    Normalize vector_bank.top_k output into (id, score) pairs.

    Accepts:
      - list/tuple of 2-tuples: [(id, score), ...]
      - list of dicts: [{"id":..., "score":...}, ...]
      - any iterable yielding 2-tuples
    Rejects:
      - None, scalar, non-iterables -> yields nothing
    """
    if x is None:
        return
        yield  # pragma: no cover (keeps generator type)

    # Common: list[tuple[id, score]]
    if isinstance(x, list) or isinstance(x, tuple):
        for it in x:
            if isinstance(it, (list, tuple)) and len(it) == 2:
                yield (it[0], _as_float(it[1], default=0.0))

            elif isinstance(it, dict):
                oid = it.get("id", it.get("node_id"))
                sc = it.get("score", it.get("distance", 0.0))
                if oid is not None:
                    try:
                        yield (oid, _as_float(sc, default=0.0))

                    except Exception:
                        yield (oid, 0.0)
        return

    # Generic iterable (best effort)
    try:
        it_obj = iter(x)  # may raise TypeError
    except TypeError:
        return

    for it in it_obj:
        if isinstance(it, (list, tuple)) and len(it) == 2:
            try:
                yield (it[0], float(it[1]))
            except Exception:
                yield (it[0], 0.0)
        elif isinstance(it, dict):
            oid = it.get("id", it.get("node_id"))
            sc = it.get("score", it.get("distance", 0.0))
            if oid is not None:
                try:
                    yield (oid, float(it[1]))
                except Exception:
                    yield (oid, 0.0)


def _iter_vec_as_floats(v: Any, max_n: int = 2048) -> List[float]:
    """
    Convert a vector-like object to a Python list[float], safely.
    Never raises. Caps length to max_n for safety.
    """
    try:
        if v is None:
            return []
        if hasattr(v, "tolist"):
            arr = v.tolist()
        else:
            arr = list(v)
        out: List[float] = []
        for x in arr[: max(0, int(max_n))]:
            fx = _safe_float_opt(x)
            if fx is None:
                out.append(0.0)
            else:
                out.append(float(fx))
        return out
    except Exception:
        return []


def _bulk_get_node_meta_safe(graph_id: str, node_ids: List[str]) -> Dict[str, Any]:
    """
    Best-effort meta fetch. Never raises. Works even if older interface.py
    does not expose bulk_get_node_meta.
    """
    fn = getattr(iface, "bulk_get_node_meta", None)
    if callable(fn):
        try:
            return fn(graph_id, node_ids)  # type: ignore[misc]
        except Exception:
            return {}
    return {}


def _vector_stats_from_vec(vec: Any) -> Optional[dict[str, float | int]]:
    """
    Compute small JSON-safe stats from an embedding vector.
    Pylance-clean: does not call .mean/.min/.max on unknown objects.
    Never raises; returns None on failure.
    """
    xs = _vector_to_float_list(vec)
    if not xs:
        return None

    st = _stats_from_list(xs)
    if st is None:
        return None

    out: dict[str, float | int] = {
        "dim": int(len(xs)),
        "norm": float(st["norm"]),
        "mean": float(st["mean"]),
        "std": float(st["std"]),
        "min": float(st["min"]),
        "max": float(st["max"]),
    }
    return out


def _vec(n: Any) -> List[float]:
    """
    Return node vector as a plain Python list (UI-safe).
    Pylance-clean.
    """
    v = getattr(n, "vec", None)
    return _vector_to_float_list(v)


# =============================================================================
# PAYLOAD DECODE (payload_ref -> real text)
# =============================================================================
def _payload_text(gid: GraphId, n: Any) -> str:
    pref = getattr(n, "payload_ref", None)
    if pref is None:
        return ""
    try:
        b = _get_engine()._payload_store.get_payload(gid, pref)  # type: ignore[attr-defined]
        if not b:
            return ""
        if isinstance(b, (bytes, bytearray)):
            return bytes(b).decode("utf-8", errors="replace")
        return str(b)
    except Exception:
        return ""


def _label_from_payload(payload: str, fallback: str) -> str:
    p = (payload or "").strip()
    if not p:
        return fallback
    line = p.splitlines()[0].strip()
    if len(line) > 96:
        line = line[:93] + "..."
    return line or fallback


def _preview_from_payload(payload: str, limit: int = 160) -> str:
    s = (payload or "").strip().replace("\n", " ")
    if len(s) > limit:
        return s[: max(0, limit - 3)] + "..."
    return s


def _infer_kind(payload: str) -> str:
    p = (payload or "").strip()
    if p.startswith("FACT:"):
        return "fact"
    if p.startswith("[doc:") or p.startswith("[pdf:"):
        return "doc"
    if p.startswith("[chat:user]"):
        return "user_chat"
    if p.startswith("[chat:assistant]"):
        return "assistant_chat"
    return "memory"


def _tokenize(s: str) -> List[str]:
    return [t for t in (s or "").lower().replace("\n", " ").split(" ") if t.strip()]


# =============================================================================
# HARDENING HELPERS — SCALAR COERCION + VECTOR STATS
# =============================================================================
def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (float, int)):
        return float(v)
    item = getattr(v, "item", None)
    if callable(item):
        try:
            vv: Any = item()
            return float(vv)
        except Exception:
            pass
    try:
        return float(v)  # type: ignore[arg-type]
    except Exception:
        return None


def _vec_dim(vec: Any) -> int:
    if vec is None:
        return 0
    shape = getattr(vec, "shape", None)
    if shape is not None:
        try:
            return int(shape[0])  # type: ignore[index]
        except Exception:
            pass
    try:
        return int(len(vec))  # type: ignore[arg-type]
    except Exception:
        return 0


def _vec_stats(vec: Any) -> Optional[Dict[str, Any]]:
    if vec is None:
        return None

    dim = _vec_dim(vec)
    if dim <= 0:
        return None

    # norm fast path
    try:
        vv = (vec**2).sum()  # type: ignore[operator]
        norm = _to_float(vv**0.5)  # type: ignore[operator]
    except Exception:
        norm = None

    def _stat_call(name: str) -> Optional[float]:
        fn = getattr(vec, name, None)
        if not callable(fn):
            return None
        try:
            return _to_float(fn())
        except Exception:
            return None

    mean = _stat_call("mean")
    std = _stat_call("std")
    vmin = _stat_call("min")
    vmax = _stat_call("max")

    # fallback for list/tuple
    if mean is None or std is None or vmin is None or vmax is None:
        try:
            arr = list(vec)  # type: ignore[arg-type]
            vals: List[float] = []
            for x in arr:
                fx = _to_float(x)
                if fx is not None:
                    vals.append(fx)
            if not vals:
                return None
            if mean is None:
                mean = float(sum(vals) / max(1, len(vals)))
            if vmin is None:
                vmin = float(min(vals))
            if vmax is None:
                vmax = float(max(vals))
            if std is None:
                mu = mean
                var = float(sum((x - mu) ** 2 for x in vals) / max(1, len(vals)))
                std = float(var**0.5)
            if norm is None:
                norm = float(sum(x * x for x in vals) ** 0.5)
            dim = int(len(vals))
        except Exception:
            pass

    out: Dict[str, Any] = {"dim": int(dim)}
    if norm is not None:
        out["norm"] = float(norm)
    if mean is not None:
        out["mean"] = float(mean)
    if std is not None:
        out["std"] = float(std)
    if vmin is not None:
        out["min"] = float(vmin)
    if vmax is not None:
        out["max"] = float(vmax)
    return out


# =============================================================================
# STABLE UI OBJECTS (locked schema)
# =============================================================================


def format_link_for_ui(
    source: str, target: str, rel: str = "parent", weight: Optional[float] = None
) -> Dict[str, Any]:
    return {
        "source": _safe_str(source),
        "target": _safe_str(target),
        "rel": _safe_str(rel),
        "weight": _safe_float_opt(weight),
    }


def _stable_node_from_payload(
    graph_id: str,
    node_id: str,
    payload: str,
    degree: int,
    created_at: Optional[float],
    last_used_at: Optional[float],
    use_count: int,
) -> Dict[str, Any]:
    label = label_from_payload(payload, fallback=node_id)
    kind = infer_kind(payload)
    preview = preview_from_payload(payload)
    return {
        "id": _safe_str(node_id),
        "label": _safe_str(label),
        "kind": _safe_str(kind),
        "degree": _safe_int(degree),
        "created_at": created_at,
        "last_used_at": last_used_at,
        "use_count": _safe_int(use_count),
        "preview": _safe_str(preview),
    }


def format_node_for_ui_raw(graph_id: str, node_obj: Any) -> Dict[str, Any]:
    """
    Lightweight stable node for scans/FIG. Does NOT require get_node_detail().
    """
    try:
        nid = _safe_str(getattr(node_obj, "id", ""))
        payload = decode_payload_text(graph_id, node_obj)
        parents = getattr(node_obj, "parents", []) or []
        children = getattr(node_obj, "children", []) or []
        degree = int(len(parents) + len(children))

        # update usage meta best-effort
        record_node_used(graph_id, nid, ts=time.time(), inc=1)
        meta_map = _bulk_get_node_meta_safe(graph_id, [nid])
        meta = meta_map.get(nid)
        ca = meta.created_at if meta else None
        lua = meta.last_used_at if meta else None
        uc = meta.use_count if meta else 0

        return _stable_node_from_payload(graph_id, nid, payload, degree, ca, lua, uc)
    except Exception:
        # absolute safety
        return {
            "id": _safe_str(getattr(node_obj, "id", "")),
            "label": _safe_str(getattr(node_obj, "id", "")),
            "kind": "memory",
            "degree": 0,
            "created_at": None,
            "last_used_at": None,
            "use_count": 0,
            "preview": "",
        }


# =============================================================================
# LEGACY-COMPAT FORMATTERS (do not remove; graphs.py may call these)
# =============================================================================


def format_node_for_ui(
    detail: Mapping[str, Any] | Any, mode: Literal["A", "B", "C"] = "A"
) -> Dict[str, Any]:
    """
    Compatibility formatter that keeps your older shapes working, while ALWAYS
    including the stable fields required by the frontend contract.

    mode:
      A = graph node (no payload)
      B = inspector (payload + parents/children)
      C = debug (may include hashes, extra)
    """
    d = _as_mapping(detail)
    try:
        if isinstance(detail, Mapping):
            raw = dict(detail)
            nid = _safe_str(raw.get("id", ""))
            payload = _safe_str(raw.get("payload", "")) if mode in ("B", "C") else ""
            label = _safe_str(raw.get("label", "")) or label_from_payload(payload, fallback=nid)
            kind = _safe_str(raw.get("kind", "")) or infer_kind(payload)
            degree = _safe_int(raw.get("degree", 0))
            preview = _safe_str(raw.get("preview", "")) or preview_from_payload(payload)

            created_at = raw.get("created_at")
            last_used_at = raw.get("last_used_at")
            use_count = _safe_int(raw.get("use_count", 0))

            out: Dict[str, Any] = {
                "kind": kind,
                "created_at": created_at if isinstance(created_at, (int, float)) else None,
                "last_used_at": last_used_at if isinstance(last_used_at, (int, float)) else None,
                "use_count": use_count,
                "preview": preview,
                "id": _safe_str(d.get("id")),
                "label": _safe_str(d.get("label")),
                "vector": None,
                "payload": d.get("payload") if mode == "B" else None,
                "parents": d.get("parents") if mode == "B" else None,
                "fractions": d.get("fractions") if mode == "B" else None,
                "novelty": d.get("novelty") if mode == "B" else None,
                "inherited": d.get("inherited") if mode == "B" else None,
                "children": d.get("children") if mode == "B" else None,
                "degree": _json_safe_scalar(d.get("degree")),
                "redundancy_score": d.get("redundancy_score"),
                "evolution_flags": d.get("evolution_flags"),
                "parent_distances": d.get("parent_distances"),
                "vector_stats": d.get("vector_stats"),
            }

            # preserve legacy fields if present (do NOT delete)
            for k, v in raw.items():
                if k in out:
                    continue
                # ensure JSON-safe primitives only
                if isinstance(v, (str, int, float, bool)) or v is None:
                    out[k] = v
                elif isinstance(v, list):
                    out[k] = v
                elif isinstance(v, dict):
                    out[k] = v
                else:
                    out[k] = _safe_str(v)

            if mode == "A":
                # ensure payload isn't forced into graph view
                out.pop("payload", None)
            return out

        # node is engine NodeRecord-like
        nid = _safe_str(getattr(detail, "id", ""))
        payload = ""
        label = nid
        kind = "memory"
        try:
            # we can derive label/kind if caller passes graph_id elsewhere;
            # but do not risk exceptions here.
            pass
        except Exception:
            pass

        parents = getattr(detail, "parents", []) or []
        children = getattr(detail, "children", []) or []
        degree = int(len(parents) + len(children))

        out2 = {
            "id": nid,
            "label": label,
            "kind": kind,
            "degree": degree,
            "created_at": None,
            "last_used_at": None,
            "use_count": 0,
            "preview": "",
        }

        if mode in ("B", "C"):
            # keep legacy keys expected by NodeInspector
            out2["payload"] = payload
            out2["parents"] = []
            out2["children"] = [_safe_str(c) for c in children]

        return out2
    except Exception:
        return {
            "id": _safe_str(getattr(detail, "id", ""))
            if not isinstance(detail, Mapping)
            else _safe_str(detail.get("id")),
            "label": "",
            "kind": "memory",
            "degree": 0,
            "created_at": None,
            "last_used_at": None,
            "use_count": 0,
            "preview": "",
        }


def format_subgraph_for_ui(
    subgraph: Mapping[str, Any], mode: Literal["A", "B", "C"] = "A"
) -> Dict[str, Any]:
    """
    Takes a raw BFS result and formats it to stable schema for FIG.
    Keeps legacy structure too.
    """
    try:
        nodes = cast(List[Dict[str, Any]], list(subgraph.get("nodes", [])))
        links = cast(List[Dict[str, Any]], list(subgraph.get("links", [])))
        out_nodes: List[Dict[str, Any]] = []
        for n in nodes:
            out = {"id": str(n.get("id")), "label": n.get("label"), "vector": None, "payload": None}
            if mode == "B":
                out["payload"] = n.get("payload")
            out_nodes.append(out)

        out_links: List[Dict[str, Any]] = []
        for e in links:
            src = _safe_str(e.get("source"))
            tgt = _safe_str(e.get("target"))
            rel = _safe_str(e.get("rel", "parent"))
            w = _safe_float_opt(e.get("weight"))
            out_links.append(format_link_for_ui(src, tgt, rel=rel, weight=w))

        return {"nodes": out_nodes, "links": out_links}
    except Exception:
        return {"nodes": [], "links": []}


# =============================================================================
# 1) VIRTUAL NODE SCAN (engine-native, compat)
# =============================================================================


def virtual_scan_nodes(
    graph_id: str, limit: int = 500, order: str = "id", galaxy: Optional[str] = None
) -> List[Any]:
    """
    Returns engine-native NodeRecords (compat with older graphs.py),
    but supports optional 'galaxy' filter for newer UI.
    """
    try:
        gid = GraphId(graph_id)
        nodes = list(_get_engine()._store.iter_nodes(gid))  # type: ignore[attr-defined]
        if galaxy:
            g = str(galaxy).strip().lower()
            # derived galaxy filter based on payload kind prefix
            filt: List[Any] = []
            for n in nodes:
                payload = decode_payload_text(graph_id, n)
                k = infer_kind(payload).lower()
                if k == g:
                    filt.append(n)
            nodes = filt

        if order == "id":
            nodes.sort(key=lambda n: _safe_str(getattr(n, "id", "")))
        elif order == "degree":
            nodes.sort(
                key=lambda n: len(getattr(n, "parents", []) or [])
                + len(getattr(n, "children", []) or []),
                reverse=True,
            )

        lim = max(1, min(5000, int(limit)))
        return nodes[:lim]
    except Exception:
        return []


# =============================================================================
# 2) VIRTUAL SUBGRAPH (BFS)
# =============================================================================


def virtual_subgraph_bfs(graph_id: str, center_id: str, depth: int = 2) -> Dict[str, Any]:
    """
    BFS expansion around a node. Returns JSON-safe dict:
      {"nodes":[{id,label,kind,degree,preview,...}, ...],
       "links":[{source,target,rel,weight}, ...]}
    """
    try:
        gid = GraphId(graph_id)
        start = NodeId(center_id)
        root = _get_engine()._store.get_node(gid, start)  # type: ignore[attr-defined]
        if root is None:
            return {"nodes": [], "links": []}

        max_depth = max(0, min(8, int(depth)))

        seen: set[str] = set()
        q: deque[Tuple[Any, int]] = deque()
        q.append((root, 0))

        nodes_out: List[Dict[str, Any]] = []
        links_out: List[Dict[str, Any]] = []

        while q:
            node, d = q.popleft()
            nid = _safe_str(getattr(node, "id", ""))
            if not nid or nid in seen:
                continue
            seen.add(nid)

            # stable node
            nodes_out.append(format_node_for_ui_raw(graph_id, node))

            if d >= max_depth:
                continue

            # parents => edges parent -> child
            parents = getattr(node, "parents", []) or []
            for p in parents:
                pid = _safe_str(getattr(p, "parent_id", ""))
                frac = _safe_float_opt(getattr(p, "fraction", None))
                if pid:
                    links_out.append(format_link_for_ui(pid, nid, rel="parent", weight=frac))
                    pn = _get_engine()._store.get_node(gid, NodeId(pid))  # type: ignore[attr-defined]
                    if pn is not None:
                        q.append((pn, d + 1))

            # children => edges node -> child
            children = getattr(node, "children", []) or []
            for cid_any in children:
                cid = _safe_str(cid_any)
                if cid:
                    links_out.append(format_link_for_ui(nid, cid, rel="child", weight=1.0))
                    cn = _get_engine()._store.get_node(gid, NodeId(cid))  # type: ignore[attr-defined]
                    if cn is not None:
                        q.append((cn, d + 1))

            # Fallback: if no structural links exist, add similarity links to keep FIG connected.
            if d < max_depth and not parents and not children:
                try:
                    neighbors = virtual_neighborhood(graph_id, nid, k=3)
                    for nb in neighbors:
                        sid = _safe_str(nb.get("id"))
                        if not sid:
                            continue
                        w = _safe_float_opt(nb.get("distance"))
                        links_out.append(format_link_for_ui(nid, sid, rel="similar", weight=w))
                        sn = _get_engine()._store.get_node(gid, NodeId(sid))  # type: ignore[attr-defined]
                        if sn is not None:
                            q.append((sn, d + 1))
                except Exception:
                    pass

        return {"nodes": nodes_out, "links": links_out}
    except Exception:
        return {"nodes": [], "links": []}


# =============================================================================
# 3) LINEAGE (parent chain)
# =============================================================================


def virtual_parent_lineage(graph_id: str, node_id: str, depth: int = 10) -> List[str]:
    """
    Returns list of node_ids starting from node_id up through parents.
    Never raises.
    """
    try:
        gid = GraphId(graph_id)
        cur = _get_engine()._store.get_node(gid, NodeId(node_id))  # type: ignore[attr-defined]
        if cur is None:
            return []

        out: List[str] = []
        maxd = max(0, min(128, int(depth)))
        step = 0

        while cur is not None and step <= maxd:
            cid = _safe_str(getattr(cur, "id", ""))
            if not cid:
                break
            out.append(cid)

            parents = getattr(cur, "parents", []) or []
            if not parents:
                break

            # deterministic: choose the parent with max fraction, tie by id
            pairs: List[Tuple[float, str]] = []
            for p in parents:
                pid = _safe_str(getattr(p, "parent_id", ""))
                frac = _safe_float_opt(getattr(p, "fraction", None))
                pairs.append((frac if frac is not None else 0.0, pid))
            pairs.sort(key=lambda t: (-t[0], t[1]))

            next_id = pairs[0][1] if pairs else ""
            if not next_id:
                break
            cur = _get_engine()._store.get_node(gid, NodeId(next_id))  # type: ignore[attr-defined]
            step += 1

        return out
    except Exception:
        return []


# =============================================================================
# 4) NEIGHBORHOOD (MUST NEVER 500)
# =============================================================================
def virtual_neighborhood(graph_id: str, node_id: str, k: int = 10):
    """
    Hybrid neighbors (commercial behavior):

    Order (deterministic):
      1) ANN neighbors via vector_bank.top_k (if available)
      2) ANN neighbors via ANN index (if available)
      3) Structural neighbors (parents + children) fallback
      4) Optional 2-hop structural expansion to fill k
      5) Vector similarity scan over store (last resort)

    Contract:
      - NEVER raises to caller (no 500)
      - Returns [] if node not found
      - Returns JSON-safe list[{id:str, distance:float}]
    """
    kk = max(1, min(128, int(k)))

    gid = GraphId(graph_id)
    nid = NodeId(node_id)

    try:
        node = _get_engine()._store.get_node(gid, nid)  # type: ignore[attr-defined]
    except Exception:
        return []

    if node is None:
        return []

    out: list[dict[str, float | str]] = []
    seen: set[str] = set()

    # -------------------------------------------------------------------------
    # 1) ANN neighbors (best effort)
    # -------------------------------------------------------------------------
    try:
        vb = getattr(_engine, "_vector_bank", None)
        vec = getattr(node, "vec", None)
        top_k = getattr(vb, "top_k", None) if vb is not None else None

        if vec is not None and callable(top_k):
            raw = top_k(gid, vec, kk + 1)  # include self

            # expected shape: Iterable[Tuple[NodeId, float]]
            for other_id, score in _iter_ann_pairs(raw):
                sid = str(other_id)
                if sid == node_id:
                    continue
                if sid in seen:
                    continue
                seen.add(sid)
                # "distance" here is whatever your vector_bank returns (sim/dist).
                out.append({"id": sid, "distance": float(score)})
                if len(out) >= kk:
                    break
    except Exception:
        # swallow and fallback to structural
        pass

    # -------------------------------------------------------------------------
    # 1b) ANN index fallback (if VectorBank is empty)
    # -------------------------------------------------------------------------
    try:
        ann = getattr(_engine, "_ann", None)
        vec = getattr(node, "vec", None)
        top_k = getattr(ann, "top_k", None) if ann is not None else None

        if vec is not None and callable(top_k):
            raw = top_k(gid, vec, kk + 1)  # include self
            for other_id, score in _iter_ann_pairs(raw):
                sid = str(other_id)
                if sid == node_id:
                    continue
                if sid in seen:
                    continue
                seen.add(sid)
                out.append({"id": sid, "distance": float(score)})
                if len(out) >= kk:
                    break
    except Exception:
        pass

    if out:
        return out

    # -------------------------------------------------------------------------
    # 2) Structural fallback (parents + children)
    # -------------------------------------------------------------------------
    def _push(sid: str, dist: float) -> None:
        if not sid or sid == node_id:
            return
        if sid in seen:
            return
        seen.add(sid)
        out.append({"id": sid, "distance": float(dist)})

    try:
        parents = getattr(node, "parents", None) or []
        for p in parents:
            pid = getattr(p, "parent_id", None)
            if pid is None:
                continue
            _push(str(pid), 0.0)

        children = getattr(node, "children", None) or []
        for c in children:
            _push(str(c), 0.0)
    except Exception:
        # if store shapes differ, still never crash
        pass

    if len(out) >= kk:
        return out[:kk]

    # -------------------------------------------------------------------------
    # 3) 2-hop expansion (fill remaining)
    # -------------------------------------------------------------------------
    # Deterministic: iterate current out in order, then expand their parents/children
    try:
        first_hop_ids = [d["id"] for d in out if isinstance(d.get("id"), str)]  # type: ignore[union-attr]
        for hop_id in first_hop_ids:
            try:
                hop_node = _get_engine()._store.get_node(gid, NodeId(str(hop_id)))  # type: ignore[attr-defined]
            except Exception:
                hop_node = None
            if hop_node is None:
                continue

            hop_parents = getattr(hop_node, "parents", None) or []
            for p in hop_parents:
                pid = getattr(p, "parent_id", None)
                if pid is None:
                    continue
                _push(str(pid), 1.0)
                if len(out) >= kk:
                    return out[:kk]

            hop_children = getattr(hop_node, "children", None) or []
            for c in hop_children:
                _push(str(c), 1.0)
                if len(out) >= kk:
                    return out[:kk]
    except Exception:
        pass

    # -------------------------------------------------------------------------
    # 4) Vector similarity scan over store (last resort)
    # -------------------------------------------------------------------------
    if len(out) < kk:
        try:
            q_vec = _vector_to_float_list(getattr(node, "vec", None))
            if q_vec:
                store = getattr(_engine, "_store", None)
                iter_nodes = getattr(store, "iter_nodes", None) if store is not None else None
                if callable(iter_nodes):
                    limit = kk - len(out)
                    best: List[Tuple[float, str]] = []
                    for cand in iter_nodes(gid):
                        cid = _safe_str(getattr(cand, "id", ""))
                        if not cid or cid == node_id or cid in seen:
                            continue
                        c_vec = _vector_to_float_list(getattr(cand, "vec", None), max_n=len(q_vec))
                        if not c_vec:
                            continue
                        sim = _cosine_sim_lists(q_vec, c_vec)
                        entry = (sim, cid)
                        if len(best) < limit:
                            heapq.heappush(best, entry)
                        elif entry > best[0]:
                            heapq.heapreplace(best, entry)

                    best.sort(key=lambda t: (-t[0], t[1]))
                    for sim, cid in best:
                        if cid in seen:
                            continue
                        seen.add(cid)
                        out.append({"id": cid, "distance": float(sim)})
                        if len(out) >= kk:
                            break
        except Exception:
            pass

    return out[:kk]


# =============================================================================
# 5) VECTOR STATS (MUST NEVER 500)
# =============================================================================


def virtual_vector_stats(graph_id: str, node_id: str):
    """
    Compute VectorStats for a node.
    HARDENED:
      - returns None if vector missing/unreadable (API should 404)
      - always returns norm, mean, std, min, max
      - supports numpy, torch (CPU/CUDA), and list-like vectors
      - never raises (no 500s)
    """
    try:
        gid = GraphId(graph_id)
        nid = NodeId(node_id)

        node = _get_engine()._store.get_node(gid, nid)  # type: ignore[attr-defined]
        if not node:
            return None

        vec = getattr(node, "vec", None)
        if vec is None:
            return None

        xs = _vector_to_float_list(vec)
        st = _stats_from_list(xs)
        return st  # already {norm,mean,std,min,max} or None
    except Exception:
        return None


# =============================================================================
# 6) DEGREE DISTRIBUTION (JSON-safe)
# =============================================================================


def virtual_degree_distribution(graph_id: str) -> Dict[str, Any]:
    try:
        gid = GraphId(graph_id)
        degs: List[int] = []
        for n in _get_engine()._store.iter_nodes(gid):  # type: ignore[attr-defined]
            parents = getattr(n, "parents", []) or []
            children = getattr(n, "children", []) or []
            degs.append(int(len(parents) + len(children)))
        c = Counter(degs)
        # stable sort by degree asc
        items = [
            {"degree": int(k), "count": int(v)} for k, v in sorted(c.items(), key=lambda t: t[0])
        ]
        return {"graph_id": graph_id, "items": items}
    except Exception:
        return {"graph_id": graph_id, "items": []}


# =============================================================================
# 7) METRICS (virtual, safe placeholders)
# =============================================================================


def virtual_compute_metrics(graph_id: str) -> Dict[str, Any]:
    """
    Non-throwing metrics for UI cards (until full metrics.py is wired).
    """
    try:
        gid = GraphId(graph_id)
        ncount = 0
        ecount = 0
        for n in _get_engine()._store.iter_nodes(gid):  # type: ignore[attr-defined]
            ncount += 1
            ecount += len(getattr(n, "parents", []) or [])
            ecount += len(getattr(n, "children", []) or [])
        # edges counted twice (parents + children), keep as is for now (UI can show both)
        return {"graph_id": graph_id, "nodes": int(ncount), "edges": int(ecount)}
    except Exception:
        return {"graph_id": graph_id, "nodes": 0, "edges": 0}


# =============================================================================
# 8) GALAXIES (derived clusters) — without touching core
# =============================================================================


def virtual_list_galaxies(graph_id: str) -> List[Dict[str, Any]]:
    """
    Derived "galaxy" list based on payload kind.
    Returns: [{"id": "fact", "label": "Facts", "count": 123}, ...]
    """
    try:
        gid = GraphId(graph_id)
        counts: Counter[str] = Counter()
        for n in _get_engine()._store.iter_nodes(gid):  # type: ignore[attr-defined]
            payload = decode_payload_text(graph_id, n)
            k = infer_kind(payload).lower().strip() or "memory"
            counts[k] += 1

        # stable order by count desc then id
        items = sorted(counts.items(), key=lambda t: (-t[1], t[0]))
        out: List[Dict[str, Any]] = []
        for kid, c in items:
            label = {
                "fact": "Facts",
                "user_chat": "User chat",
                "assistant_chat": "Assistant chat",
                "doc": "Documents",
                "memory": "Memory",
            }.get(kid, kid)
            out.append({"id": kid, "label": label, "count": int(c)})
        return out
    except Exception:
        return []


# =============================================================================
# OPTIONAL: PLACEHOLDER CLUSTER GRAPH (kept for compat)
# =============================================================================


def virtual_cluster_graph(graph_id: str, clusters: int = 16):
    # Keep stable API even if not implemented
    return {"graph_id": graph_id, "clusters": int(clusters), "nodes": [], "links": []}


# =============================================================================
# 9) LEGACY UI FORMATTING (Option A / B / C) — kept for compatibility
# =============================================================================

UIMode = Literal["A", "B", "C"]


def _as_mapping(obj: Any) -> Mapping[str, Any]:
    if isinstance(obj, Mapping):
        return obj

    # Pydantic v1
    if hasattr(obj, "dict") and callable(obj.dict):
        try:
            data = obj.dict()  # type: ignore[call-arg]
            if isinstance(data, Mapping):
                return cast(Mapping[str, Any], data)
        except Exception:
            pass

    # Pydantic v2
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        try:
            data = obj.model_dump()  # type: ignore[call-arg]
            if isinstance(data, Mapping):
                return cast(Mapping[str, Any], data)
        except Exception:
            pass

    try:
        return cast(Mapping[str, Any], dict(obj))  # type: ignore[arg-type]
    except Exception:
        return cast(Mapping[str, Any], {})


def format_metrics_for_ui(metrics: Any) -> Dict[str, Any]:
    m = _as_mapping(metrics)
    return {
        "node_count": int(m.get("node_count", 0) or 0),
        "edge_count": int(m.get("edge_count", 0) or 0),
        "compression_ratio": float(m.get("compression_ratio", 0.0) or 0.0),
        "redundancy": float(m.get("redundancy", 0.0) or 0.0),
        "drift": float(m.get("drift", 0.0) or 0.0),
        "latency": m.get("latency")
        or {
            "p50": float(m.get("retrieve_p50_ms", 0.0) or 0.0),
            "p95": float(m.get("retrieve_p95_ms", 0.0) or 0.0),
        },
    }
