# =============================================================================
# FAIM Usage Tracking Service (Centralized)
# =============================================================================
# Replaces token_tracker.py with clear metrics:
# - Memories: Number of nodes stored
# - Storage: File upload size
# - API Calls: Monthly request count
# =============================================================================

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Set
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# =============================================================================
# Plan Limits
# =============================================================================

PLAN_LIMITS = {
    # Free - Hobbyist / Try out
    "free": {
        "memories": 1_000,
        "storage_bytes": 104_857_600,  # 100 MB
        "api_calls_month": 10_000,
        "price_monthly": 0,
    },
    # Starter - $15/month - Small teams
    "starter": {
        "memories": 10_000,
        "storage_bytes": 1_073_741_824,  # 1 GB
        "api_calls_month": 100_000,
        "price_monthly": 15,
    },
    # Custom - Contact sales for custom limits
    "custom": {
        "memories": 999_999_999,  # Set per customer
        "storage_bytes": 999_999_999_999,  # Set per customer
        "api_calls_month": 999_999_999,  # Set per customer
        "price_monthly": -1,  # -1 = Contact sales
    },
}


def get_plan_limits(plan: str) -> dict:
    """Get limits for a plan."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


# =============================================================================
# SSE Manager for Real-Time Updates
# =============================================================================


class UsageSSEManager:
    """Manages SSE connections for real-time usage updates."""

    def __init__(self):
        self._connections: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str) -> asyncio.Queue:
        """Register a new SSE connection for a user."""
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._connections[user_id].add(queue)
        logger.info(f"[SSE] Client connected for user {user_id[:8]}...")
        return queue

    async def disconnect(self, user_id: str, queue: asyncio.Queue):
        """Remove an SSE connection."""
        async with self._lock:
            self._connections[user_id].discard(queue)
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info(f"[SSE] Client disconnected from user {user_id[:8]}...")

    async def broadcast(self, user_id: str, data: Dict[str, Any]):
        """Send usage update to all connected clients for a user."""
        async with self._lock:
            queues = list(self._connections.get(user_id, []))

        if not queues:
            return

        message = json.dumps(data)
        for queue in queues:
            try:
                await queue.put(message)
            except Exception as e:
                logger.warning(f"[SSE] Failed to broadcast: {e}")


# Global SSE manager instance
usage_sse_manager = UsageSSEManager()


# =============================================================================
# Usage Tracking Functions
# =============================================================================


def get_user_usage(db: Session, user_id: str) -> Dict[str, Any]:
    """Get current usage stats for a user."""
    from faim.config.models import User

    try:
        user = db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            return {}

        limits = get_plan_limits(user.plan or "free")

        return {
            "user_id": user_id,
            "plan": user.plan or "free",
            "memories_count": user.memories_count or 0,
            "memories_max": limits["memories"],
            "storage_used_bytes": user.storage_used_bytes or 0,
            "storage_max_bytes": limits["storage_bytes"],
            "api_calls_count": user.api_calls_count or 0,
            "api_calls_max": limits["api_calls_month"],
            "last_updated": user.last_usage_update.isoformat() if user.last_usage_update else None,
        }
    except Exception as e:
        logger.error(f"[Usage] Failed to get usage: {e}")
        return {}


def check_memory_limit(db: Session, user_id: str, count: int = 1) -> tuple[bool, str]:
    """Check if user can add more memories."""
    from faim.config.models import User

    try:
        user = db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            return True, "OK"

        limits = get_plan_limits(user.plan or "free")
        current = user.memories_count or 0

        if current + count > limits["memories"]:
            return False, f"Memory limit exceeded ({current:,}/{limits['memories']:,}). Upgrade your plan."

        return True, "OK"
    except Exception as e:
        logger.warning(f"[Usage] Limit check failed: {e}")
        return True, "OK"  # Fail open


def check_storage_limit(db: Session, user_id: str, bytes_to_add: int) -> tuple[bool, str]:
    """Check if user can upload more storage."""
    from faim.config.models import User

    try:
        user = db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            return True, "OK"

        limits = get_plan_limits(user.plan or "free")
        current = user.storage_used_bytes or 0

        if current + bytes_to_add > limits["storage_bytes"]:
            current_mb = current / (1024 * 1024)
            max_mb = limits["storage_bytes"] / (1024 * 1024)
            return False, f"Storage limit exceeded ({current_mb:.1f}MB/{max_mb:.0f}MB). Upgrade your plan."

        return True, "OK"
    except Exception as e:
        logger.warning(f"[Usage] Storage check failed: {e}")
        return True, "OK"


def add_memory_usage(db: Session, user_id: str, count: int = 1) -> Dict[str, Any]:
    """Increment memory count for a user."""
    from faim.config.models import User

    try:
        user = db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            return {}

        user.memories_count = (user.memories_count or 0) + count
        user.last_usage_update = datetime.utcnow()
        db.commit()

        return get_user_usage(db, user_id)
    except Exception as e:
        logger.error(f"[Usage] Failed to add memory usage: {e}")
        return {}


def add_storage_usage(db: Session, user_id: str, bytes_added: int) -> Dict[str, Any]:
    """Add storage usage for a user."""
    from faim.config.models import User

    try:
        user = db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            return {}

        user.storage_used_bytes = (user.storage_used_bytes or 0) + bytes_added
        user.last_usage_update = datetime.utcnow()
        db.commit()

        return get_user_usage(db, user_id)
    except Exception as e:
        logger.error(f"[Usage] Failed to add storage usage: {e}")
        return {}


def add_api_call(db: Session, user_id: str) -> None:
    """Increment API call count for a user."""
    from faim.config.models import User

    try:
        user = db.query(User).filter(User.id == UUID(user_id)).first()
        if not user:
            return

        # Check if we need to reset (monthly)
        now = datetime.utcnow()
        reset_at = user.api_calls_reset_at
        if reset_at and reset_at.month != now.month:
            user.api_calls_count = 0
            user.api_calls_reset_at = now

        user.api_calls_count = (user.api_calls_count or 0) + 1
        db.commit()
    except Exception as e:
        logger.warning(f"[Usage] Failed to add API call: {e}")


def upgrade_user_plan(db: Session, user_id: str, new_plan: str) -> Dict[str, Any]:
    """Upgrade a user's plan and update limits."""
    from faim.config.models import User

    if new_plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {new_plan}")

    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    limits = PLAN_LIMITS[new_plan]
    user.plan = new_plan
    user.memories_max = limits["memories"]
    user.storage_max_bytes = limits["storage_bytes"]
    user.api_calls_max = limits["api_calls_month"]
    db.commit()

    return {
        "status": "upgraded",
        "plan": new_plan,
        "memories_max": limits["memories"],
        "storage_max_bytes": limits["storage_bytes"],
        "api_calls_max": limits["api_calls_month"],
    }
