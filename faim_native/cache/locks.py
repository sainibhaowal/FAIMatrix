"""FAIM-Native Distributed Locks.

Lock manager with Redis + file fallback.

Key properties:
- Redis lock via SET key value NX PX
- Fallback: local file lock when Redis unavailable
- Context manager interface
- Used for evolve/reindex/worker single-writer guarantee

NO NUMPY. NO ML.
"""

from __future__ import annotations

import fcntl
import logging
import os
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Redis Lock
# =============================================================================


def _get_redis_client():
    """Get Redis client from query_cache module."""
    try:
        from .query_cache import _get_client

        return _get_client()
    except ImportError:
        return None


class RedisLock:
    """Redis-based distributed lock using SET NX PX.

    Uses the standard Redis lock pattern:
    SET lock_key lock_value NX PX timeout_ms
    """

    def __init__(
        self,
        key: str,
        timeout_ms: int = 30000,
        retry_interval_ms: int = 100,
        max_retries: int = 10,
    ) -> None:
        """Initialize Redis lock.

        Args:
            key: Lock key.
            timeout_ms: Lock timeout in milliseconds.
            retry_interval_ms: Retry interval in milliseconds.
            max_retries: Maximum number of acquire retries.
        """
        self._key = f"faim:lock:{key}"
        self._timeout_ms = timeout_ms
        self._retry_interval_ms = retry_interval_ms
        self._max_retries = max_retries
        self._lock_value = str(uuid.uuid4())
        self._acquired = False

    def acquire(self) -> bool:
        """Acquire the lock.

        Returns:
            True if lock acquired, False otherwise.
        """
        client = _get_redis_client()
        if client is None:
            return False

        for _ in range(self._max_retries):
            try:
                # SET key value NX PX timeout_ms
                result = client.set(
                    self._key,
                    self._lock_value,
                    nx=True,
                    px=self._timeout_ms,
                )

                if result:
                    self._acquired = True
                    logger.debug(f"Acquired lock: {self._key}")
                    return True

                # Lock held by someone else, retry
                time.sleep(self._retry_interval_ms / 1000)

            except Exception as e:
                logger.warning(f"Redis lock acquire failed: {e}")
                return False

        return False

    def release(self) -> bool:
        """Release the lock.

        Only releases if we own the lock (value matches).

        Returns:
            True if released, False otherwise.
        """
        if not self._acquired:
            return False

        client = _get_redis_client()
        if client is None:
            return False

        try:
            # Check if we own the lock before releasing
            current = client.get(self._key)
            if current and current.decode("utf-8") == self._lock_value:
                client.delete(self._key)
                self._acquired = False
                logger.debug(f"Released lock: {self._key}")
                return True
            return False

        except Exception as e:
            logger.warning(f"Redis lock release failed: {e}")
            return False

    @property
    def is_acquired(self) -> bool:
        """Check if lock is acquired."""
        return self._acquired


# =============================================================================
# File Lock (Fallback)
# =============================================================================


class FileLock:
    """Local file-based lock for fallback.

    Uses fcntl.flock for POSIX file locking.
    """

    LOCK_DIR = Path(os.getenv("FAIM_LOCK_DIR", "/tmp/faim/locks"))  # nosec B108

    def __init__(
        self,
        key: str,
        timeout_seconds: float = 30.0,
        retry_interval_seconds: float = 0.1,
        max_retries: int = 10,
    ) -> None:
        """Initialize file lock.

        Args:
            key: Lock key (used to generate filename).
            timeout_seconds: Lock timeout.
            retry_interval_seconds: Retry interval.
            max_retries: Maximum retries.
        """
        # Sanitize key for filename
        safe_key = key.replace("/", "_").replace(":", "_")
        self._lock_file = self.LOCK_DIR / f"{safe_key}.lock"
        self._timeout = timeout_seconds
        self._retry_interval = retry_interval_seconds
        self._max_retries = max_retries
        self._fd: Optional[int] = None
        self._acquired = False

    def acquire(self) -> bool:
        """Acquire the file lock."""
        # Ensure lock directory exists
        self.LOCK_DIR.mkdir(parents=True, exist_ok=True)

        for _ in range(self._max_retries):
            try:
                self._fd = os.open(
                    str(self._lock_file),
                    os.O_CREAT | os.O_RDWR,
                    0o644,
                )

                # Try non-blocking exclusive lock
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._acquired = True
                logger.debug(f"Acquired file lock: {self._lock_file}")
                return True

            except (BlockingIOError, OSError):
                # Lock held by someone else
                if self._fd is not None:
                    os.close(self._fd)
                    self._fd = None
                time.sleep(self._retry_interval)

        return False

    def release(self) -> bool:
        """Release the file lock."""
        if not self._acquired or self._fd is None:
            return False

        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None
            self._acquired = False
            logger.debug(f"Released file lock: {self._lock_file}")
            return True
        except Exception as e:
            logger.warning(f"File lock release failed: {e}")
            return False

    @property
    def is_acquired(self) -> bool:
        """Check if lock is acquired."""
        return self._acquired


