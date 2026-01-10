# =============================================================================
# FAIM — GOLD EDITION (COMMERCIAL / INDUSTRY PRODUCTION)
# =============================================================================
# File: faim/retrieve/context.py
# Purpose: Retrieval policy (FACTS FIRST, CHAT NOISE LAST) + hard caps + preview
#
# Step-3 rules:
#   - FACT nodes highest priority
#   - (future) DOC summaries / extracted facts next (DOC:/SUMMARY:/EXTRACT:)
#   - recent user messages next
#   - assistant boilerplate last (or excluded)
#   - hard caps:
#       max nodes returned
#       max ctx characters injected
#       dedupe by payload hash
# =============================================================================

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from faim.api.adapters.adapter import virtual_scan_nodes
from faim.config import FaimSettings
from faim.core.engine import FAIMEngine
from faim.core.types import GraphId, NodeRecord

# =============================================================================
# CONFIG
# =============================================================================
settings = FaimSettings.from_env()
FIG_CACHE: Path = settings.cache_dir / "fig_cache.json"
FIG_CACHE.parent.mkdir(parents=True, exist_ok=True)

# Lazy engine initialization
import threading as _threading
from typing import Optional

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


_FACT_PREFIX = "FACT:"
_USER_PREFIX = "[chat:user]"
_ASST_PREFIX = "[chat:assistant]"
_DOC_PREFIXES = ("DOC:", "SUMMARY:", "EXTRACT:", "EXTRACTED:")

MAX_RETURN_NODES = int(os.getenv("FAIM_RETRIEVE_MAX_NODES", "16"))
MAX_CTX_CHARS = int(os.getenv("FAIM_RETRIEVE_MAX_CTX_CHARS", "6000"))
EXCLUDE_ASSISTANT_CHAT = os.getenv("FAIM_RETRIEVE_EXCLUDE_ASSISTANT_CHAT", "1").strip().lower() in (
    "1",
    "true",
    "yes",
    "y",
    "on",
)


# =============================================================================
# HELPERS — SAFE COERCIONS
# =============================================================================
def _safe_str(v: Any) -> str:
    try:
        return "" if v is None else str(v)
    except Exception:
        return ""


def _as_int(v: Any, default: int = 0) -> int:
    if v is None or isinstance(v, bool):
        return default
    if isinstance(v, int):
        return int(v)
    if isinstance(v, float):
        try:
            return int(v)
        except Exception:
            return default
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return default
        try:
            return int(float(s))
        except Exception:
            return default
    return default


def _as_float(v: Any, default: float = 0.0) -> float:
    if v is None or isinstance(v, bool):
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
    return default


def _payload_hash(payload: str) -> str:
    p = (payload or "").encode("utf-8", errors="replace")
    return hashlib.sha256(p).hexdigest()[:16]


def _seq_from_id(nid: str) -> int:
    """
    Your ids look like: U:<hash>:<seq>:<hex>
    We use seq for "recency" tie-break when available.
    """
    try:
        parts = nid.split(":")
        if len(parts) >= 3:
            return int(parts[-2])
    except Exception:
        pass
    return 0


def _kind(payload: str) -> str:
    p = (payload or "").lstrip()
    up = p.upper()
    if up.startswith(_FACT_PREFIX):
        return "fact"
    if any(up.startswith(x) for x in _DOC_PREFIXES):
        return "doc_fact"
    if p.startswith(_USER_PREFIX):
        return "user_chat"
    if p.startswith(_ASST_PREFIX):
        return "assistant_chat"
    return "other"


def _kind_priority(k: str) -> int:
    # Highest first
    if k == "fact":
        return 4
    if k == "doc_fact":
        return 3
    if k == "user_chat":
        return 2
    if k == "other":
        return 1
    return 0  # assistant_chat


def _label_from_payload(payload: str, fallback: str) -> str:
    p = (payload or "").strip()
    if not p:
        return fallback
    line = p.splitlines()[0].strip()
    if len(line) > 72:
        line = line[:69] + "..."
    return line or fallback


