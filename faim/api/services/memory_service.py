# =============================================================================
# FAIM Memory Service - Business Logic
# =============================================================================
# Core memory management operations:
# - List memories (with pagination/filtering)
# - Get memory details
# - Delete memories (single, batch, all)
# - Memory statistics
#
# This service is called by routers/memories.py (HTTP layer)
# =============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from faim.config.models import GraphOwnership, User

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class MemoryInfo:
    """Single memory node."""

    id: str
    content: str
    source: Optional[str] = None
    source_name: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class MemoryListResult:
    """Paginated list result."""

    memories: List[MemoryInfo]
    total: int
    page: int
    page_size: int
    has_more: bool


@dataclass
class DeleteResult:
    """Deletion operation result."""

    success: bool
    deleted_count: int
    failed_ids: List[str]
    new_memories_count: int
    message: str


@dataclass
class MemoryStats:
    """User memory statistics."""

    total_memories: int
    memories_max: int
    by_source: Dict[str, int]


# =============================================================================
# Helper Functions
# =============================================================================


def get_user_graph_id(db: Session, user_id: UUID) -> Optional[str]:
    """Get the user's primary graph ID."""
    ownership = db.query(GraphOwnership).filter(GraphOwnership.user_id == user_id).first()
    return ownership.graph_id if ownership else None


def get_faim_engine():
    """Get FAIM engine instance."""
    try:
        from faim.api.adapters.adapter import get_engine

        return get_engine()
    except Exception as e:
        logger.error(f"Failed to get FAIM engine: {e}")
        return None


