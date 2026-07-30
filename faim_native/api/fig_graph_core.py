"""FIG graph helpers (no FastAPI router imports).

Isolated so unit tests avoid loading api.routers (auth / email-validator).
"""

from __future__ import annotations

import sys
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy import and_, asc, or_
from sqlalchemy.orm import Session

_parent = Path(__file__).parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from core.operators.semantic_typing import KNOWN_SEMANTIC_KINDS  # noqa: E402
from store.pg.models_faim import EdgeModel, NodeModel  # noqa: E402

SURFACE_NODE_DEF, SURFACE_NODE_MIN, SURFACE_NODE_MAX = 200, 1, 500
SURFACE_EDGE_DEF, SURFACE_EDGE_MIN, SURFACE_EDGE_MAX = 800, 0, 2000
TIMELINE_DEF, TIMELINE_MIN, TIMELINE_MAX = 0, 0, 100
NB_DEPTH_DEF, NB_DEPTH_MIN, NB_DEPTH_MAX = 2, 1, 4
NB_NODE_DEF, NB_NODE_MIN, NB_NODE_MAX = 150, 1, 300
NB_EDGE_DEF, NB_EDGE_MIN, NB_EDGE_MAX = 400, 0, 800
PATH_HOPS_DEF, PATH_HOPS_MIN, PATH_HOPS_MAX = 12, 1, 32
PATH_MAX_DEF, PATH_MAX_MIN, PATH_MAX_MAX = 1, 1, 3

COLD_AGE = timedelta(days=90)
WARM_AGE = timedelta(days=30)
COLD_TOUCH0_AGE = timedelta(days=7)
ACTIVE_RECENT = timedelta(days=7)
ACTIVE_TOUCH = 5

ANCHOR_TITLE_KEYS = ("title", "label", "text", "name")


def _clamp_int(value: int, default: int, lo: int, hi: int) -> int:
    if value < lo:
        return default if default >= lo else lo
    return max(lo, min(hi, value))


def _parse_edge_kinds_csv(s: str) -> Set[str]:
    known = {"inheritance", "opposition"} | KNOWN_SEMANTIC_KINDS
    parts = {p.strip() for p in (s or "").split(",") if p.strip()}
    return {p for p in parts if p in known}


def _anchor_title(anchor: Any) -> Tuple[str, str]:
    if not isinstance(anchor, dict):
        return "", "unknown"
    for key in ANCHOR_TITLE_KEYS:
        v = anchor.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip(), "anchor"
    return "", "unknown"


def _truncate(s: Optional[str], n: int) -> str:
    if not s:
        return ""
    return s if len(s) <= n else s[:n]


def node_display_payload(node: NodeModel) -> Dict[str, Any]:
    """Contract §5 — display.title, title_source, state."""
    title, src = _anchor_title(node.anchor_json)
    if not title and node.block_id:
        title, src = _truncate(node.block_id, 64), "block_id"
    if not title and node.raw_id:
        title, src = _truncate(str(node.raw_id), 64), "raw_id"
    if not title:
        prefix = (node.vector_hash or "")[:8]
        title, src = f"{node.kind}·{prefix}", "vector_hash"
    if not title:
        title, src = str(node.node_id)[:12] + "…", "node_id"

    state = "unknown"
    now = datetime.now(timezone.utc)
    created = node.created_at or now
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    last = node.last_access
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)

    if last is None and node.touch_count == 0 and (now - created) > COLD_TOUCH0_AGE:
        state = "cold"
    elif last is not None and (now - last) > COLD_AGE:
        state = "cold"
    elif last is not None and (now - last) <= ACTIVE_RECENT:
        state = "active"
    elif node.touch_count >= ACTIVE_TOUCH:
        state = "active"
    elif last is not None and (now - last) <= WARM_AGE:
        state = "warm"

    # temperature: granular 3-tier (hot / warm / cold)
    temperature = "cold"
    if last is not None and (now - last) <= ACTIVE_RECENT:
        temperature = "hot"
    elif node.touch_count >= ACTIVE_TOUCH or (
        last is not None and (now - last) <= WARM_AGE
    ):
        temperature = "warm"

    return {
        "title": title,
        "title_source": src,
        "state": state,
        "temperature": temperature,
    }


