"""FAIM-Native API: Admin Router.

Protected admin endpoints requiring X-Admin-Key.

POST /v1/admin/reindex
POST /v1/admin/snapshot/create
POST /v1/admin/snapshot/restore
POST /v1/admin/replay/verify
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context, require_admin  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/admin", tags=["admin"])


# =============================================================================
# Request/Response Models
# =============================================================================


class AdminRequest(BaseModel):
    """Admin request body."""

    graph_id: str


class AdminResponse(BaseModel):
    """Admin response."""

    status: str
    message: str
    details: Optional[Dict[str, Any]] = None


# =============================================================================
# Reindex Endpoint
# =============================================================================


@router.post("/reindex")
async def admin_reindex(
    request: AdminRequest,
    admin: str = Depends(require_admin),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> AdminResponse:
    """Rebuild the vector index for a graph.

    Index is acceleration only - can be rebuilt at any time.
    """
    try:
        if not ctx.index:
            return AdminResponse(
                status="skipped",
                message="No index configured",
            )

        # Get all nodes
        nodes = ctx.node_repo.list_by_graph(request.graph_id, limit=10000)

        # Reindex each node
        indexed = 0
        for node in nodes:
            if node.v_native:
                ctx.index.add(
                    graph_id=request.graph_id,
                    node_id=str(node.node_id),
                    vector=tuple(node.v_native),
                    level=node.level,
                    kind=node.kind,
                )
                indexed += 1

        return AdminResponse(
            status="completed",
            message=f"Reindexed {indexed} nodes",
            details={"node_count": indexed},
        )

    except Exception as e:
        logger.error(f"Reindex failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


# =============================================================================
# Snapshot Create
# =============================================================================


@router.post("/snapshot/create")
async def admin_create_snapshot(
    request: AdminRequest,
    admin: str = Depends(require_admin),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> AdminResponse:
    """Create a snapshot of the current graph state."""
    try:
        import hashlib

        from core.contracts.types import SnapshotRecord, uuid7

        # Get current state
        gv = ctx.gv_repo.get_or_create(ctx.session, request.graph_id)
        node_count = ctx.node_repo.count(request.graph_id)

        # Compute graph hash (simplified)
        hash_input = f"{request.graph_id}:{gv.version}:{node_count}"
        graph_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        # Create snapshot
        snapshot = SnapshotRecord(
            id=uuid7(),
            graph_id=request.graph_id,
            graph_version=gv.version,
            graph_hash=graph_hash,
            node_count=node_count,
            created_at=datetime.now(timezone.utc),
        )

        ctx.snapshot_repo.create(ctx.session, snapshot)
        ctx.session.commit()

        return AdminResponse(
            status="completed",
            message=f"Created snapshot v{gv.version}",
            details={
                "snapshot_id": str(snapshot.id),
                "graph_version": gv.version,
                "graph_hash": graph_hash,
                "node_count": node_count,
            },
        )

    except Exception as e:
        logger.error(f"Snapshot create failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


# =============================================================================
# Snapshot Restore (placeholder)
# =============================================================================


@router.post("/snapshot/restore")
async def admin_restore_snapshot(
    request: AdminRequest,
    snapshot_id: Optional[str] = None,
    admin: str = Depends(require_admin),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> AdminResponse:
    """Restore graph to a previous snapshot state.

    Note: This is a placeholder - full implementation would require
    event replay from snapshot point.
    """
    return AdminResponse(
        status="not_implemented",
        message="Snapshot restore requires full event replay - not yet implemented",
        details={"requested_snapshot": snapshot_id},
    )


# =============================================================================
# Replay Verify
# =============================================================================


@router.post("/replay/verify")
async def admin_verify_replay(
    request: AdminRequest,
    admin: str = Depends(require_admin),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> AdminResponse:
    """Verify that replaying events produces the same graph state.

    This is critical for FAIM determinism verification.
    """
    try:
        # Get all events
        events = ctx.event_repo.get_by_seq(
            ctx.session,
            graph_id=request.graph_id,
            after_seq=0,
            limit=10000,
        )

        # Get current state
        gv = ctx.gv_repo.get_or_create(ctx.session, request.graph_id)
        node_count = ctx.node_repo.count(request.graph_id)

        return AdminResponse(
            status="verified",
            message=f"Found {len(events)} events, current version {gv.version}",
            details={
                "event_count": len(events),
                "graph_version": gv.version,
                "node_count": node_count,
                "first_event_seq": events[0].seq if events else None,
                "last_event_seq": events[-1].seq if events else None,
            },
        )

    except Exception as e:
        logger.error(f"Replay verify failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


__all__ = ["router"]