# =============================================================================
# PAYLOAD DECODE
# =============================================================================
def _payload_text(gid: GraphId, n: NodeRecord) -> str:
    pref = getattr(n, "payload_ref", None)
    if pref is None:
        return ""
    try:
        b = _get_engine()._payload_store.get_payload(gid, pref)  # type: ignore[attr-defined]
        if not b:
            return ""
        return b.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _node_ui_dict(graph_id: str, n: NodeRecord, score: float) -> Dict[str, Any]:
    gid = GraphId(graph_id)
    payload = _payload_text(gid, n)
    nid = _safe_str(getattr(n, "id", ""))

    parents = getattr(n, "parents", []) or []
    children = getattr(n, "children", []) or []
    degree = int(len(parents) + len(children))

    knd = _kind(payload)
    label = _label_from_payload(payload, fallback=nid)

    return {
        "id": nid,
        "label": _safe_str(label),
        "payload": _safe_str(payload),
        "degree": degree,
        "score": float(score),  # NEVER NULL
        "kind": knd,  # optional (useful for UI)
    }


# =============================================================================
# FIG CACHE
# =============================================================================
def _load_raw_fig_cache() -> Dict[str, Any]:
    if not FIG_CACHE.exists():
        return {"nodes": [], "links": []}
    try:
        with FIG_CACHE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"nodes": [], "links": []}

    nodes = data.get("nodes") or []
    links = data.get("links") or []
    if not isinstance(nodes, list):
        nodes = []
    if not isinstance(links, list):
        links = []

    nodes2: List[Dict[str, Any]] = [n for n in nodes if isinstance(n, dict)]
    return {"nodes": nodes2, "links": links}


def load_fig_cache() -> Dict[str, Any]:
    return _load_raw_fig_cache()


