"""FAIM-Native API: Metrics Router.

GET /v1/metrics/scorecard - Get metrics snapshot for graph.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/metrics", tags=["metrics"])


# =============================================================================
# Response Models
# =============================================================================


class MetricsScorecard(BaseModel):
    """Metrics scorecard response."""

    graph_id: str
    graph_version: int
    graph_hash: str

    # Fractal metrics (Stage-4.1)
    dimension_D: Optional[float] = None
    entropy_H: Optional[float] = None
    pressure_lambda: Optional[float] = None

    # Health metrics
    node_count: int
    edge_count: int
    redundancy: Optional[float] = None
    novelty: Optional[float] = None
    energy: Optional[float] = None

    # Timestamps
    computed_at: Optional[str] = None


# =============================================================================
# Metrics Endpoint
# =============================================================================


@router.get("/scorecard")
async def get_scorecard(
    graph_id: str = Query(...),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> MetricsScorecard:
    """Get the latest metrics scorecard for a graph.

    Returns MetricsSnapshot from the latest DIAGNOSTICS_SNAPSHOT event,
    or computes on demand via fractal_physics.
    """
    try:
        # Try to get from latest snapshot event
        events = ctx.event_repo.get_by_seq(
            ctx.session,
            graph_id=graph_id,
            after_seq=0,
            limit=500,
        )

        diagnostics_event = None
        for e in reversed(events):
            if e.kind == "DIAGNOSTICS_SNAPSHOT":
                diagnostics_event = e
                break

        # Get graph version
        gv = ctx.gv_repo.get_or_create(ctx.session, graph_id)

        # Get counts
        node_count = ctx.node_repo.count(graph_id)
        edge_count = ctx.edge_repo.count(graph_id)

        if diagnostics_event:
            payload = diagnostics_event.payload or {}
            metrics = payload.get("metrics", {})

            return MetricsScorecard(
                graph_id=graph_id,
                graph_version=gv.version,
                graph_hash=payload.get("graph_hash", ""),
                dimension_D=metrics.get("D"),
                entropy_H=metrics.get("H"),
                pressure_lambda=metrics.get("lambda"),
                node_count=node_count,
                edge_count=edge_count,
                redundancy=metrics.get("redundancy"),
                novelty=metrics.get("novelty"),
                energy=metrics.get("energy"),
                computed_at=(
                    diagnostics_event.ts.isoformat() if diagnostics_event.ts else None
                ),
            )

        # No snapshot found, return basic info
        return MetricsScorecard(
            graph_id=graph_id,
            graph_version=gv.version,
            graph_hash="",
            node_count=node_count,
            edge_count=edge_count,
        )

    except Exception as e:
        logger.error(f"Get scorecard failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


__all__ = ["router"]