# =============================================================================
# Lock Manager (Redis + Fallback)
# =============================================================================


class LockManager:
    """Lock manager with Redis primary and file fallback.

    Tries Redis first, falls back to local file lock if unavailable.
    """

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        retry_interval_seconds: float = 0.1,
        max_retries: int = 10,
    ) -> None:
        """Initialize lock manager.

        Args:
            timeout_seconds: Lock timeout.
            retry_interval_seconds: Retry interval.
            max_retries: Maximum retries.
        """
        self._timeout = timeout_seconds
        self._retry_interval = retry_interval_seconds
        self._max_retries = max_retries

    @contextmanager
    def lock(self, key: str) -> Generator[bool, None, None]:
        """Acquire lock as context manager.

        Tries Redis first, falls back to file lock.

        Args:
            key: Lock key.

        Yields:
            True if lock acquired, False otherwise.

        Usage:
            with lock_manager.lock("graph_123_evolve") as acquired:
                if acquired:
                    # Do protected work
                else:
                    # Handle lock failure
        """
        lock = None
        acquired = False

        # Try Redis lock first
        redis_lock = RedisLock(
            key,
            timeout_ms=int(self._timeout * 1000),
            retry_interval_ms=int(self._retry_interval * 1000),
            max_retries=self._max_retries,
        )

        if redis_lock.acquire():
            lock = redis_lock
            acquired = True
        else:
            # Fall back to file lock
            file_lock = FileLock(
                key,
                timeout_seconds=self._timeout,
                retry_interval_seconds=self._retry_interval,
                max_retries=self._max_retries,
            )

            if file_lock.acquire():
                lock = file_lock
                acquired = True

        try:
            yield acquired
        finally:
            if lock is not None:
                lock.release()

    def try_lock(self, key: str) -> Optional[RedisLock | FileLock]:
        """Try to acquire lock, returning lock object if successful.

        Caller is responsible for releasing.

        Args:
            key: Lock key.

        Returns:
            Lock object if acquired, None otherwise.
        """
        # Try Redis first
        redis_lock = RedisLock(
            key,
            timeout_ms=int(self._timeout * 1000),
            retry_interval_ms=int(self._retry_interval * 1000),
            max_retries=1,  # Only one attempt
        )

        if redis_lock.acquire():
            return redis_lock

        # Fall back to file lock
        file_lock = FileLock(
            key,
            timeout_seconds=self._timeout,
            retry_interval_seconds=self._retry_interval,
            max_retries=1,
        )

        if file_lock.acquire():
            return file_lock

        return None


# =============================================================================
# Graph-Specific Locks
# =============================================================================


def graph_evolve_lock_key(graph_id: str) -> str:
    """Generate lock key for graph evolution."""
    return f"graph:{graph_id}:evolve"


def graph_reindex_lock_key(graph_id: str) -> str:
    """Generate lock key for graph reindexing."""
    return f"graph:{graph_id}:reindex"


def graph_write_lock_key(graph_id: str) -> str:
    """Generate lock key for graph writes."""
    return f"graph:{graph_id}:write"


# =============================================================================
# Convenience Context Managers
# =============================================================================


_default_lock_manager = LockManager()


@contextmanager
def evolve_lock(graph_id: str) -> Generator[bool, None, None]:
    """Lock for graph evolution.

    Usage:
        with evolve_lock("graph_123") as acquired:
            if acquired:
                # Do evolution
    """
    with _default_lock_manager.lock(graph_evolve_lock_key(graph_id)) as acquired:
        yield acquired


@contextmanager
def reindex_lock(graph_id: str) -> Generator[bool, None, None]:
    """Lock for graph reindexing."""
    with _default_lock_manager.lock(graph_reindex_lock_key(graph_id)) as acquired:
        yield acquired


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "RedisLock",
    "FileLock",
    "LockManager",
    "graph_evolve_lock_key",
    "graph_reindex_lock_key",
    "graph_write_lock_key",
    "evolve_lock",
    "reindex_lock",
]
