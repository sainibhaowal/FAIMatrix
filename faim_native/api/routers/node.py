"""FAIM-Native API: Node Router (Stage-8 Enhanced).

GET /v1/node/{node_id} - Get node details
GET /v1/node/{node_id}/explain - Get node explain (parents, fractions, evidence)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/node", tags=["node"])


# =============================================================================
# Response Models
# =============================================================================


class NodeDetail(BaseModel):
    """Node details response."""

    node_id: str
    graph_id: str
    kind: str
    level: int
    vector_hash: str
    residual: float
    touch_count: int
    raw_id: Optional[str] = None
    block_id: Optional[str] = None
    anchor: Optional[Dict[str, Any]] = None
    opp_signature: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ParentInfo(BaseModel):
    """Parent node with fraction."""

    parent_id: str
    fraction: float
    kind: str


class NodeExplain(BaseModel):
    """Node explanation with parents and events."""

    node_id: str
    parents: List[ParentInfo]
    fractions_sum: float
    recent_events: List[Dict[str, Any]]


# =============================================================================
# Node Detail Endpoint
# =============================================================================


@router.get("/{node_id}")
async def get_node(
    node_id: str,
    graph_id: str = Query(...),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> NodeDetail:
    """Get node details.

    Args:
        node_id: Node UUID.
        graph_id: Graph identifier.

    Returns:
        Node details including vector_hash, residual, level, etc.
    """
    node = ctx.node_repo.get_by_id(graph_id, node_id)

    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")

    return NodeDetail(
        node_id=str(node.node_id),
        graph_id=node.graph_id,
        kind=node.kind,
        level=node.level,
        vector_hash=node.vector_hash,
        residual=node.residual / 1e9 if node.residual else 0.0,
        touch_count=node.touch_count,
        raw_id=node.raw_id,
        block_id=node.block_id,
        anchor=node.anchor_json,
        opp_signature=node.opp_signature,
        created_at=node.created_at.isoformat() if node.created_at else None,
        updated_at=node.updated_at.isoformat() if node.updated_at else None,
    )


# =============================================================================
# Node Explain Endpoint
# =============================================================================


@router.get("/{node_id}/explain")
async def explain_node(
    node_id: str,
    graph_id: str = Query(...),
    limit_events: int = Query(10, ge=1, le=100),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> NodeExplain:
    """Explain a node: parents, fractions, recent events.

    Useful for understanding node provenance and inheritance.
    """
    node = ctx.node_repo.get_by_id(graph_id, node_id)

    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")

    # Get parent edges (INHERIT edges where dst_node_id = node_id)
    parents = []
    fractions_sum = 0.0

    try:
        parent_edges = ctx.edge_repo.get_parents(graph_id, node_id)
        for edge in parent_edges:
            fraction = edge.weight / 1e9 if edge.weight else 0.0
            fractions_sum += fraction

            parent_node = ctx.node_repo.get_by_id(graph_id, str(edge.src_node_id))
            parents.append(
                ParentInfo(
                    parent_id=str(edge.src_node_id),
                    fraction=fraction,
                    kind=parent_node.kind if parent_node else "unknown",
                )
            )
    except Exception as e:
        logger.warning(f"Failed to get parent edges: {e}")

    # Get recent events affecting this node
    recent_events = []
    try:
        all_events = ctx.event_repo.get_by_seq(
            ctx.session,
            graph_id=graph_id,
            after_seq=0,
            limit=100,
        )

        # Filter events mentioning this node
        for event in reversed(all_events):
            payload = event.payload or {}
            if (
                payload.get("node_id") == node_id
                or node_id in str(payload.get("nodes", []))
                or payload.get("vector_hash") == node.vector_hash
            ):
                recent_events.append(
                    {
                        "seq": event.seq,
                        "kind": event.kind,
                        "ts": event.ts.isoformat() if event.ts else None,
                        "payload_keys": list(payload.keys()),
                    }
                )
                if len(recent_events) >= limit_events:
                    break
    except Exception as e:
        logger.warning(f"Failed to get node events: {e}")

    return NodeExplain(
        node_id=node_id,
        parents=parents,
        fractions_sum=round(fractions_sum, 6),
        recent_events=recent_events,
    )


__all__ = ["router"]