def _serialize_node(node: NodeModel) -> Dict[str, Any]:
    display = node_display_payload(node)
    out: Dict[str, Any] = {
        "node_id": str(node.node_id),
        "kind": node.kind,
        "level": node.level,
        "vector_hash": node.vector_hash,
        "display": display,
        "metrics": {
            "touch_count": node.touch_count,
            "residual": node.residual / 1e9 if node.residual else 0.0,
            "last_access": node.last_access.isoformat() if node.last_access else None,
            "temperature": display.get("temperature", "cold"),
        },
        "long_term": getattr(node, "long_term", False),
        "cluster_id": getattr(node, "cluster_id", None),
        "cognitive_type": getattr(node, "cognitive_type", None),
        "galaxy_id": getattr(node, "galaxy_id", None),
        # created_at exposed for client-side timeline stepping (graph-at-time visualization).
        "created_at": node.created_at.isoformat() if node.created_at else None,
    }

    # Anchor metadata — expose structural fields for FIG View and LLM context
    anchor = node.anchor_json or {}
    out["anchor"] = {
        "doc_type": anchor.get("doc_type"),
        "block_type": anchor.get("block_type"),
        "page": anchor.get("page"),
        "slide": anchor.get("slide"),
        "sheet": anchor.get("sheet"),
        "section": anchor.get("section"),
        "row_start": anchor.get("row_start"),
        "row_end": anchor.get("row_end"),
        "char_start": anchor.get("char_start"),
        "char_end": anchor.get("char_end"),
    }

    prov = {}
    if node.raw_id:
        prov["raw_id"] = str(node.raw_id)
    if node.block_id:
        prov["block_id"] = node.block_id
    if prov:
        out["provenance"] = prov
    return out


def _safe_meta(meta: Any) -> Any:
    if meta is None:
        return None
    if isinstance(meta, dict):
        return meta
    return None


def _serialize_edge(edge: EdgeModel) -> Dict[str, Any]:
    return {
        "edge_id": str(edge.edge_id),
        "src_node_id": str(edge.src_node_id),
        "dst_node_id": str(edge.dst_node_id),
        "kind": edge.kind,
        "weight": edge.weight / 1e9 if edge.weight else 0.0,
        "meta": _safe_meta(edge.meta),
        # created_at exposed for client-side timeline stepping.
        "created_at": edge.created_at.isoformat() if edge.created_at else None,
    }


def _incident_edges_query(
    session: Session,
    tenant_id: str,
    graph_id: str,
    node_ids: List[UUID],
    allowed_kinds: Set[str],
):
    if not node_ids or not allowed_kinds:
        return session.query(EdgeModel).filter(False)
    return (
        session.query(EdgeModel)
        .filter(
            and_(
                EdgeModel.tenant_id == tenant_id,
                EdgeModel.graph_id == graph_id,
                EdgeModel.kind.in_(sorted(allowed_kinds)),
                or_(
                    EdgeModel.src_node_id.in_(node_ids),
                    EdgeModel.dst_node_id.in_(node_ids),
                ),
            )
        )
        .order_by(
            asc(EdgeModel.src_node_id),
            asc(EdgeModel.dst_node_id),
            asc(EdgeModel.kind),
        )
    )


def _other_node(edge: EdgeModel, u: UUID) -> Optional[UUID]:
    if edge.src_node_id == u:
        return edge.dst_node_id
    if edge.dst_node_id == u:
        return edge.src_node_id
    return None


def shortest_path_undirected(
    session: Session,
    tenant_id: str,
    graph_id: str,
    start: UUID,
    goal: UUID,
    allowed: Set[str],
    max_hops: int,
) -> Optional[Tuple[List[UUID], List[EdgeModel]]]:
    """Undirected BFS for path explanation (inheritance + opposition)."""
    if start == goal:
        return [start], []
    q: deque[UUID] = deque([start])
    prev_node: Dict[UUID, Optional[UUID]] = {start: None}
    prev_edge: Dict[UUID, Optional[EdgeModel]] = {start: None}
    depth: Dict[UUID, int] = {start: 0}

    while q:
        u = q.popleft()
        if depth[u] >= max_hops:
            continue
        edges = _incident_edges_query(session, tenant_id, graph_id, [u], allowed).all()
        for edge in edges:
            v = _other_node(edge, u)
            if v is None:
                continue
            if v not in prev_node:
                prev_node[v] = u
                prev_edge[v] = edge
                depth[v] = depth[u] + 1
                q.append(v)
                if v == goal:
                    pn_rev: List[UUID] = []
                    pe_rev: List[EdgeModel] = []
                    cur: Optional[UUID] = goal
                    while cur is not None:
                        pn_rev.append(cur)
                        parent = prev_node.get(cur)
                        e = prev_edge.get(cur)
                        if parent is not None and e is not None:
                            pe_rev.append(e)
                        cur = parent
                    pn_rev.reverse()
                    pe_rev.reverse()
                    return pn_rev, pe_rev
    return None


__all__ = [
    "SURFACE_NODE_DEF",
    "PATH_HOPS_DEF",
    "PATH_MAX_DEF",
    "NB_DEPTH_DEF",
    "NB_NODE_DEF",
    "NB_EDGE_DEF",
    "SURFACE_EDGE_DEF",
    "TIMELINE_DEF",
    "_clamp_int",
    "_parse_edge_kinds_csv",
    "node_display_payload",
    "shortest_path_undirected",
    "_serialize_node",
    "_serialize_edge",
    "_incident_edges_query",
    "_other_node",
]
