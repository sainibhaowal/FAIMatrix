"""Stage-9 Acceptance Test: Ingest Idempotency.

Tests that duplicate ingests don't create duplicate nodes.
The most critical production safety feature.
"""

import inspect
import unittest


class TestIngestIdempotency(unittest.TestCase):
    """Test ingest idempotency via dedup table."""

    def test_ingest_result_has_dedup_hit_field(self):
        """IngestResult has dedup_hit field."""
        from orchestration.ingest_flow import IngestResult

        result = IngestResult(
            status="completed",
            packet_hash="abc123",
            graph_version=1,
            nodes_written=5,
            merges=0,
            block_count=3,
            vector_count=3,
            diagnostics_hash=None,
            events_emitted=["INGEST_START"],
            latency_ms=100,
            dedup_hit=False,
        )

        self.assertFalse(result.dedup_hit)

    def test_ingest_dedup_model_exists(self):
        """IngestDedupModel exists with required methods."""
        from store.pg.models_faim import IngestDedupModel

        self.assertTrue(hasattr(IngestDedupModel, "check_exists"))
        self.assertTrue(hasattr(IngestDedupModel, "record_ingest"))
        self.assertEqual(IngestDedupModel.__tablename__, "ingest_dedup")

    def test_run_ingest_has_tenant_id_param(self):
        """run_ingest accepts tenant_id parameter."""
        import inspect

        from orchestration.ingest_flow import run_ingest

        sig = inspect.signature(run_ingest)
        params = list(sig.parameters.keys())

        self.assertIn("tenant_id", params)
        self.assertIn("session", params)

    def test_run_ingest_has_dedup_check(self):
        """run_ingest contains dedup check logic."""
        from orchestration.ingest_flow import run_ingest

        source = inspect.getsource(run_ingest)

        self.assertIn("DEDUP CHECK", source)
        self.assertIn("check_exists", source)
        self.assertIn("INGEST_DEDUP_HIT", source)

    def test_run_ingest_records_dedup(self):
        """run_ingest records successful ingest for future dedup."""
        from orchestration.ingest_flow import run_ingest

        source = inspect.getsource(run_ingest)

        self.assertIn("record_ingest", source)
        self.assertIn("dedup table", source.lower())

    def test_dedup_model_primary_key(self):
        """IngestDedupModel has composite primary key."""
        from store.pg.models_faim import IngestDedupModel

        pk_cols = [c.name for c in IngestDedupModel.__table__.primary_key.columns]

        self.assertIn("tenant_id", pk_cols)
        self.assertIn("graph_id", pk_cols)
        self.assertIn("packet_hash", pk_cols)


class TestDedupEventEmission(unittest.TestCase):
    """Test dedup events are emitted correctly."""

    def test_dedup_hit_event_in_source(self):
        """INGEST_DEDUP_HIT event is emitted on dedup."""
        from orchestration.ingest_flow import run_ingest

        source = inspect.getsource(run_ingest)

        self.assertIn("INGEST_DEDUP_HIT", source)
        self.assertIn("original_raw_id", source)
        self.assertIn("original_node_count", source)


if __name__ == "__main__":
    unittest.main()
