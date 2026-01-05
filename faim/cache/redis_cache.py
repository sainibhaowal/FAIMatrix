"""Redis-backed Cache Layer for FAIM.

Production implementation using Redis for caching with multi-tenant isolation.
Keys are scoped by project_id to ensure data isolation.

Key format: faim:{project_id}:{graph_id}:{key_type}:{key}
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

# Redis client - lazy loaded
_redis_client = None


def _get_redis_url() -> str:
    """Get Redis URL from environment."""
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _get_client():
    """Get or create Redis client (lazy loading)."""
    global _redis_client
    if _redis_client is None:
        try:
            import redis

            _redis_client = redis.from_url(_get_redis_url())
            # Test connection
            _redis_client.ping()
            logger.info(f"Connected to Redis at {_get_redis_url()}")
        except ImportError:
            logger.warning("redis package not installed")
            _redis_client = None
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            _redis_client = None
    return _redis_client


class RedisCache:
    """Redis-backed cache with multi-tenant isolation.

    All keys are prefixed with project_id for complete data isolation.
    """

    # Default TTLs in seconds
    DEFAULT_TTL = 3600  # 1 hour
    HOT_NODE_TTL = 300  # 5 minutes for frequently accessed nodes
    SESSION_TTL = 86400  # 24 hours for sessions

    def __init__(self, project_id: UUID) -> None:
        """Initialize cache for a project.

        Args:
            project_id: The project UUID for tenant isolation
        """
        self._project_id = project_id
        self._prefix = f"faim:{str(project_id)}:"

    def _key(self, key_type: str, key: str) -> str:
        """Generate a full cache key with project prefix."""
        return f"{self._prefix}{key_type}:{key}"

    # ------------------------------------------------------------------ Basic Operations

    def get(self, key_type: str, key: str) -> Optional[str]:
        """Get a cached string value."""
        client = _get_client()
        if client is None:
            return None

        try:
            result = client.get(self._key(key_type, key))
            return result.decode("utf-8") if result else None
        except Exception as e:
            logger.error(f"Redis GET failed: {e}")
            return None

    def set(self, key_type: str, key: str, value: str, ttl: int = DEFAULT_TTL) -> bool:
        """Set a cached string value with TTL."""
        client = _get_client()
        if client is None:
            return False

        try:
            client.setex(self._key(key_type, key), ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET failed: {e}")
            return False

    def delete(self, key_type: str, key: str) -> bool:
        """Delete a cached value."""
        client = _get_client()
        if client is None:
            return False

        try:
            client.delete(self._key(key_type, key))
            return True
        except Exception as e:
            logger.error(f"Redis DELETE failed: {e}")
            return False

    # ------------------------------------------------------------------ JSON Operations

    def get_json(self, key_type: str, key: str) -> Optional[Any]:
        """Get a cached JSON value."""
        value = self.get(key_type, key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    def set_json(self, key_type: str, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """Set a cached JSON value with TTL."""
        try:
            return self.set(key_type, key, json.dumps(value), ttl)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON serialization failed: {e}")
            return False

    # ------------------------------------------------------------------ Hot Node Cache

    def cache_node(self, graph_id: str, node_id: str, node_data: Dict) -> bool:
        """Cache a hot node for fast retrieval."""
        key = f"{graph_id}:{node_id}"
        return self.set_json("node", key, node_data, self.HOT_NODE_TTL)

    def get_cached_node(self, graph_id: str, node_id: str) -> Optional[Dict]:
        """Get a cached node."""
        key = f"{graph_id}:{node_id}"
        return self.get_json("node", key)

    def invalidate_node(self, graph_id: str, node_id: str) -> bool:
        """Invalidate a cached node."""
        key = f"{graph_id}:{node_id}"
        return self.delete("node", key)

    # ------------------------------------------------------------------ Rate Limiting

    def check_rate_limit(self, endpoint: str, limit: int = 100, window_seconds: int = 60) -> bool:
        """Check if request is within rate limit.

        Returns True if within limit, False if rate limited.
        """
        client = _get_client()
        if client is None:
            return True  # Allow if Redis unavailable

        try:
            key = self._key("rate", endpoint)

            # Increment counter
            current = client.incr(key)

            # Set expiry on first request
            if current == 1:
                client.expire(key, window_seconds)

            return current <= limit
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True

    def get_rate_limit_remaining(self, endpoint: str, limit: int = 100) -> int:
        """Get remaining requests in current rate limit window."""
        client = _get_client()
        if client is None:
            return limit

        try:
            key = self._key("rate", endpoint)
            current = client.get(key)
            if current:
                return max(0, limit - int(current))
            return limit
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return limit

    # ------------------------------------------------------------------ Graph Stats Cache

    def cache_graph_stats(self, graph_id: str, stats: Dict) -> bool:
        """Cache graph statistics."""
        return self.set_json("stats", graph_id, stats, self.DEFAULT_TTL)

    def get_graph_stats(self, graph_id: str) -> Optional[Dict]:
        """Get cached graph statistics."""
        return self.get_json("stats", graph_id)

    def invalidate_graph_stats(self, graph_id: str) -> bool:
        """Invalidate cached graph statistics."""
        return self.delete("stats", graph_id)

    # ------------------------------------------------------------------ Bulk Operations

    def clear_graph_cache(self, graph_id: str) -> int:
        """Clear all cached data for a graph."""
        client = _get_client()
        if client is None:
            return 0

        try:
            # Find all keys for this graph
            pattern = f"{self._prefix}*:{graph_id}*"
            keys = list(client.scan_iter(match=pattern))

            if keys:
                return client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Clear graph cache failed: {e}")
            return 0

    def clear_project_cache(self) -> int:
        """Clear all cached data for the project."""
        client = _get_client()
        if client is None:
            return 0

        try:
            # Find all keys for this project
            pattern = f"{self._prefix}*"
            keys = list(client.scan_iter(match=pattern))

            if keys:
                return client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Clear project cache failed: {e}")
            return 0


# ------------------------------------------------------------------ Global Rate Limiter


class GlobalRateLimiter:
    """Rate limiter for non-project-scoped operations (e.g., login attempts)."""

    def __init__(self, prefix: str = "faim:global:") -> None:
        self._prefix = prefix

    def check_rate_limit(self, key: str, limit: int = 10, window_seconds: int = 60) -> bool:
        """Check if request is within rate limit."""
        client = _get_client()
        if client is None:
            return True

        try:
            full_key = f"{self._prefix}rate:{key}"
            current = client.incr(full_key)
            if current == 1:
                client.expire(full_key, window_seconds)
            return current <= limit
        except Exception as e:
            logger.error(f"Global rate limit check failed: {e}")
            return True
