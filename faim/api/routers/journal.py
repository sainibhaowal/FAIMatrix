# =============================================================================
# FAIM Journal Router - Audit Log API Endpoints
# =============================================================================
# File: faim/api/routers/journal.py
#
# Production endpoints for audit log access:
# - GET /api/v1/journal - List journal entries (paginated, filtered)
# - GET /api/v1/journal/stats - Dashboard statistics
# - GET /api/v1/journal/operations - Available operation types for filters
# - GET /api/v1/journal/{entry_id} - Single entry details
# - GET /api/v1/journal/node/{node_id}/timeline - Node activity history
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from faim.api.middleware.auth_middleware import get_current_user_oidc
from faim.api.services import journal_service
from faim.config.database import get_db
from faim.config.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/journal", tags=["Journal / Audit Log"])


# =============================================================================
# Response Models
# =============================================================================


class JournalEntryOut(BaseModel):
    """Single journal entry."""

    id: str
    timestamp: str
    operation: str
    node_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    graph_id: str


class JournalListOut(BaseModel):
    """Paginated journal list."""

    entries: List[JournalEntryOut]
    total: int
    page: int
    page_size: int
    has_more: bool


class JournalStatsOut(BaseModel):
    """Journal statistics for dashboard."""

    total_entries: int
    entries_today: int
    entries_this_week: int
    by_operation: Dict[str, int]
    most_active_node: Optional[str] = None


class OperationTypesOut(BaseModel):
    """Available operation types."""

    operations: List[str]


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=JournalListOut)
@router.get("/", response_model=JournalListOut, include_in_schema=False)
def list_journal(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    operation: Optional[str] = Query(None, description="Filter by operation type"),
    node_id: Optional[str] = Query(None, description="Filter by node ID"),
    since: Optional[str] = Query(None, description="ISO datetime, entries after this"),
    until: Optional[str] = Query(None, description="ISO datetime, entries before this"),
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """
    List journal entries with pagination and filtering.

    **Filters:**
    - `operation`: Filter by type (touch, add, merge, delete, evolve, prune)
    - `node_id`: Show only entries for a specific node
    - `since`: Show entries after this datetime (ISO format)
    - `until`: Show entries before this datetime (ISO format)

    **Multi-tenant:** Only shows entries for graphs you own.
    """
    # Parse datetime filters
    since_dt = None
    until_dt = None

    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'since' datetime format")

    if until:
        try:
            until_dt = datetime.fromisoformat(until.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'until' datetime format")

    result = journal_service.list_journal_entries(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        operation=operation,
        node_id=node_id,
        since=since_dt,
        until=until_dt,
    )

    return JournalListOut(
        entries=[
            JournalEntryOut(
                id=e.id,
                timestamp=e.timestamp,
                operation=e.operation,
                node_id=e.node_id,
                details=e.details,
                graph_id=e.graph_id,
            )
            for e in result.entries
        ],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        has_more=result.has_more,
    )


@router.get("/stats", response_model=JournalStatsOut)
def get_journal_stats(
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """
    Get journal statistics for dashboard.

    Returns:
    - Total entries
    - Entries today
    - Entries this week
    - Breakdown by operation type
    - Most active node
    """
    stats = journal_service.get_journal_stats(db, current_user.id)

    return JournalStatsOut(
        total_entries=stats.total_entries,
        entries_today=stats.entries_today,
        entries_this_week=stats.entries_this_week,
        by_operation=stats.by_operation,
        most_active_node=stats.most_active_node,
    )


@router.get("/operations", response_model=OperationTypesOut)
def get_operation_types(
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """
    Get list of operation types in your journal.

    Useful for building filter dropdowns in the UI.
    """
    ops = journal_service.get_operation_types(db, current_user.id)

    return OperationTypesOut(operations=ops)


@router.get("/node/{node_id}/timeline", response_model=List[JournalEntryOut])
def get_node_timeline(
    node_id: str,
    limit: int = Query(50, ge=1, le=100, description="Max entries to return"),
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """
    Get activity timeline for a specific node.

    Shows the complete history of operations on this memory:
    - When it was created
    - When it was touched/retrieved
    - When it merged with other nodes
    - When it evolved
    """
    entries = journal_service.get_node_timeline(
        db=db,
        user_id=current_user.id,
        node_id=node_id,
        limit=limit,
    )

    return [
        JournalEntryOut(
            id=e.id,
            timestamp=e.timestamp,
            operation=e.operation,
            node_id=e.node_id,
            details=e.details,
            graph_id=e.graph_id,
        )
        for e in entries
    ]


@router.get("/{entry_id}", response_model=JournalEntryOut)
def get_journal_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """
    Get a single journal entry by ID.

    **Multi-tenant:** Only accessible if you own the graph.
    """
    entry = journal_service.get_journal_entry(db, current_user.id, entry_id)

    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    return JournalEntryOut(
        id=entry.id,
        timestamp=entry.timestamp,
        operation=entry.operation,
        node_id=entry.node_id,
        details=entry.details,
        graph_id=entry.graph_id,
    )
