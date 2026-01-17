"""FAIM-Native Query Cache.

Redis-backed query cache with graph_version in keys.

Key properties:
- Cache key includes: (tenant_id, graph_id, graph_version, query_hash, profile, k)
- Version change → old cache not returned
- Redis down → empty cache (graceful degradation)
- Cache hit/miss never changes graph state

NO NUMPY. NO ML. ACCELERATION ONLY.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)

# Redis client - lazy loaded
_redis_client = None
_redis_available = None


def _get_redis_url() -> str:
    """Get Redis URL from environment."""
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _get_client():
    """Get or create Redis client (lazy loading).

    Returns None if Redis unavailable.
    """
    global _redis_client, _redis_available

    if _redis_available is False:
        return None

    if _redis_client is None:
        try:
            import redis

            _redis_client = redis.from_url(_get_redis_url())
            _redis_client.ping()
            _redis_available = True
            logger.info(f"Connected to Redis at {_get_redis_url()}")
        except ImportError:
            logger.warning("redis package not installed")
            _redis_available = False
            _redis_client = None
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}")
            _redis_available = False
            _redis_client = None

    return _redis_client


def is_redis_available() -> bool:
    """Check if Redis is available."""
    _get_client()
    return _redis_available is True


# =============================================================================
# Cache Key Generation
# =============================================================================


def compute_query_hash(query_vector: Tuple[float, ...]) -> str:
    """Compute SHA256 hash of query vector.

    Args:
        query_vector: Query vector tuple.

    Returns:
        Hex digest of SHA256 hash.
    """
    # Convert to canonical JSON string
    canonical = json.dumps(list(query_vector), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def make_cache_key(
    tenant_id: str,
    graph_id: str,
    graph_version: int,
    query_hash: str,
    profile: str,
    k: int,
) -> str:
    """Generate cache key with graph_version.

    Format: faim:query:<tenant>:<graph>:v<version>:<query_hash>:<profile>:k<k>

    The graph_version ensures stale results are never returned.
    """
    return f"faim:query:{tenant_id}:{graph_id}:v{graph_version}:{query_hash}:{profile}:k{k}"


def parse_cache_key(key: str) -> Optional[Dict[str, Any]]:
    """Parse cache key components.

    Returns dict with tenant_id, graph_id, graph_version, query_hash, profile, k.
    """
    if not key.startswith("faim:query:"):
        return None

    parts = key.split(":")
    if len(parts) != 8:
        return None

    try:
        return {
            "tenant_id": parts[2],
            "graph_id": parts[3],
            "graph_version": int(parts[4][1:]),  # Remove 'v' prefix
            "query_hash": parts[5],
            "profile": parts[6],
            "k": int(parts[7][1:]),  # Remove 'k' prefix
        }
    except (ValueError, IndexError):
        return None


# =============================================================================
# Query Cache
# =============================================================================


class QueryCache:
    """FAIM-native query cache with version-aware invalidation.

    Key guarantees:
    - Cache keys include graph_version
    - Version bump → old cache not returned (key is different)
    - Redis down → empty cache (never fails)
    - Cache is acceleration only, never affects truth
    """

    DEFAULT_TTL = 3600  # 1 hour

    def __init__(
        self,
        tenant_id: UUID,
        default_ttl: int = DEFAULT_TTL,
    ) -> None:
        """Initialize query cache for a tenant.

        Args:
            tenant_id: Tenant/project UUID.
            default_ttl: Default TTL in seconds.
        """
        self._tenant_id = str(tenant_id)
        self._default_ttl = default_ttl

    def get(
        self,
        graph_id: str,
        graph_version: int,
        query_vector: Tuple[float, ...],
        profile: str,
        k: int,
    ) -> Optional[List[Tuple[str, float]]]:
        """Get cached query results.

        Args:
            graph_id: Graph identifier.
            graph_version: Current graph version (used in key).
            query_vector: Query vector.
            profile: Profile name (e.g., "strict", "fast").
            k: Number of results.

        Returns:
            Cached results as list of (node_id, score), or None if not cached.
        """
        client = _get_client()
        if client is None:
            return None

        try:
            query_hash = compute_query_hash(query_vector)
            key = make_cache_key(
                self._tenant_id, graph_id, graph_version, query_hash, profile, k
            )

            data = client.get(key)
            if data is None:
                return None

            # Parse cached results
            results = json.loads(data.decode("utf-8"))
            return [(r[0], r[1]) for r in results]

        except Exception as e:
            logger.warning(f"Query cache get failed: {e}")
            return None

    def set(
        self,
        graph_id: str,
        graph_version: int,
        query_vector: Tuple[float, ...],
        profile: str,
        k: int,
        results: List[Tuple[str, float]],
        ttl: Optional[int] = None,
    ) -> bool:
        """Store query results in cache.

        Args:
            graph_id: Graph identifier.
            graph_version: Current graph version (used in key).
            query_vector: Query vector.
            profile: Profile name.
            k: Number of results.
            results: List of (node_id, score) tuples.
            ttl: TTL in seconds (optional).

        Returns:
            True if cached successfully.
        """
        client = _get_client()
        if client is None:
            return False

        try:
            query_hash = compute_query_hash(query_vector)
            key = make_cache_key(
                self._tenant_id, graph_id, graph_version, query_hash, profile, k
            )

            # Serialize results
            data = json.dumps(results)

            # Store with TTL
            client.setex(key, ttl or self._default_ttl, data)
            return True

        except Exception as e:
            logger.warning(f"Query cache set failed: {e}")
            return False

    def invalidate_graph(self, graph_id: str) -> int:
        """Invalidate all cached queries for a graph.

        Note: With version-aware keys, this is optional since
        version bumps automatically invalidate old cache entries.

        Args:
            graph_id: Graph identifier.

        Returns:
            Number of keys deleted.
        """
        client = _get_client()
        if client is None:
            return 0

        try:
            pattern = f"faim:query:{self._tenant_id}:{graph_id}:*"
            keys = list(client.scan_iter(match=pattern))

            if keys:
                return client.delete(*keys)
            return 0

        except Exception as e:
            logger.warning(f"Query cache invalidate failed: {e}")
            return 0

    def clear(self) -> int:
        """Clear all cached queries for this tenant.

        Returns:
            Number of keys deleted.
        """
        client = _get_client()
        if client is None:
            return 0

        try:
            pattern = f"faim:query:{self._tenant_id}:*"
            keys = list(client.scan_iter(match=pattern))

            if keys:
                return client.delete(*keys)
            return 0

        except Exception as e:
            logger.warning(f"Query cache clear failed: {e}")
            return 0


# =============================================================================
# Graph Stats Cache
# =============================================================================


class StatsCache:
    """Cache for graph statistics with version-aware keys."""

    DEFAULT_TTL = 300  # 5 minutes

    def __init__(
        self,
        tenant_id: UUID,
        default_ttl: int = DEFAULT_TTL,
    ) -> None:
        self._tenant_id = str(tenant_id)
        self._default_ttl = default_ttl

    def _key(self, graph_id: str, graph_version: int) -> str:
        """Generate stats cache key."""
        return f"faim:stats:{self._tenant_id}:{graph_id}:v{graph_version}"

    def get(
        self,
        graph_id: str,
        graph_version: int,
    ) -> Optional[Dict[str, Any]]:
        """Get cached stats."""
        client = _get_client()
        if client is None:
            return None

        try:
            data = client.get(self._key(graph_id, graph_version))
            if data is None:
                return None
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            logger.warning(f"Stats cache get failed: {e}")
            return None

    def set(
        self,
        graph_id: str,
        graph_version: int,
        stats: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """Store stats in cache."""
        client = _get_client()
        if client is None:
            return False

        try:
            data = json.dumps(stats)
            client.setex(
                self._key(graph_id, graph_version), ttl or self._default_ttl, data
            )
            return True
        except Exception as e:
            logger.warning(f"Stats cache set failed: {e}")
            return False

    def invalidate(self, graph_id: str) -> int:
        """Invalidate all stats for a graph."""
        client = _get_client()
        if client is None:
            return 0

        try:
            pattern = f"faim:stats:{self._tenant_id}:{graph_id}:*"
            keys = list(client.scan_iter(match=pattern))
            if keys:
                return client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Stats cache invalidate failed: {e}")
            return 0


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "compute_query_hash",
    "make_cache_key",
    "parse_cache_key",
    "QueryCache",
    "StatsCache",
    "is_redis_available",
]
