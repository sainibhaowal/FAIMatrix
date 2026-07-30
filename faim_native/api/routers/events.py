"""FAIM-Native API: Events Router (Stage-7.1 Hardened).

SSE event stream + pagination endpoints.

Stage-7.1 improvements:
- Short-lived DB sessions per page fetch
- Bounded paging
- Sleep on empty
- Clean disconnect handling

GET /v1/events - Event pagination
GET /v1/events/stream - SSE stream (UI-critical)
GET /v1/events/latest - Last event seq
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context, get_tenant_id  # noqa: E402
from store.journal.event_journal import truncate_payload  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


# =============================================================================
# Constants
# =============================================================================

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 50
POLL_INTERVAL_SECONDS = 1.0
HEARTBEAT_INTERVAL_SECONDS = 15.0
MAX_EMPTY_POLLS = 300  # Stop after 5 minutes of no events


class FigInteractionBody(BaseModel):
    """Best-effort FIG interaction pulse payload.

    The UI sends a deterministic pulse-v2 summary. The backend stores it as an
    append-only FIG_INTERACTION event so the runtime has an auditable trail for
    selection, hover, overlay, mode, drawer, and timeline changes.
    """

    pulse: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Short-lived Session Helper
# =============================================================================


@contextmanager
def _get_fresh_session():
    """Get a fresh, short-lived database session."""
    from runtime.context import close_session, get_session

    session = get_session()
    try:
        yield session
    finally:
        close_session(session)


# =============================================================================
# Event Pagination
# =============================================================================


@router.get("")
async def list_events(
    graph_id: str,
    after_seq: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> Dict[str, Any]:
    """List events for a graph with pagination.

    Args:
        graph_id: Graph identifier.
        after_seq: Return events with seq > after_seq.
        limit: Maximum events to return (bounded to MAX_PAGE_SIZE).

    Returns:
        {"events": [...], "has_more": bool, "next_seq": int}
    """
    # Bound limit defensively instead of hard-rejecting larger client values.
    # This keeps API behavior backward-compatible for older UIs that may send
    # larger limits (for example 120) while preserving server-side cap.
    limit = min(limit, MAX_PAGE_SIZE)

    events = ctx.event_repo.get_by_seq(
        ctx.session,
        graph_id=graph_id,
        after_seq=after_seq,
        limit=limit + 1,  # Fetch one extra to check has_more
    )

    has_more = len(events) > limit
    if has_more:
        events = events[:limit]

    next_seq = events[-1].seq if events else after_seq

    return {
        "graph_id": graph_id,
        "tenant_id": ctx.tenant_id,
        "events": [
            {
                "seq": e.seq,
                "id": str(e.id),
                "kind": e.kind,
                "ts": e.ts.isoformat() if e.ts else None,
                "payload": e.payload,
                "checksum": e.checksum,
            }
            for e in events
        ],
        "has_more": has_more,
        "next_seq": next_seq,
        "count": len(events),
    }


# =============================================================================
# Latest Event
# =============================================================================


@router.get("/latest")
async def get_latest_event(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> Dict[str, Any]:
    """Get the latest event info for a graph.

    Returns:
        {"last_seq": int, "last_kind": str, "snapshot_hash": str|null}
    """
    # Real total count via SQL COUNT — not capped by pagination
    total_count = ctx.event_repo.count(ctx.session, graph_id=graph_id)

    # Fetch only the last few events to find latest seq/kind and snapshot hash
    recent = ctx.event_repo.get_by_seq(
        ctx.session,
        graph_id=graph_id,
        after_seq=0,
        limit=50,
    )

    last_event = recent[-1] if recent else None

    snapshot_hash = None
    for e in reversed(recent):
        if e.kind == "DIAGNOSTICS_SNAPSHOT":
            snapshot_hash = e.payload.get("graph_hash")
            break

    return {
        "graph_id": graph_id,
        "last_seq": last_event.seq if last_event else 0,
        "last_kind": last_event.kind if last_event else None,
        "last_ts": last_event.ts.isoformat() if last_event and last_event.ts else None,
        "snapshot_hash": snapshot_hash,
        "event_count": total_count,
    }


# =============================================================================
# FIG Interaction Pulse Write Path
# =============================================================================


@router.post("/fig-interaction")
async def append_fig_interaction_event(
    graph_id: str,
    body: FigInteractionBody,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> Dict[str, Any]:
    """Append a best-effort FIG interaction pulse to the event journal.

    This is intentionally non-blocking from a product perspective: if the
    append fails, the UI can continue because the live pulse is still rendered
    from local deterministic state and query explain payloads.
    """

    payload = body.pulse if isinstance(body.pulse, dict) else {}
    payload = truncate_payload(payload)
    payload.setdefault("protocol", "pulse-v2")
    payload.setdefault("source", "fig_view")
    payload.setdefault("kind", "FIG_INTERACTION")
    payload.setdefault("graph_id", graph_id)
    payload.setdefault("tenant_id", ctx.tenant_id)
    payload.setdefault("ingest_mode", "best_effort")

    try:
        event = ctx.event_repo.emit(
            ctx.session,
            graph_id,
            "FIG_INTERACTION",
            payload,
        )
        ctx.session.commit()
        return {
            "stored": True,
            "graph_id": graph_id,
            "tenant_id": ctx.tenant_id,
            "seq": event.seq,
            "event_id": str(event.id),
            "ts": event.ts.isoformat() if event.ts else None,
            "protocol": payload.get("protocol"),
        }
    except Exception as exc:  # nosec B110
        logger.warning("FIG interaction append failed: graph=%s err=%s", graph_id, exc)
        try:
            ctx.session.rollback()
        except Exception:  # nosec B110
            pass
        return {
            "stored": False,
            "graph_id": graph_id,
            "tenant_id": ctx.tenant_id,
            "error": "pulse_append_failed",
        }


# =============================================================================
# SSE Event Stream (Stage-7.1 Hardened)
# =============================================================================


async def _event_generator(
    tenant_id: str,
    graph_id: str,
    after_seq: int,
) -> AsyncGenerator[str, None]:
    """Generate SSE events from event journal.

    Stage-7.1 improvements:
    - Uses short-lived DB sessions per fetch (no session leaks)
    - Bounded paging (MAX_PAGE_SIZE)
    - Sleep on empty to reduce load
    - Heartbeat every 15s
    - Clean exit after extended inactivity

    Args:
        tenant_id: Tenant for session scoping.
        graph_id: Graph to stream.
        after_seq: Resume point.
    """
    from store.pg.repos.event_repo import EventRepo

    current_seq = after_seq
    last_heartbeat = asyncio.get_event_loop().time()
    empty_poll_count = 0

    try:
        while True:
            try:
                # Use short-lived session per fetch
                with _get_fresh_session() as session:
                    event_repo = EventRepo()
                    events = event_repo.get_by_seq(
                        session,
                        graph_id=graph_id,
                        after_seq=current_seq,
                        limit=MAX_PAGE_SIZE,
                    )

                if events:
                    empty_poll_count = 0

                    for event in events:
                        # Format as SSE
                        sse_data = {
                            "seq": event.seq,
                            "id": str(event.id),
                            "kind": event.kind,
                            "ts": event.ts.isoformat() if event.ts else None,
                            "payload": event.payload,
                        }

                        yield f"id: {event.seq}\n"
                        yield f"event: {event.kind}\n"
                        yield f"data: {json.dumps(sse_data)}\n\n"

                        current_seq = event.seq

                    last_heartbeat = asyncio.get_event_loop().time()
                else:
                    empty_poll_count += 1

                    # Check if heartbeat needed
                    now = asyncio.get_event_loop().time()
                    if now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                        yield "event: ping\n"
                        yield f"data: {json.dumps({'ts': datetime.now(timezone.utc).isoformat(), 'last_seq': current_seq})}\n\n"
                        last_heartbeat = now

                    # Exit after extended inactivity
                    if empty_poll_count >= MAX_EMPTY_POLLS:
                        yield "event: timeout\n"
                        yield f"data: {json.dumps({'message': 'Stream timeout after inactivity', 'last_seq': current_seq})}\n\n"
                        break

                # Wait before next poll
                await asyncio.sleep(POLL_INTERVAL_SECONDS)

            except asyncio.CancelledError:
                # Clean disconnect handling
                logger.info(f"SSE stream cancelled for graph={graph_id}")
                yield "event: disconnect\n"
                yield f"data: {json.dumps({'message': 'Stream closed', 'last_seq': current_seq})}\n\n"
                break

            except Exception as e:
                logger.error(f"SSE stream error: {e}")
                yield "event: error\n"
                yield f"data: {json.dumps({'error': str(e), 'last_seq': current_seq})}\n\n"
                break

    except GeneratorExit:
        # Client disconnected
        logger.info(f"SSE client disconnected for graph={graph_id}")


@router.get("/stream")
async def stream_events(
    request: Request,
    graph_id: str,
    after_seq: int = Query(0, ge=0),
    tenant_id: str = Depends(get_tenant_id),
):
    """SSE event stream for real-time UI updates.

    Streams events in seq order from the event journal (Postgres).
    NOT from Redis - Postgres is truth.

    Stage-7.1 improvements:
    - Short-lived sessions (no leaks)
    - Bounded paging
    - Clean disconnect

    Args:
        graph_id: Graph to stream events for.
        after_seq: Resume from this seq (client's last known seq).

    Returns:
        Server-Sent Events stream.
    """
    return StreamingResponse(
        _event_generator(tenant_id, graph_id, after_seq),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = ["router"]
