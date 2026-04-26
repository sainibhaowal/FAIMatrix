"""FAIM-Native API: Graph router (FIG aggregate read API).

GET /api/v1/graph/surface
GET /api/v1/graph/neighborhood
POST /api/v1/graph/paths/explain

Contract: frontend/Docs/03_Phase1_FIG_Graph_API_Contract.md
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import and_, func

_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context  # noqa: E402
from api.fig_graph_core import (  # noqa: E402
    NB_DEPTH_DEF,
    NB_DEPTH_MAX,
    NB_DEPTH_MIN,
    NB_EDGE_DEF,
    NB_EDGE_MAX,
    NB_EDGE_MIN,
    NB_NODE_DEF,
    NB_NODE_MAX,
    NB_NODE_MIN,
    PATH_HOPS_DEF,
    PATH_HOPS_MAX,
    PATH_HOPS_MIN,
    PATH_MAX_DEF,
    PATH_MAX_MAX,
    PATH_MAX_MIN,
    SURFACE_EDGE_DEF,
    SURFACE_EDGE_MAX,
    SURFACE_EDGE_MIN,
    SURFACE_NODE_DEF,
    SURFACE_NODE_MAX,
    SURFACE_NODE_MIN,
    TIMELINE_DEF,
    TIMELINE_MAX,
    TIMELINE_MIN,
    _clamp_int,
    _incident_edges_query,
    _other_node,
    _parse_edge_kinds_csv,
    _serialize_edge,
    _serialize_node,
    shortest_path_undirected,
)
from api.routers.metrics import _metric_text_value, _payload_dict  # noqa: E402
from core.operators.semantic_typing import KNOWN_SEMANTIC_KINDS  # noqa: E402
from store.pg.models_faim import EdgeModel  # noqa: E402

# All valid edge kinds including semantic types
_ALL_EDGE_KINDS = ",".join(sorted({"inheritance", "opposition"} | KNOWN_SEMANTIC_KINDS))
# Default edge kinds for graph queries
_DEFAULT_EDGE_KINDS = _ALL_EDGE_KINDS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])


def _parse_uuid(node_id: str) -> UUID:
    try:
        return UUID(str(node_id))
    except (ValueError, TypeError, AttributeError) as e:
        raise HTTPException(
            status_code=400,
            detail="invalid_node_id",
        ) from e


def _best_effort_graph_hash(ctx: FAIMContext, graph_id: str) -> str:
    try:
        events = ctx.event_repo.get_by_seq(
            ctx.session,
            graph_id=graph_id,
            after_seq=0,
            limit=500,
        )
        for e in reversed(events):
            if e.kind == "DIAGNOSTICS_SNAPSHOT":
                payload = _payload_dict(e.payload)
                return _metric_text_value(
                    payload,
                    payload_keys=("graph_hash", "diagnostics_hash"),
                )
    except Exception as ex:
        logger.warning("graph_hash lookup failed graph=%s: %s", graph_id, ex)
    return ""


def _build_snapshot(
    ctx: FAIMContext,
    graph_id: str,
    *,
    graph_hash: str,
    consistent_read: bool,
) -> Dict[str, Any]:
    gv = ctx.gv_repo.get_or_create(ctx.session, graph_id)
    return {
        "graph_id": graph_id,
        "graph_version": int(gv.version),
        "graph_hash": graph_hash,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "consistent_read": consistent_read,
    }


def _resolve_graph_id(
    request: Request,
    graph_id: Optional[str] = Query(None),
    x_graph_id: Optional[str] = Header(None, alias="X-Graph-Id"),
) -> str:
    if not graph_id or not str(graph_id).strip():
        raise HTTPException(status_code=400, detail="missing_graph_id")
    gid = str(graph_id).strip()
    if (
        x_graph_id is not None
        and str(x_graph_id).strip()
        and str(x_graph_id).strip() != gid
    ):
        raise HTTPException(status_code=400, detail="graph_id_mismatch")
    return gid


@router.get("/surface")
async def graph_surface(
    request: Request,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
    graph_id: str = Depends(_resolve_graph_id),
    node_limit: int = Query(SURFACE_NODE_DEF, ge=0),
    edge_limit: int = Query(SURFACE_EDGE_DEF, ge=0),
    timeline_limit: int = Query(TIMELINE_DEF, ge=0),
    after_seq: int = Query(0, ge=0),
    include_topology: bool = Query(True),
) -> Dict[str, Any]:
    nl = _clamp_int(node_limit, SURFACE_NODE_DEF, SURFACE_NODE_MIN, SURFACE_NODE_MAX)
    el = _clamp_int(edge_limit, SURFACE_EDGE_DEF, SURFACE_EDGE_MIN, SURFACE_EDGE_MAX)
    tl = _clamp_int(timeline_limit, TIMELINE_DEF, TIMELINE_MIN, TIMELINE_MAX)

    nodes = ctx.node_repo.list_nodes(graph_id, limit=nl, offset=0)
    node_ids = {str(n.node_id) for n in nodes}
    scan_cap = min(20000, max(el * 20, nl * nl, 500))
    all_edges = ctx.edge_repo.list_all_edges(graph_id, limit=scan_cap)
    all_in_nodes = [
        e
        for e in all_edges
        if str(e.src_node_id) in node_ids and str(e.dst_node_id) in node_ids
    ]
    edges_f = all_in_nodes[:el]

    gh = _best_effort_graph_hash(ctx, graph_id)
    truncated = False
    reasons: List[str] = []
    if ctx.node_repo.count(graph_id) > len(nodes):
        truncated = True
        reasons.append("node_cap")
    if el > 0 and len(all_in_nodes) > el:
        truncated = True
        reasons.append("edge_cap")
    if len(all_edges) >= scan_cap:
        truncated = True
        reasons.append("edge_scan_cap")

    timeline = None
    consistent = True
    if tl > 0:
        consistent = False
        raw = ctx.event_repo.get_by_seq(
            ctx.session,
            graph_id=graph_id,
            after_seq=after_seq,
            limit=tl + 1,
        )
        has_more = len(raw) > tl
        chunk = raw[:tl]
        next_seq = chunk[-1].seq if chunk else after_seq
        timeline = {
            "after_seq": after_seq,
            "next_seq": next_seq,
            "has_more": has_more,
            "events": [
                {
                    "seq": ev.seq,
                    "kind": ev.kind,
                    "ts": ev.ts.isoformat() if ev.ts else None,
                    "payload_keys": sorted(ev.payload.keys()) if ev.payload else [],
                    "graph_id": graph_id,
                }
                for ev in chunk
            ],
        }

    topology = None
    if include_topology:
        edge_by_kind: Dict[str, int] = {}
        try:
            rows = (
                ctx.session.query(EdgeModel.kind, func.count(EdgeModel.edge_id))
                .filter(
                    and_(
                        EdgeModel.tenant_id == ctx.tenant_id,
                        EdgeModel.graph_id == graph_id,
                    )
                )
                .group_by(EdgeModel.kind)
                .all()
            )
            for kind, cnt in rows:
                edge_by_kind[str(kind)] = int(cnt)
        except Exception as ex:
            logger.warning("edge_counts_by_kind failed: %s", ex)
        topology = {
            "node_count": ctx.node_repo.count(graph_id),
            "edge_count": ctx.edge_repo.count(graph_id),
            "edge_counts_by_kind": edge_by_kind,
            "scorecard": None,
        }

    return {
        "snapshot": _build_snapshot(
            ctx,
            graph_id,
            graph_hash=gh,
            consistent_read=consistent,
        ),
        "nodes": [_serialize_node(n) for n in nodes],
        "edges": [_serialize_edge(e) for e in edges_f],
        "timeline": timeline,
        "topology": topology,
        "controls": {
            "similarity": {
                "mode": "none",
                "notes": "Exploration filters affect ranking only; they do not mutate graph truth.",
            }
        },
        "truncated": truncated,
        "truncation_reason": ",".join(reasons) if reasons else None,
    }


@router.get("/neighborhood")
async def graph_neighborhood(
    request: Request,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
    graph_id: str = Depends(_resolve_graph_id),
    node_id: str = Query(..., min_length=1),
    depth: int = Query(NB_DEPTH_DEF, ge=0),
    node_limit: int = Query(NB_NODE_DEF, ge=0),
    edge_limit: int = Query(NB_EDGE_DEF, ge=0),
    edge_kinds: str = Query(_DEFAULT_EDGE_KINDS),
) -> Dict[str, Any]:
    dep = _clamp_int(depth, NB_DEPTH_DEF, NB_DEPTH_MIN, NB_DEPTH_MAX)
    nl = _clamp_int(node_limit, NB_NODE_DEF, NB_NODE_MIN, NB_NODE_MAX)
    el_cap = _clamp_int(edge_limit, NB_EDGE_DEF, NB_EDGE_MIN, NB_EDGE_MAX)

    seed = _parse_uuid(node_id)
    seed_model = ctx.node_repo.get_by_id(graph_id, str(seed))
    if seed_model is None:
        raise HTTPException(status_code=404, detail="node_not_found")

    allowed = _parse_edge_kinds_csv(edge_kinds)
    if not allowed:
        allowed = _parse_edge_kinds_csv(_DEFAULT_EDGE_KINDS)

    visited: Set[UUID] = {seed}
    distances: Dict[str, int] = {str(seed): 0}
    collected_edges: List = []
    edge_seen: Set[str] = set()
    frontier: Set[UUID] = {seed}
    truncated = False
    truncation_reason: Optional[str] = None

    for d in range(dep):
        if not frontier:
            break
        q = _incident_edges_query(
            ctx.session, ctx.tenant_id, graph_id, list(frontier), allowed
        )
        next_frontier: Set[UUID] = set()
        for edge in q.all():
            ekey = str(edge.edge_id)
            if ekey in edge_seen:
                continue
            if edge.src_node_id in frontier:
                u = edge.src_node_id
            elif edge.dst_node_id in frontier:
                u = edge.dst_node_id
            else:
                continue
            other = _other_node(edge, u)
            if other is None:
                continue
            if el_cap > 0 and len(collected_edges) >= el_cap:
                truncated = True
                truncation_reason = "edge_cap"
                break
            edge_seen.add(ekey)
            if el_cap > 0:
                collected_edges.append(edge)
            if other not in visited:
                if len(visited) >= nl:
                    truncated = True
                    truncation_reason = "node_cap"
                    break
                visited.add(other)
                distances[str(other)] = d + 1
                next_frontier.add(other)
        if truncation_reason:
            break
        frontier = next_frontier

    node_models: Dict[str, Any] = {str(seed): seed_model}
    for uid in visited:
        if uid == seed:
            continue
        m = ctx.node_repo.get_by_id(graph_id, str(uid))
        if m:
            node_models[str(uid)] = m

    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    nodes_out = sorted(
        node_models.values(),
        key=lambda n: (n.created_at or epoch, str(n.node_id)),
    )
    edges_out = sorted(
        collected_edges,
        key=lambda e: (str(e.src_node_id), str(e.dst_node_id), e.kind),
    )

    gh = _best_effort_graph_hash(ctx, graph_id)
    return {
        "snapshot": _build_snapshot(
            ctx, graph_id, graph_hash=gh, consistent_read=False
        ),
        "seed_node_id": str(seed),
        "depth_requested": dep,
        "depth_effective": dep,
        "nodes": [_serialize_node(n) for n in nodes_out],
        "edges": [_serialize_edge(e) for e in edges_out],
        "distances": distances,
        "truncated": truncated,
        "truncation_reason": truncation_reason,
    }


class PathsExplainBody(BaseModel):
    from_node_id: str
    to_node_id: str
    max_hops: int = Field(default=PATH_HOPS_DEF, ge=1)
    max_paths: int = Field(default=PATH_MAX_DEF, ge=1)
    edge_kinds: List[str] = Field(
        default_factory=lambda: sorted(
            {"inheritance", "opposition"} | KNOWN_SEMANTIC_KINDS
        )
    )


@router.post("/paths/explain")
async def graph_paths_explain(
    body: PathsExplainBody,
    request: Request,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
    graph_id: str = Depends(_resolve_graph_id),
) -> Dict[str, Any]:
    a = _parse_uuid(body.from_node_id)
    b = _parse_uuid(body.to_node_id)
    na = ctx.node_repo.get_by_id(graph_id, str(a))
    nb = ctx.node_repo.get_by_id(graph_id, str(b))
    if na is None or nb is None:
        raise HTTPException(status_code=404, detail="node_not_found")

    max_hops = _clamp_int(body.max_hops, PATH_HOPS_DEF, PATH_HOPS_MIN, PATH_HOPS_MAX)
    max_paths = _clamp_int(body.max_paths, PATH_MAX_DEF, PATH_MAX_MIN, PATH_MAX_MAX)

    allowed = {
        k
        for k in body.edge_kinds
        if k in ({"inheritance", "opposition"} | KNOWN_SEMANTIC_KINDS)
    }
    if not allowed:
        allowed = {"inheritance", "opposition"} | KNOWN_SEMANTIC_KINDS

    result = shortest_path_undirected(
        ctx.session,
        ctx.tenant_id,
        graph_id,
        a,
        b,
        allowed,
        max_hops,
    )
    gh = _best_effort_graph_hash(ctx, graph_id)

    if not result:
        kinds = sorted(allowed)
        return {
            "snapshot": _build_snapshot(
                ctx, graph_id, graph_hash=gh, consistent_read=True
            ),
            "from_node_id": str(a),
            "to_node_id": str(b),
            "path_found": False,
            "paths": [],
            "explanation": {
                "summary": f"no path within {max_hops} hops ({','.join(kinds)})",
                "hops": 0,
                "edge_kinds_used": kinds,
                "relation_distance": None,
            },
        }

    path_nodes, path_edges = result
    hops = len(path_nodes) - 1
    kinds_used = sorted({e.kind for e in path_edges})
    summary = f"path, {hops} hop(s), kinds={','.join(kinds_used)}"

    paths_out = [
        {
            "node_ids": [str(x) for x in path_nodes],
            "edges": [_serialize_edge(e) for e in path_edges],
        }
    ]
    _ = max_paths

    return {
        "snapshot": _build_snapshot(ctx, graph_id, graph_hash=gh, consistent_read=True),
        "from_node_id": str(a),
        "to_node_id": str(b),
        "path_found": True,
        "paths": paths_out,
        "explanation": {
            "summary": summary,
            "hops": hops,
            "edge_kinds_used": kinds_used,
            "relation_distance": hops,
        },
    }


__all__ = ["router"]
