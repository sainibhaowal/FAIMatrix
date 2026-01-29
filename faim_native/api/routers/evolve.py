"""FAIM-Native API: Evolve Router.

POST /v1/evolve - Run evolution cycle on graph.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["evolve"])


# =============================================================================
# Request/Response Models
# =============================================================================


class EvolveRequest(BaseModel):
    """Evolve request body."""

    graph_id: str
    profile: str = "strict"
    persist_mode: str = "relaxed"


class EvolveResponse(BaseModel):
    """Evolve response."""

    status: str
    graph_version: int
    merges: int
    prunes: int
    diagnostics: Optional[Dict[str, Any]] = None
    events_emitted: List[str]
    latency_ms: int
    error: Optional[str] = None


# =============================================================================
# Evolve Endpoint
# =============================================================================


@router.post("/evolve", response_model=EvolveResponse)
async def evolve_graph(
    request: EvolveRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> EvolveResponse:
    """Run one evolution cycle on the graph.

    Uses lock manager to prevent concurrent evolution.
    Returns MetricsSnapshot (Stage-4.1.1 contract).
    """
    try:
        from orchestration.evolve_flow import FAIMProfile, PersistMode, run_evolve

        profile = FAIMProfile(request.profile.lower())
        persist_mode = PersistMode(request.persist_mode.lower())

        result = run_evolve(
            graph_id=request.graph_id,
            profile=profile,
            persist_mode=persist_mode,
            node_repo=ctx.node_repo,
            edge_repo=ctx.edge_repo,
            event_repo=ctx.event_repo,
            gv_repo=ctx.gv_repo,
        )

        return EvolveResponse(
            status=result.status,
            graph_version=result.graph_version,
            merges=result.merges,
            prunes=result.prunes,
            diagnostics=result.diagnostics,
            events_emitted=result.events_emitted,
            latency_ms=result.latency_ms,
            error=result.error,
        )

    except Exception as e:
        logger.error(f"Evolve failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


__all__ = ["router"]
