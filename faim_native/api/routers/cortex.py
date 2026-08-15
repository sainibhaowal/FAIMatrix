"""FAIM Cortex turn router."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context, get_tenant_id  # noqa: E402
from core.cortex.history import (  # noqa: E402
    delete_cortex_session,
    list_cortex_sessions,
    load_recent_cortex_turns,
)
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
        from core.cortex.runtime import run_cortex_turn
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


@router.delete("/sessions/{session_id}")
async def cortex_delete_session(
    session_id: str,
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
):
    """Delete a Cortex session and its associated turns."""

    try:
        success = delete_cortex_session(
            ctx.session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            session_id=session_id,
        )
        return {"session_id": session_id, "deleted": success}
    except Exception as e:
        if ctx.session is not None:
            ctx.session.rollback()
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# -----------------------------------------------------------------------------
# Human-in-the-loop tool approval ledger
# -----------------------------------------------------------------------------


class CortexApprovalListResponse(BaseModel):
    tenant_id: str
    total: int
    items: list[dict]


class CortexApprovalDecisionRequest(BaseModel):
    note: str | None = None


class CortexApprovalProposeRequest(BaseModel):
    tool_name: str
    graph_id: str
    args: dict = {}
    reason: str = ""
    session_id: str | None = None
    turn_id: str | None = None


@router.post("/tool-approvals/propose", response_model=dict)
async def cortex_propose_approval(
    request: CortexApprovalProposeRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
):
    """Propose a mutating storage action; it waits for human approval."""
    from core.cortex.cortex_storage_tools import propose_approval

    allowed = {
        "faim_storage_upload",
        "faim_storage_delete",
        "faim_storage_reingest",
        "faim_storage_retry",
    }
    if request.tool_name not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"tool_name must be one of {sorted(allowed)}",
        )
    try:
        result = propose_approval(
            ctx.session,
            tenant_id=tenant_id,
            graph_id=request.graph_id,
            tool_name=request.tool_name,
            args=request.args,
            reason=request.reason,
            session_id=request.session_id,
            turn_id=request.turn_id,
        )
        ctx.session.commit()
        return result
    except Exception as e:
        if ctx.session is not None:
            ctx.session.rollback()
        logger.error(f"Failed to propose tool approval: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/storage/status", response_model=dict)
async def cortex_storage_status(
    graph_id: str | None = Query(default=None),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
):
    """Live tenant storage summary exposed to the Cortex agent."""
    from core.cortex.cortex_storage_tools import faim_storage_status

    return await faim_storage_status(tenant_id, graph_id)


@router.get("/storage/orphan-scan", response_model=dict)
async def cortex_storage_orphan_scan(
    graph_id: str | None = Query(default=None),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
):
    """Scan for orphaned graph artifacts (read-only health check)."""
    from core.cortex.cortex_storage_tools import faim_storage_orphan_scan

    return await faim_storage_orphan_scan(tenant_id, graph_id)


@router.get("/tool-approvals", response_model=CortexApprovalListResponse)
async def cortex_list_approvals(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
) -> CortexApprovalListResponse:
    """List human-in-the-loop approval requests for this tenant."""

    from core.cortex.cortex_storage_tools import list_approvals

    items = list_approvals(
        ctx.session,
        tenant_id=tenant_id,
        status=status,
        limit=limit,
    )
    return CortexApprovalListResponse(tenant_id=tenant_id, total=len(items), items=items)


@router.post("/tool-approvals/{approval_id}/approve")
async def cortex_approve_approval(
    approval_id: int,
    request: CortexApprovalDecisionRequest | None = None,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
):
    """Approve a pending tool action and execute it."""
    from core.cortex.cortex_storage_tools import approve_approval, execute_approval

    note = request.note if request is not None else None
    try:
        approved = approve_approval(
            ctx.session,
            approval_id=approval_id,
            tenant_id=tenant_id,
            decision_by="operator",
        )
        # Approve path re-opens its own session since the approval rows and
        # execution share the request's DB session; run on the request session.
        ctx.session.expire_all()
        result = execute_approval(
            ctx.session,
            approval_id=approval_id,
            tenant_id=tenant_id,
        )
        ctx.session.commit()
        return {"approval": approved, "execution": result}
    except ValueError as e:
        if ctx.session is not None:
            ctx.session.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        if ctx.session is not None:
            ctx.session.rollback()
        logger.error(f"Failed to approve tool approval {approval_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/tool-approvals/{approval_id}/reject")
async def cortex_reject_approval(
    approval_id: int,
    request: CortexApprovalDecisionRequest | None = None,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
):
    """Reject a pending tool action without executing it."""
    from core.cortex.cortex_storage_tools import reject_approval

    note = request.note if request is not None else None
    try:
        result = reject_approval(
            ctx.session,
            approval_id=approval_id,
            tenant_id=tenant_id,
            decision_by="operator",
            note=note,
        )
        ctx.session.commit()
        return result
    except ValueError as e:
        if ctx.session is not None:
            ctx.session.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        if ctx.session is not None:
            ctx.session.rollback()
        logger.error(f"Failed to reject tool approval {approval_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# -----------------------------------------------------------------------------
# WebSocket Chat Endpoint for Real-time Cortex Conversation
# -----------------------------------------------------------------------------


class CortexWSMessage(BaseModel):
    """WebSocket message schema for Cortex chat."""
    type: str  # "user_message", "agent_response", "tool_call", "tool_result", "error", "session_created"
    session_id: Optional[str] = None
    graph_id: str
    content: Optional[str] = None
    payload: Optional[dict] = None


class CortexWSManager:
    """Manages active WebSocket connections for Cortex chat."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"Cortex WS connected: {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"Cortex WS disconnected: {session_id}")

    async def send_message(self, session_id: str, message: CortexWSMessage):
        if session_id in self.active_connections:
            ws = self.active_connections[session_id]
            try:
                await ws.send_text(message.model_dump_json())
            except Exception as e:
                logger.error(f"Failed to send WS message to {session_id}: {e}")

    async def broadcast(self, message: CortexWSMessage):
        for ws in self.active_connections.values():
            try:
                await ws.send_text(message.model_dump_json())
            except Exception as e:
                logger.error(f"Failed to broadcast WS message: {e}")


