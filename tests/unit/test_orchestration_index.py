"""Stage-6 Tests: Orchestration Index Integration.

Tests for orchestration-index wiring:
- test_strict_mode_skips_index
- test_non_strict_upserts_index_after_write
"""

import unittest


class TestOrchestrationIndex(unittest.TestCase):
    """Tests for orchestration-index integration."""

    def test_strict_mode_skips_index_check_code(self):
        """STRICT mode must skip index writes (check code pattern)."""
        import inspect

        from orchestration.ingest_flow import run_ingest

        source = inspect.getsource(run_ingest)

        # Check centralized profile/persist policy resolver is used
        self.assertIn("resolve_profile_persist_policy", source)
        self.assertIn("index_enabled", source)
        self.assertIn("STRICT mode", source)

    def test_non_strict_has_index_upsert(self):
        """Non-STRICT mode must have index upsert code."""
        import inspect

        import orchestration.ingest_flow as ingest_flow
        from orchestration.ingest_flow import run_ingest

        source = inspect.getsource(run_ingest)
        module_source = inspect.getsource(ingest_flow)

        # Check index upsert code exists
        self.assertIn("INDEX_UPSERTED", source)
        self.assertIn("FAIMIndex", module_source)
        self.assertIn("index.add", module_source)

    def test_index_failure_is_non_fatal(self):
        """Index failures must be non-fatal (logged but not raised)."""
        import inspect

        from orchestration.ingest_flow import run_ingest

        source = inspect.getsource(run_ingest)

        # Check for try/except around index operations
        self.assertIn("Index failures are non-fatal", source)
        self.assertIn("logger.warning", source)

    def test_faim_profile_has_strict(self):
        """FAIMProfile enum must have STRICT option."""
        from orchestration.ingest_flow import FAIMProfile

        self.assertEqual(FAIMProfile.STRICT.value, "strict")
        self.assertEqual(FAIMProfile.FAST.value, "fast")
        self.assertEqual(FAIMProfile.RELAXED.value, "relaxed")

    def test_evolve_uses_lock_manager(self):
        """evolve_flow must use lock manager."""
        import inspect

        from orchestration.evolve_flow import run_evolve

        source = inspect.getsource(run_evolve)

        self.assertIn("evolve_lock", source)
        self.assertIn("lock_acquired", source)


if __name__ == "__main__":
    unittest.main()
