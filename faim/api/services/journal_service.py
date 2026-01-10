# =============================================================================
# FAIM Journal Service - Audit Log Business Logic
# =============================================================================
# File: faim/api/services/journal_service.py
#
# Production-grade audit log service providing:
# - List journal entries with pagination
# - Filter by operation type, date range, node
# - Get activity summary/statistics
# - Multi-tenant isolation (user can only see their own graph's journal)
# =============================================================================

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from faim.config.models import EventJournalEntry, GraphOwnership

# =============================================================================
# Data Transfer Objects
# =============================================================================


@dataclass
class JournalEntry:
    """Single journal entry for API response."""

    id: str
    timestamp: str
    operation: str
    node_id: Optional[str]
    details: Dict[str, Any]
    graph_id: str


@dataclass
class JournalListResult:
    """Paginated journal list result."""

    entries: List[JournalEntry]
    total: int
    page: int
    page_size: int
    has_more: bool


@dataclass
class JournalStats:
    """Journal statistics for dashboard."""

    total_entries: int
    entries_today: int
    entries_this_week: int
    by_operation: Dict[str, int]
    most_active_node: Optional[str]


# =============================================================================
# Journal Listing
# =============================================================================


def list_journal_entries(
    db: Session,
    user_id: UUID,
    page: int = 1,
    page_size: int = 50,
    operation: Optional[str] = None,
    node_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> JournalListResult:
    """
    List journal entries for a user with pagination and filters.

    Multi-tenant: Only returns entries for graphs owned by the user.

    Args:
        db: Database session
        user_id: User's UUID
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
        operation: Filter by operation type (touch, add, merge, delete, evolve, prune)
        node_id: Filter by specific node
        since: Filter entries after this date
        until: Filter entries before this date

    Returns:
        JournalListResult with paginated entries
    """
    # Cap page size
    page_size = min(page_size, 100)

    # Get user's graphs for multi-tenant filtering
    user_graphs = db.query(GraphOwnership.graph_id).filter(GraphOwnership.user_id == user_id).all()
    graph_ids = [g.graph_id for g in user_graphs]

    if not graph_ids:
        return JournalListResult(entries=[], total=0, page=page, page_size=page_size, has_more=False)

    # Build query
    query = db.query(EventJournalEntry).filter(EventJournalEntry.graph_id.in_(graph_ids))

    # Apply filters
    if operation:
        query = query.filter(EventJournalEntry.kind == operation)

    if node_id:
        query = query.filter(EventJournalEntry.node_id == node_id)

    if since:
        query = query.filter(EventJournalEntry.ts >= since)

    if until:
        query = query.filter(EventJournalEntry.ts <= until)

    # Order by most recent first
    query = query.order_by(EventJournalEntry.ts.desc())

    # Get total count
    total = query.count()

    # Paginate
    offset = (page - 1) * page_size
    entries = query.offset(offset).limit(page_size).all()

    return JournalListResult(
        entries=[
            JournalEntry(
                id=str(e.id),
                timestamp=e.ts.isoformat() if e.ts else "",
                operation=e.kind,
                node_id=e.node_id,
                details=e.details or {},
                graph_id=e.graph_id,
            )
            for e in entries
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(entries)) < total,
    )


# =============================================================================
# Get Single Entry
# =============================================================================


def get_journal_entry(db: Session, user_id: UUID, entry_id: str) -> Optional[JournalEntry]:
    """
    Get a single journal entry by ID.

    Multi-tenant: Verifies user owns the graph before returning.
    """
    entry = db.query(EventJournalEntry).filter(EventJournalEntry.id == entry_id).first()

    if not entry:
        return None

    # Verify user owns this graph
    ownership = (
        db.query(GraphOwnership)
        .filter(
            GraphOwnership.graph_id == entry.graph_id,
            GraphOwnership.user_id == user_id,
        )
        .first()
    )

    if not ownership:
        return None  # User doesn't own this graph

    return JournalEntry(
        id=str(entry.id),
        timestamp=entry.ts.isoformat() if entry.ts else "",
        operation=entry.kind,
        node_id=entry.node_id,
        details=entry.details or {},
        graph_id=entry.graph_id,
    )


# =============================================================================
# Journal Statistics
# =============================================================================


def get_journal_stats(db: Session, user_id: UUID) -> JournalStats:
    """
    Get journal statistics for a user's dashboard.

    Multi-tenant: Only counts entries for graphs owned by the user.
    """
    # Get user's graphs
    user_graphs = db.query(GraphOwnership.graph_id).filter(GraphOwnership.user_id == user_id).all()
    graph_ids = [g.graph_id for g in user_graphs]

    if not graph_ids:
        return JournalStats(
            total_entries=0,
            entries_today=0,
            entries_this_week=0,
            by_operation={},
            most_active_node=None,
        )

    # Total entries
    total = db.query(func.count(EventJournalEntry.id)).filter(EventJournalEntry.graph_id.in_(graph_ids)).scalar() or 0

    # Today's entries
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = (
        db.query(func.count(EventJournalEntry.id))
        .filter(
            EventJournalEntry.graph_id.in_(graph_ids),
            EventJournalEntry.ts >= today_start,
        )
        .scalar()
        or 0
    )

    # This week's entries
    week_start = today_start - timedelta(days=today_start.weekday())
    week_count = (
        db.query(func.count(EventJournalEntry.id))
        .filter(
            EventJournalEntry.graph_id.in_(graph_ids),
            EventJournalEntry.ts >= week_start,
        )
        .scalar()
        or 0
    )

    # Count by operation type
    op_counts = (
        db.query(EventJournalEntry.kind, func.count(EventJournalEntry.id))
        .filter(EventJournalEntry.graph_id.in_(graph_ids))
        .group_by(EventJournalEntry.kind)
        .all()
    )
    by_operation = {op: count for op, count in op_counts}

    # Most active node (most entries)
    most_active = (
        db.query(EventJournalEntry.node_id, func.count(EventJournalEntry.id).label("cnt"))
        .filter(
            EventJournalEntry.graph_id.in_(graph_ids),
            EventJournalEntry.node_id.isnot(None),
        )
        .group_by(EventJournalEntry.node_id)
        .order_by(func.count(EventJournalEntry.id).desc())
        .first()
    )

    return JournalStats(
        total_entries=total,
        entries_today=today_count,
        entries_this_week=week_count,
        by_operation=by_operation,
        most_active_node=most_active[0] if most_active else None,
    )


# =============================================================================
# Get Operation Types
# =============================================================================


def get_operation_types(db: Session, user_id: UUID) -> List[str]:
    """
    Get list of distinct operation types in user's journal.

    Useful for building filter dropdowns in UI.
    """
    user_graphs = db.query(GraphOwnership.graph_id).filter(GraphOwnership.user_id == user_id).all()
    graph_ids = [g.graph_id for g in user_graphs]

    if not graph_ids:
        return []

    ops = db.query(EventJournalEntry.kind).filter(EventJournalEntry.graph_id.in_(graph_ids)).distinct().all()

    return [op[0] for op in ops if op[0]]


# =============================================================================
# Node Activity Timeline
# =============================================================================


def get_node_timeline(
    db: Session,
    user_id: UUID,
    node_id: str,
    limit: int = 50,
) -> List[JournalEntry]:
    """
    Get activity timeline for a specific node.

    Useful for showing "History of this memory" in UI.
    """
    # Get user's graphs
    user_graphs = db.query(GraphOwnership.graph_id).filter(GraphOwnership.user_id == user_id).all()
    graph_ids = [g.graph_id for g in user_graphs]

    if not graph_ids:
        return []

    entries = (
        db.query(EventJournalEntry)
        .filter(
            EventJournalEntry.graph_id.in_(graph_ids),
            EventJournalEntry.node_id == node_id,
        )
        .order_by(EventJournalEntry.ts.desc())
        .limit(min(limit, 100))
        .all()
    )

    return [
        JournalEntry(
            id=str(e.id),
            timestamp=e.ts.isoformat() if e.ts else "",
            operation=e.kind,
            node_id=e.node_id,
            details=e.details or {},
            graph_id=e.graph_id,
        )
        for e in entries
    ]