ws_manager = CortexWSManager()


async def get_ws_tenant_id(websocket: WebSocket) -> str:
    """Extract tenant_id from WebSocket query params or headers."""
    # Check query params first
    tenant_id = websocket.query_params.get("tenant_id")
    if tenant_id:
        return tenant_id
    # Check headers
    tenant_id = websocket.headers.get("x-tenant-id")
    if tenant_id:
        return tenant_id
    # Check for API key in query params
    api_key = websocket.query_params.get("api_key")
    if api_key:
        # Could validate API key here, for now return default
        return "default"
    return "default"


@router.websocket("/ws/chat")
async def cortex_ws_chat(
    websocket: WebSocket,
    graph_id: str = Query(...),
    session_id: Optional[str] = Query(default=None),
):
    """WebSocket endpoint for real-time Cortex chat conversation.

    Message flow:
    1. Client connects with graph_id (and optional session_id)
    2. Server accepts, creates/loads session
    3. Client sends: {"type": "user_message", "content": "..."}
    3. Server processes via Cortex agent, streams responses:
       - {"type": "agent_response", "content": "..."}
       - {"type": "tool_call", "payload": {"tool": "...", "args": {...}}}
       - {"type": "tool_result", "payload": {"tool": "...", "result": {...}}}
    4. Client can send tool approval decisions:
       - {"type": "approve_tool", "payload": {"approval_id": 1}}
       - {"type": "reject_tool", "payload": {"approval_id": 1, "note": "..."}}
    """
    tenant_id = await get_ws_tenant_id(websocket)

    # Use session_id from query or generate new
    actual_session_id = session_id or f"ws_{graph_id}_{tenant_id[:8]}"

    await ws_manager.connect(actual_session_id, websocket)

    try:
        # Send initial session info
        await ws_manager.send_message(actual_session_id, CortexWSMessage(
            type="session_created",
            session_id=actual_session_id,
            graph_id=graph_id,
            payload={"tenant_id": tenant_id, "graph_id": graph_id}
        ))

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")

                if msg_type == "user_message":
                    content = msg.get("content", "")
                    if content:
                        await _process_cortex_message(
                            websocket=websocket,
                            tenant_id=tenant_id,
                            graph_id=graph_id,
                            session_id=actual_session_id,
                            content=content,
                        )
                elif msg_type == "approve_tool":
                    approval_id = msg.get("payload", {}).get("approval_id")
                    if approval_id:
                        await _approve_tool_via_ws(tenant_id, approval_id, actual_session_id)
                elif msg_type == "reject_tool":
                    approval_id = msg.get("payload", {}).get("approval_id")
                    note = msg.get("payload", {}).get("note")
                    if approval_id:
                        await _reject_tool_via_ws(tenant_id, approval_id, note, actual_session_id)
                elif msg_type == "ping":
                    await ws_manager.send_message(actual_session_id, CortexWSMessage(
                        type="pong", session_id=actual_session_id, graph_id=graph_id
                    ))
                else:
                    await ws_manager.send_message(actual_session_id, CortexWSMessage(
                        type="error",
                        session_id=actual_session_id,
                        graph_id=graph_id,
                        payload={"message": f"Unknown message type: {msg_type}"}
                    ))
            except json.JSONDecodeError:
                await ws_manager.send_message(actual_session_id, CortexWSMessage(
                    type="error",
                    session_id=actual_session_id,
                    graph_id=graph_id,
                    payload={"message": "Invalid JSON"}
                ))
            except Exception as e:
                logger.error(f"WS message processing error: {e}")
                await ws_manager.send_message(actual_session_id, CortexWSMessage(
                    type="error",
                    session_id=actual_session_id,
                    graph_id=graph_id,
                    payload={"message": str(e)}
                ))

    except WebSocketDisconnect:
        ws_manager.disconnect(actual_session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(actual_session_id)


async def _process_cortex_message(
    websocket: WebSocket,
    tenant_id: str,
    graph_id: str,
    session_id: str,
    content: str,
):
    """Process a user message through Cortex agent and stream response via WebSocket."""
    from core.cortex.runtime import run_cortex_turn
    from api.deps import get_faim_context, get_tenant_id
    from core.cortex.schemas import CortexTurnRequest
    from orchestration.ingest_flow import FAIMProfile

    # Create a mock request context for the WS session
    # In production, this would use a proper session context
    from runtime.context import get_repos, close_session

    repos = get_repos(tenant_id)
    ctx_session = repos["session"]

    try:
        # Echo user message back
        await ws_manager.send_message(session_id, CortexWSMessage(
            type="user_message_echo",
            session_id=session_id,
            graph_id=graph_id,
            content=content,
        ))

        # Run Cortex turn
        request = CortexTurnRequest(
            graph_id=graph_id,
            query_text=content,
            k=15,
            profile=FAIMProfile.RELAXED,
            answer_mode="auto",
            session_id=session_id,
            return_explain=True,
            think_enabled=True,
        )

        # Send thinking indicator
        await ws_manager.send_message(session_id, CortexWSMessage(
            type="thinking",
            session_id=session_id,
            graph_id=graph_id,
            payload={"message": "Cortex is thinking..."}
        ))

        result = await run_cortex_turn(
            session=ctx_session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            query_text=content,
            k=15,
            profile=FAIMProfile.RELAXED,
            answer_mode="auto",
            session_id=session_id,
            return_explain=True,
            think_enabled=True,
        )
        ctx_session.commit()

        # Send agent response
        await ws_manager.send_message(session_id, CortexWSMessage(
            type="agent_response",
            session_id=session_id,
            graph_id=graph_id,
            content=result.answer.direct_answer if result.answer else result.narrative,
            payload={
                "turn_id": result.turn_id,
                "session_id": result.session_id,
                "answer_mode": result.answer_mode,
                "task_type": result.task_type.value if result.task_type else None,
                "brain_state": result.brain_state.model_dump() if result.brain_state else None,
            }
        ))

        # Check for tool approvals needed
        if result.brain_state and result.brain_state.reasoning_tree:
            _check_tool_approvals_in_reasoning(result.brain_state, session_id, graph_id, tenant_id)

    except Exception as e:
        logger.error(f"Cortex WS processing error: {e}")
        await ws_manager.send_message(session_id, CortexWSMessage(
            type="error",
            session_id=session_id,
            graph_id=graph_id,
            payload={"message": str(e)}
        ))
    finally:
        close_session(ctx_session)


def _check_tool_approvals_in_reasoning(brain_state, session_id: str, graph_id: str, tenant_id: str):
    """Check reasoning tree for tool calls that need approval."""
    # This is a simplified check - in reality would parse the reasoning tree
    # for storage tool calls that need human approval
    pass


async def _approve_tool_via_ws(tenant_id: str, approval_id: int, session_id: str):
    """Approve a tool action via WebSocket."""
    from core.cortex.cortex_storage_tools import approve_approval, execute_approval
    from runtime.context import get_repos, close_session

    repos = get_repos(tenant_id)
    ctx_session = repos["session"]

    try:
        approved = approve_approval(ctx_session, approval_id=approval_id, tenant_id=tenant_id, decision_by="operator_ws")
        ctx_session.expire_all()
        result = execute_approval(ctx_session, approval_id=approval_id, tenant_id=tenant_id)
        ctx_session.commit()

        await ws_manager.send_message(session_id, CortexWSMessage(
            type="tool_approved",
            session_id=session_id,
            graph_id="",
            payload={"approval": approved, "execution": result}
        ))
    except Exception as e:
        logger.error(f"WS tool approve error: {e}")
        await ws_manager.send_message(session_id, CortexWSMessage(
            type="error", session_id=session_id, graph_id="", payload={"message": str(e)}
        ))
    finally:
        close_session(ctx_session)


async def _reject_tool_via_ws(tenant_id: str, approval_id: int, note: Optional[str], session_id: str):
    """Reject a tool action via WebSocket."""
    from core.cortex.cortex_storage_tools import reject_approval
    from runtime.context import get_repos, close_session

    repos = get_repos(tenant_id)
    ctx_session = repos["session"]

    try:
        result = reject_approval(ctx_session, approval_id=approval_id, tenant_id=tenant_id, decision_by="operator_ws", note=note)
        ctx_session.commit()

        await ws_manager.send_message(session_id, CortexWSMessage(
            type="tool_rejected",
            session_id=session_id,
            graph_id="",
            payload=result
        ))
    except Exception as e:
        logger.error(f"WS tool reject error: {e}")
        await ws_manager.send_message(session_id, CortexWSMessage(
            type="error", session_id=session_id, graph_id="", payload={"message": str(e)}
        ))
    finally:
        close_session(ctx_session)