# =============================================================================
# SORT + DEDUPE (BY ID + PAYLOAD HASH)
# =============================================================================
def _sort_used(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def key(n: Dict[str, Any]):
        payload = _safe_str(n.get("payload", ""))
        knd = _safe_str(n.get("kind", _kind(payload)))
        pri = _kind_priority(knd)

        score = _as_float(n.get("score", 0.0), default=0.0)
        degree = _as_int(n.get("degree", 0), default=0)

        nid = _safe_str(n.get("id", ""))
        rec = _seq_from_id(nid)

        # facts-first, then score desc, then recency desc, then degree desc, then id asc
        return (-pri, -score, -rec, -degree, nid)

    return sorted(nodes, key=key)


def _dedupe_by_id(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for n in nodes:
        nid = _safe_str(n.get("id", ""))
        if not nid or nid in seen:
            continue
        seen.add(nid)
        out.append(n)
    return out


def _dedupe_by_payload(nodes: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Keep best-scoring instance of identical payload text.
    Assumes nodes are already sorted best-first.
    """
    seen = set()
    out: List[Dict[str, Any]] = []
    dropped = 0
    for n in nodes:
        ph = _payload_hash(_safe_str(n.get("payload", "")))
        if ph in seen:
            dropped += 1
            continue
        seen.add(ph)
        out.append(n)
    return out, dropped


def _cap_nodes(k: int) -> int:
    k = max(1, int(k))
    return min(k, max(1, MAX_RETURN_NODES))


def _ctx_lines(nodes: List[Dict[str, Any]]) -> Tuple[str, int]:
    """
    Build ctx text with MAX_CTX_CHARS hard cap.
    Returns (ctx_text, chars_used).
    """
    lines: List[str] = []
    used = 0
    for n in nodes:
        nid = _safe_str(n.get("id", ""))
        label = _safe_str(n.get("label", ""))
        payload = _safe_str(n.get("payload", "")).strip()
        # per-node cap
        if len(payload) > 800:
            payload = payload[:800] + "..."
        line = f"[{nid}] {label} {payload}".strip()
        # global cap
        if used + len(line) + 1 > MAX_CTX_CHARS:
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines), used


# =============================================================================
# FIG OVERLAP SCORING
# =============================================================================
def _tokenize(s: str) -> List[str]:
    return [t for t in s.lower().replace("\n", " ").split(" ") if t.strip()]


def _score_nodes_by_overlap(
    fig_nodes: List[Dict[str, Any]], query: str, k: int
) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
    q_tokens = set(_tokenize(query))
    if not q_tokens:
        return [], "", {"strategy": "fig_cache", "dropped_payload_dupes": 0, "ctx_chars": 0}

    scored: List[Dict[str, Any]] = []
    for n in fig_nodes:
        nid = _safe_str(n.get("id", ""))
        if not nid:
            continue
        label = _safe_str(n.get("label", ""))
        payload = _safe_str(n.get("payload", ""))
        degree = _as_int(n.get("degree", 0), default=0)

        # Optional noise filtering for cached assistant nodes too
        knd = _kind(payload)
        if EXCLUDE_ASSISTANT_CHAT and knd == "assistant_chat":
            continue

        text = f"{label} {payload}".lower().strip()
        if not text:
            continue

        overlap = len(q_tokens.intersection(set(_tokenize(text))))
        if overlap <= 0:
            continue

        # score: overlap + kind bonus (facts strongest)
        score = float(overlap) + (
            5.0
            if knd == "fact"
            else 2.0
            if knd == "doc_fact"
            else 0.25
            if knd == "user_chat"
            else 0.0
        )
        scored.append(
            {
                "id": nid,
                "label": label,
                "payload": payload,
                "degree": int(degree),
                "score": float(score),
                "kind": knd,
            }
        )

    if not scored:
        return [], "", {"strategy": "fig_cache", "dropped_payload_dupes": 0, "ctx_chars": 0}

    scored = _sort_used(_dedupe_by_id(scored))
    scored, dropped = _dedupe_by_payload(scored)

    top = scored[:k]
    ctx, chars = _ctx_lines(top)
    meta = {"strategy": "fig_cache", "dropped_payload_dupes": dropped, "ctx_chars": chars}
    return top, ctx, meta


# =============================================================================
# ENGINE RETRIEVE
# =============================================================================
def _engine_retrieve(
    graph_id: str, query: str, k: int
) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
    try:
        nodes: List[NodeRecord] = _get_engine().retrieve(graph_id, query, k=max(k, 16))
    except Exception:
        return [], "", {"strategy": "engine", "dropped_payload_dupes": 0, "ctx_chars": 0}

    if not nodes:
        return [], "", {"strategy": "engine", "dropped_payload_dupes": 0, "ctx_chars": 0}

    used: List[Dict[str, Any]] = []
    for idx, n in enumerate(nodes[: max(0, int(k))]):
        s_any = getattr(n, "score", None)
        base = _as_float(s_any, default=1.0)
        score = base if base > 0 else 1.0
        score = score + max(0.0, 0.25 - (0.02 * float(idx)))  # deterministic rank bonus
        ui = _node_ui_dict(graph_id, n, score=score)

        # noise control
        if EXCLUDE_ASSISTANT_CHAT and ui.get("kind") == "assistant_chat":
            continue
        # facts/doc bonus
        if ui.get("kind") == "fact":
            ui["score"] = float(ui["score"]) + 5.0
        elif ui.get("kind") == "doc_fact":
            ui["score"] = float(ui["score"]) + 2.0
        elif ui.get("kind") == "user_chat":
            ui["score"] = float(ui["score"]) + 0.25

        used.append(ui)

    used = _sort_used(_dedupe_by_id(used))
    used, dropped = _dedupe_by_payload(used)

    top = used[:k]
    ctx, chars = _ctx_lines(top)
    meta = {"strategy": "engine", "dropped_payload_dupes": dropped, "ctx_chars": chars}
    return top, ctx, meta


# =============================================================================
# SCAN FALLBACK
# =============================================================================
def _scan_fallback(graph_id: str, k: int) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
    try:
        raw_nodes: List[NodeRecord] = virtual_scan_nodes(graph_id, limit=max(k, 64), order="degree")
    except Exception:
        return [], "", {"strategy": "scan", "dropped_payload_dupes": 0, "ctx_chars": 0}

    if not raw_nodes:
        return [], "", {"strategy": "scan", "dropped_payload_dupes": 0, "ctx_chars": 0}

    used: List[Dict[str, Any]] = []
    for idx, n in enumerate(raw_nodes[: max(0, int(k))]):
        parents = getattr(n, "parents", []) or []
        children = getattr(n, "children", []) or []
        degree = float(len(parents) + len(children))
        score = degree + max(0.0, 0.10 - (0.01 * float(idx)))  # stable tie-break

        ui = _node_ui_dict(graph_id, n, score=score)

        if EXCLUDE_ASSISTANT_CHAT and ui.get("kind") == "assistant_chat":
            continue
        if ui.get("kind") == "fact":
            ui["score"] = float(ui["score"]) + 5.0
        elif ui.get("kind") == "doc_fact":
            ui["score"] = float(ui["score"]) + 2.0
        elif ui.get("kind") == "user_chat":
            ui["score"] = float(ui["score"]) + 0.25

        used.append(ui)

    used = _sort_used(_dedupe_by_id(used))
    used, dropped = _dedupe_by_payload(used)

    top = used[:k]
    ctx, chars = _ctx_lines(top)
    meta = {"strategy": "scan", "dropped_payload_dupes": dropped, "ctx_chars": chars}
    return top, ctx, meta


# =============================================================================
# PUBLIC API
# =============================================================================
def naive_used_nodes(graph_id: str, query: str, k: int = 8) -> Tuple[List[Dict[str, Any]], str]:
    """
    Returns:
      used_nodes: items include score(float) always
      ctx_text: capped by MAX_CTX_CHARS
    """
    k2 = _cap_nodes(k)

    cache = _load_raw_fig_cache()
    fig_nodes: List[Dict[str, Any]] = cache.get("nodes", []) or []
    if fig_nodes:
        top_nodes, ctx_text, _meta = _score_nodes_by_overlap(fig_nodes, query, k2)
        if top_nodes:
            return top_nodes, ctx_text

    used, ctx, _meta = _engine_retrieve(graph_id, query, k2)
    if used:
        return used, ctx

    used2, ctx2, _meta2 = _scan_fallback(graph_id, k2)
    return used2, ctx2


def retrieve_preview(graph_id: str, query: str, k: int = 8) -> Dict[str, Any]:
    """
    Debug helper for endpoint:
      /api/v1/graphs/{graph_id}/retrieve_preview?query=...
    Provides strategy + dedupe stats + capped chars.
    """
    k2 = _cap_nodes(k)

    cache = _load_raw_fig_cache()
    fig_nodes: List[Dict[str, Any]] = cache.get("nodes", []) or []
    if fig_nodes:
        nodes, ctx, meta = _score_nodes_by_overlap(fig_nodes, query, k2)
        if nodes:
            return {
                "graph_id": graph_id,
                "query": query,
                "k": k2,
                "used_nodes": nodes,
                "ctx_text": ctx,
                "meta": meta,
            }

    nodes, ctx, meta = _engine_retrieve(graph_id, query, k2)
    if nodes:
        return {
            "graph_id": graph_id,
            "query": query,
            "k": k2,
            "used_nodes": nodes,
            "ctx_text": ctx,
            "meta": meta,
        }

    nodes, ctx, meta = _scan_fallback(graph_id, k2)
    return {
        "graph_id": graph_id,
        "query": query,
        "k": k2,
        "used_nodes": nodes,
        "ctx_text": ctx,
        "meta": meta,
    }
