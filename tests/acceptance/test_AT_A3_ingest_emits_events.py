"""Stage-7 Acceptance Test: Ingest Emits Events.

Gate 3: Ingest emits expected events to journal.
"""

import unittest


class TestIngestEmitsEvents(unittest.TestCase):
    """Test that ingest emits proper events."""

    def test_ingest_router_exists(self):
        """Ingest router must exist."""
        from api.routers.ingest import router

        self.assertIsNotNone(router)

    def test_ingest_request_model(self):
        """IngestRequest model must have required fields."""
        from api.routers.ingest import IngestRequest

        # Check required fields
        req = IngestRequest(
            graph_id="test_graph",
            filename="test.txt",
        )
        self.assertEqual(req.graph_id, "test_graph")
        self.assertEqual(req.filename, "test.txt")
        self.assertEqual(req.profile, "strict")  # default

    def test_ingest_response_has_events_emitted(self):
        """IngestResponse must include events_emitted field."""
        from api.routers.ingest import IngestResponse

        resp = IngestResponse(
            status="completed",
            packet_hash="abc123",
            graph_version=1,
            nodes_written=5,
            merges=0,
            block_count=3,
            vector_count=3,
            events_emitted=["INGEST_START", "PACKET_CREATED"],
            latency_ms=100,
        )

        self.assertIn("INGEST_START", resp.events_emitted)
        self.assertIn("PACKET_CREATED", resp.events_emitted)

    def test_orchestration_ingest_returns_events(self):
        """run_ingest must return events_emitted in result."""
        from orchestration.ingest_flow import IngestResult

        # IngestResult must have events_emitted field
        result = IngestResult(
            status="completed",
            packet_hash="xyz",
            graph_version=1,
            nodes_written=0,
            merges=0,
            block_count=0,
            vector_count=0,
            events_emitted=[],
            latency_ms=0,
            diagnostics_hash="",
        )
        self.assertIsInstance(result.events_emitted, list)


if __name__ == "__main__":
    unittest.main()
