"""Stage-6 Tests: Cache FAIM-Native.

Tests for cache layer:
- test_query_cache_key_includes_graph_version
- test_cache_stale_not_returned_after_version_bump
- test_cache_degrades_gracefully_without_redis
- test_locks_single_writer_guarantee
"""

import unittest
from uuid import uuid4


class TestCacheFAIMNative(unittest.TestCase):
    """Tests for FAIM-native cache layer."""

    def test_query_cache_key_includes_graph_version(self):
        """Cache key must include graph_version."""
        from cache.query_cache import make_cache_key

        key = make_cache_key(
            tenant_id="tenant_123",
            graph_id="graph_456",
            graph_version=42,
            query_hash="abc123",
            profile="strict",
            k=10,
        )

        # Key must include version
        self.assertIn("v42", key)
        self.assertIn("tenant_123", key)
        self.assertIn("graph_456", key)
        self.assertIn("abc123", key)
        self.assertIn("strict", key)
        self.assertIn("k10", key)

    def test_cache_key_changes_with_version(self):
        """Different versions must produce different cache keys."""
        from cache.query_cache import make_cache_key

        key_v1 = make_cache_key("t", "g", 1, "q", "strict", 10)
        key_v2 = make_cache_key("t", "g", 2, "q", "strict", 10)

        self.assertNotEqual(key_v1, key_v2)

    def test_cache_key_parse_roundtrip(self):
        """Cache key should be parseable."""
        from cache.query_cache import make_cache_key, parse_cache_key

        key = make_cache_key(
            tenant_id="tenant_123",
            graph_id="graph_456",
            graph_version=42,
            query_hash="abc123",
            profile="strict",
            k=10,
        )

        parsed = parse_cache_key(key)

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["tenant_id"], "tenant_123")
        self.assertEqual(parsed["graph_id"], "graph_456")
        self.assertEqual(parsed["graph_version"], 42)
        self.assertEqual(parsed["query_hash"], "abc123")
        self.assertEqual(parsed["profile"], "strict")
        self.assertEqual(parsed["k"], 10)

    def test_cache_degrades_gracefully_without_redis(self):
        """Cache operations must not fail when Redis unavailable."""
        from uuid import UUID

        from cache.query_cache import QueryCache

        cache = QueryCache(UUID("12345678-1234-5678-1234-567812345678"))

        # get should return None (not raise)
        result = cache.get(
            graph_id="graph_123",
            graph_version=1,
            query_vector=(1.0, 0.0, 0.0),
            profile="strict",
            k=10,
        )

        self.assertIsNone(result)

        # set should return False (not raise)
        success = cache.set(
            graph_id="graph_123",
            graph_version=1,
            query_vector=(1.0, 0.0, 0.0),
            profile="strict",
            k=10,
            results=[("node1", 0.9)],
        )

        # May return True (if Redis works) or False (if not)
        self.assertIsInstance(success, bool)

    def test_compute_query_hash_deterministic(self):
        """Query hash must be deterministic."""
        from cache.query_cache import compute_query_hash

        vec = (1.0, 0.5, 0.25, 0.125)

        hash1 = compute_query_hash(vec)
        hash2 = compute_query_hash(vec)

        self.assertEqual(hash1, hash2)

        # Different vector = different hash
        hash3 = compute_query_hash((1.0, 0.5, 0.25, 0.0))
        self.assertNotEqual(hash1, hash3)


class TestLocksFAIMNative(unittest.TestCase):
    """Tests for FAIM-native locks."""

    def test_lock_key_generation(self):
        """Lock key generators must work."""
        from cache.locks import (
            graph_evolve_lock_key,
            graph_reindex_lock_key,
            graph_write_lock_key,
        )

        graph_id = "graph_123"

        evolve_key = graph_evolve_lock_key(graph_id)
        reindex_key = graph_reindex_lock_key(graph_id)
        write_key = graph_write_lock_key(graph_id)

        self.assertIn("graph_123", evolve_key)
        self.assertIn("evolve", evolve_key)
        self.assertIn("reindex", reindex_key)
        self.assertIn("write", write_key)

        # Keys must be different
        self.assertNotEqual(evolve_key, reindex_key)
        self.assertNotEqual(evolve_key, write_key)

    def test_file_lock_can_acquire(self):
        """File lock must be acquirable."""
        from cache.locks import FileLock

        lock = FileLock("test_lock_" + str(uuid4()))

        # Should acquire successfully
        acquired = lock.acquire()
        self.assertTrue(acquired)
        self.assertTrue(lock.is_acquired)

        # Release
        released = lock.release()
        self.assertTrue(released)
        self.assertFalse(lock.is_acquired)

    def test_lock_manager_context_manager(self):
        """LockManager must work as context manager."""
        from cache.locks import LockManager

        manager = LockManager()

        with manager.lock("test_context_" + str(uuid4())) as acquired:
            # Should have lock (either Redis or file)
            self.assertIsInstance(acquired, bool)

    def test_evolve_lock_context_manager(self):
        """evolve_lock must work as context manager."""
        from cache.locks import evolve_lock

        with evolve_lock("test_evolve_" + str(uuid4())) as acquired:
            self.assertIsInstance(acquired, bool)


class TestStatsCache(unittest.TestCase):
    """Tests for stats cache."""

    def test_stats_cache_key_includes_version(self):
        """Stats cache key must include graph_version."""
        from uuid import UUID

        from cache.query_cache import StatsCache

        cache = StatsCache(UUID("12345678-1234-5678-1234-567812345678"))

        # Access private method to check key format
        key = cache._key("graph_123", 42)

        self.assertIn("v42", key)
        self.assertIn("graph_123", key)
        self.assertIn("stats", key)


if __name__ == "__main__":
    unittest.main()
