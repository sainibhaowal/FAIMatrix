"""FAIM-Native API: Metrics Router.

GET /v1/metrics/scorecard - Get metrics snapshot for graph.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _payload_dict(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return {}


def _metric_value(
    payload: Dict[str, Any],
    metrics_obj: Dict[str, Any],
    *,
    metric_keys: tuple[str, ...],
    payload_keys: tuple[str, ...],
) -> Optional[float]:
    for key in metric_keys:
        if key in metrics_obj and metrics_obj[key] is not None:
            try:
                return float(metrics_obj[key])
            except (TypeError, ValueError):
                pass
    for key in payload_keys:
        if key in payload and payload[key] is not None:
            try:
                return float(payload[key])
            except (TypeError, ValueError):
                pass
    return None


def _metric_text_value(
    payload: Dict[str, Any],
    *,
    payload_keys: tuple[str, ...],
) -> str:
    for key in payload_keys:
        value = payload.get(key)
        if value:
            return str(value)
    return ""


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
            payload = _payload_dict(diagnostics_event.payload)
            metrics = _payload_dict(payload.get("metrics"))

            return MetricsScorecard(
                graph_id=graph_id,
                graph_version=gv.version,
                graph_hash=_metric_text_value(
                    payload,
                    payload_keys=("graph_hash", "diagnostics_hash"),
                ),
                dimension_D=_metric_value(
                    payload,
                    metrics,
                    metric_keys=("D", "d", "D_hat", "d_hat"),
                    payload_keys=("D_hat", "D", "d_hat", "d"),
                ),
                entropy_H=_metric_value(
                    payload,
                    metrics,
                    metric_keys=("H", "h", "H_hat", "h_hat"),
                    payload_keys=("H_hat", "H", "h_hat", "h"),
                ),
                pressure_lambda=_metric_value(
                    payload,
                    metrics,
                    metric_keys=("lambda", "lambda_hat"),
                    payload_keys=("lambda_hat", "lambda"),
                ),
                node_count=node_count,
                edge_count=edge_count,
                redundancy=_metric_value(
                    payload,
                    metrics,
                    metric_keys=("redundancy", "R", "redundancy_R"),
                    payload_keys=("redundancy_R", "redundancy", "R"),
                ),
                novelty=_metric_value(
                    payload,
                    metrics,
                    metric_keys=("novelty", "N", "novelty_N"),
                    payload_keys=("novelty_N", "novelty", "N"),
                ),
                energy=_metric_value(
                    payload,
                    metrics,
                    metric_keys=("energy", "E", "energy_E"),
                    payload_keys=("energy_E", "energy", "E"),
                ),
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
