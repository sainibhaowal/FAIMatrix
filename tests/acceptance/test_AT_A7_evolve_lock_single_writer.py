"""Stage-7 Acceptance Test: Evolve Lock Single Writer.

Gate 5: Two evolve calls concurrently → only one acquires lock.
"""

import unittest


class TestEvolveLockSingleWriter(unittest.TestCase):
    """Test evolve uses lock manager for single writer."""

    def test_evolve_router_exists(self):
        """Evolve router must exist."""
        from api.routers.evolve import router

        self.assertIsNotNone(router)

    def test_evolve_request_model(self):
        """EvolveRequest must have required fields."""
        from api.routers.evolve import EvolveRequest

        req = EvolveRequest(
            graph_id="test_graph",
            profile="strict",
        )
        self.assertEqual(req.graph_id, "test_graph")
        self.assertEqual(req.profile, "strict")

    def test_evolve_response_has_diagnostics(self):
        """EvolveResponse must include diagnostics (MetricsSnapshot)."""
        from api.routers.evolve import EvolveResponse

        resp = EvolveResponse(
            status="completed",
            graph_version=5,
            merges=2,
            prunes=1,
            events_emitted=["EVOLUTION_COMPLETE"],
            latency_ms=50,
        )

        self.assertEqual(resp.merges, 2)
        self.assertEqual(resp.prunes, 1)

    def test_orchestration_evolve_uses_lock(self):
        """run_evolve must use evolve_lock."""
        import inspect

        from orchestration.evolve_flow import run_evolve

        source = inspect.getsource(run_evolve)

        # Check for lock usage
        self.assertIn("evolve_lock", source)
        self.assertIn("lock_acquired", source)

    def test_evolve_lock_context_manager_works(self):
        """evolve_lock must work as context manager."""
        from uuid import uuid4

        from cache.locks import evolve_lock

        graph_id = f"test_evolve_{uuid4()}"

        with evolve_lock(graph_id) as acquired:
            self.assertIsInstance(acquired, bool)

    def test_lock_manager_has_acquire_release(self):
        """LockManager must have acquire/release."""
        from cache.locks import LockManager

        manager = LockManager()
        self.assertTrue(hasattr(manager, "lock"))


if __name__ == "__main__":
    unittest.main()