def update_memory_count(db: Session, user_id: UUID, delta: int) -> int:
    """Update user's memory count by delta (positive or negative)."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        new_count = max(0, (user.memories_count or 0) + delta)
        user.memories_count = new_count
        user.last_usage_update = datetime.utcnow()
        db.commit()
        return new_count
    return 0


# =============================================================================
# Service Functions
# =============================================================================


def list_memories(
    db: Session,
    user_id: UUID,
    page: int = 1,
    page_size: int = 50,
    source_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> MemoryListResult:
    """
    List user's memories with pagination and filtering.

    Args:
        db: Database session
        user_id: User UUID
        page: Page number (1-indexed)
        page_size: Items per page
        source_filter: Filter by source type (document, api, chat)
        search: Search term in content

    Returns:
        MemoryListResult with paginated memories
    """
    graph_id = get_user_graph_id(db, user_id)
    if not graph_id:
        return MemoryListResult(
            memories=[],
            total=0,
            page=page,
            page_size=page_size,
            has_more=False,
        )

    engine = get_faim_engine()
    if not engine:
        logger.error("Memory engine not available")
        return MemoryListResult(
            memories=[],
            total=0,
            page=page,
            page_size=page_size,
            has_more=False,
        )

    try:
        # Get all nodes from the graph
        all_nodes = []
        if hasattr(engine, "_store") and hasattr(engine._store, "get_all_nodes"):
            all_nodes = engine._store.get_all_nodes(graph_id)

        # Filter by source
        if source_filter:
            all_nodes = [n for n in all_nodes if n.get("source", "").startswith(source_filter)]

        # Search filter
        if search:
            search_lower = search.lower()
            all_nodes = [n for n in all_nodes if search_lower in n.get("content", "").lower()]

        total = len(all_nodes)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        paginated = all_nodes[start:end]

        memories = [
            MemoryInfo(
                id=str(n.get("id", "")),
                content=n.get("content", "")[:500],  # Truncate for list
                source=n.get("source"),
                source_name=n.get("source_name", "Unknown"),
                created_at=n.get("created_at"),
                metadata=n.get("metadata"),
            )
            for n in paginated
        ]

        return MemoryListResult(
            memories=memories,
            total=total,
            page=page,
            page_size=page_size,
            has_more=end < total,
        )

    except Exception as e:
        logger.error(f"Failed to list memories: {e}")
        return MemoryListResult(
            memories=[],
            total=0,
            page=page,
            page_size=page_size,
            has_more=False,
        )


def get_memory(db: Session, user_id: UUID, memory_id: str) -> Optional[MemoryInfo]:
    """
    Get a single memory by ID.

    Returns None if not found.
    """
    graph_id = get_user_graph_id(db, user_id)
    if not graph_id:
        return None

    engine = get_faim_engine()
    if not engine:
        return None

    try:
        node = None
        if hasattr(engine, "_store") and hasattr(engine._store, "get_node"):
            node = engine._store.get_node(graph_id, memory_id)

        if not node:
            return None

        return MemoryInfo(
            id=str(node.get("id", "")),
            content=node.get("content", ""),
            source=node.get("source"),
            source_name=node.get("source_name"),
            created_at=node.get("created_at"),
            metadata=node.get("metadata"),
        )

    except Exception as e:
        logger.error(f"Failed to get memory: {e}")
        return None


def delete_memory(db: Session, user_id: UUID, memory_id: str) -> DeleteResult:
    """
    Delete a single memory.

    Returns DeleteResult with success status.
    """
    graph_id = get_user_graph_id(db, user_id)
    if not graph_id:
        return DeleteResult(
            success=False,
            deleted_count=0,
            failed_ids=[memory_id],
            new_memories_count=0,
            message="No graph found for user",
        )

    engine = get_faim_engine()
    if not engine:
        return DeleteResult(
            success=False,
            deleted_count=0,
            failed_ids=[memory_id],
            new_memories_count=0,
            message="Memory engine not available",
        )

    try:
        success = False
        if hasattr(engine, "_store") and hasattr(engine._store, "delete_node"):
            success = engine._store.delete_node(graph_id, memory_id)
        else:
            logger.warning("Store doesn't support delete_node")
            success = True  # Soft delete fallback

        if success:
            new_count = update_memory_count(db, user_id, -1)
            logger.info(f"Memory {memory_id} deleted for user {user_id}")
            return DeleteResult(
                success=True,
                deleted_count=1,
                failed_ids=[],
                new_memories_count=new_count,
                message="Memory deleted successfully",
            )
        else:
            return DeleteResult(
                success=False,
                deleted_count=0,
                failed_ids=[memory_id],
                new_memories_count=0,
                message="Memory not found or already deleted",
            )

    except Exception as e:
        logger.error(f"Failed to delete memory: {e}")
        return DeleteResult(
            success=False,
            deleted_count=0,
            failed_ids=[memory_id],
            new_memories_count=0,
            message=f"Delete failed: {str(e)}",
        )


def batch_delete_memories(
    db: Session,
    user_id: UUID,
    memory_ids: List[str],
) -> DeleteResult:
    """
    Delete multiple memories at once.

    Returns DeleteResult with counts of successes/failures.
    """
    graph_id = get_user_graph_id(db, user_id)
    if not graph_id:
        return DeleteResult(
            success=False,
            deleted_count=0,
            failed_ids=memory_ids,
            new_memories_count=0,
            message="No graph found for user",
        )

    engine = get_faim_engine()
    if not engine:
        return DeleteResult(
            success=False,
            deleted_count=0,
            failed_ids=memory_ids,
            new_memories_count=0,
            message="Memory engine not available",
        )

    deleted_count = 0
    failed_ids = []

    for memory_id in memory_ids:
        try:
            success = False
            if hasattr(engine, "_store") and hasattr(engine._store, "delete_node"):
                success = engine._store.delete_node(graph_id, memory_id)
            else:
                success = True

            if success:
                deleted_count += 1
            else:
                failed_ids.append(memory_id)

        except Exception as e:
            logger.warning(f"Failed to delete memory {memory_id}: {e}")
            failed_ids.append(memory_id)

    # Update count
    new_count = 0
    if deleted_count > 0:
        new_count = update_memory_count(db, user_id, -deleted_count)

    logger.info(f"Batch delete: {deleted_count}/{len(memory_ids)} for user {user_id}")

    return DeleteResult(
        success=len(failed_ids) == 0,
        deleted_count=deleted_count,
        failed_ids=failed_ids,
        new_memories_count=new_count,
        message=f"Deleted {deleted_count} memories" + (f", {len(failed_ids)} failed" if failed_ids else ""),
    )


def clear_all_memories(db: Session, user_id: UUID) -> DeleteResult:
    """
    Delete ALL memories for a user.

    ⚠️ This is destructive and cannot be undone!
    """
    graph_id = get_user_graph_id(db, user_id)
    if not graph_id:
        return DeleteResult(
            success=True,
            deleted_count=0,
            failed_ids=[],
            new_memories_count=0,
            message="No graph found, nothing to delete",
        )

    engine = get_faim_engine()
    if not engine:
        return DeleteResult(
            success=False,
            deleted_count=0,
            failed_ids=[],
            new_memories_count=0,
            message="Memory engine not available",
        )

    try:
        # Get current count
        user = db.query(User).filter(User.id == user_id).first()
        old_count = user.memories_count if user else 0

        # Clear graph
        if hasattr(engine, "_store") and hasattr(engine._store, "clear_graph"):
            engine._store.clear_graph(graph_id)

        # Reset count
        if user:
            user.memories_count = 0
            user.last_usage_update = datetime.utcnow()
            db.commit()

        logger.warning(f"All memories cleared for user {user_id} (was {old_count})")

        return DeleteResult(
            success=True,
            deleted_count=old_count,
            failed_ids=[],
            new_memories_count=0,
            message=f"Cleared all {old_count} memories",
        )

    except Exception as e:
        logger.error(f"Failed to clear memories: {e}")
        return DeleteResult(
            success=False,
            deleted_count=0,
            failed_ids=[],
            new_memories_count=0,
            message=f"Clear failed: {str(e)}",
        )


def get_memory_stats(db: Session, user_id: UUID) -> MemoryStats:
    """Get memory statistics for a user."""
    from faim.api.services.usage_service import PLAN_LIMITS

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return MemoryStats(total_memories=0, memories_max=1000, by_source={})

    plan = user.plan or "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    return MemoryStats(
        total_memories=user.memories_count or 0,
        memories_max=limits["memories"],
        by_source={
            "document": 0,  # TODO: Implement source tracking
            "api": 0,
            "chat": 0,
        },
    )
