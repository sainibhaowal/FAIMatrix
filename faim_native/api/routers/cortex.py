"""FAIM Cortex turn router."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context, get_tenant_id  # noqa: E402
from core.cortex.history import (  # noqa: E402
    list_cortex_sessions,
    load_recent_cortex_turns,
)
from core.cortex.runtime import run_cortex_turn  # noqa: E402
from core.cortex.schemas import (  # noqa: E402
    CortexSessionSummary,
    CortexTurnRequest,
    CortexTurnResponse,
    CortexTurnSummary,
)  # noqa: E402
from orchestration.ingest_flow import FAIMProfile  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cortex", tags=["cortex"])

PROFILE_MAP = {
    "STRICT": FAIMProfile.STRICT,
    "RELAXED": FAIMProfile.RELAXED,
    "FAST": FAIMProfile.FAST,
    "strict": FAIMProfile.STRICT,
    "relaxed": FAIMProfile.RELAXED,
    "fast": FAIMProfile.FAST,
}


class CortexSessionListResponse(BaseModel):
    graph_id: str
    total: int
    items: list[CortexSessionSummary]


class CortexTurnListResponse(BaseModel):
    graph_id: str
    session_id: str
    total: int
    items: list[CortexTurnSummary]


@router.post("/turn", response_model=CortexTurnResponse)
async def cortex_turn(
    request: CortexTurnRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> CortexTurnResponse:
    """Execute a structured Cortex turn."""

    try:
        profile = PROFILE_MAP.get(request.profile, FAIMProfile.RELAXED)
        result = await run_cortex_turn(
            session=ctx.session,
            tenant_id=tenant_id,
            graph_id=request.graph_id,
            query_text=request.query_text,
            k=request.k,
            profile=profile,
            answer_mode=request.answer_mode,
            session_id=request.session_id,
            return_explain=request.return_explain,
            think_enabled=request.think_enabled,
        )
        ctx.session.commit()
        return result
    except HTTPException:
        if ctx.session is not None:
            ctx.session.rollback()
        raise
    except Exception as e:
        if ctx.session is not None:
            ctx.session.rollback()
        logger.error(f"Cortex turn failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sessions", response_model=CortexSessionListResponse)
async def cortex_sessions(
    graph_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> CortexSessionListResponse:
    """List recent Cortex sessions for a graph."""

    items = list_cortex_sessions(
        ctx.session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        limit=limit,
    )
    return CortexSessionListResponse(graph_id=graph_id, total=len(items), items=items)


@router.get("/sessions/{session_id}/turns", response_model=CortexTurnListResponse)
async def cortex_session_turns(
    session_id: str,
    graph_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> CortexTurnListResponse:
    """List recent turns for one Cortex session."""

    items = load_recent_cortex_turns(
        ctx.session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        session_id=session_id,
        limit=limit,
    )
    return CortexTurnListResponse(
        graph_id=graph_id,
        session_id=session_id,
        total=len(items),
        items=items,
    )
