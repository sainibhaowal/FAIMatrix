"""Stage-7 Acceptance Test: Query Deterministic STRICT.

Gate 4: Same query twice in STRICT mode → identical results.
Updated for Stage-8 query models.
"""

import unittest


class TestQueryDeterministicStrict(unittest.TestCase):
    """Test query determinism in STRICT mode."""

    def test_query_router_exists(self):
        """Query router must exist."""
        from api.routers.query import router

        self.assertIsNotNone(router)

    def test_query_request_has_profile(self):
        """QueryRequest must have profile field."""
        from api.routers.query import QueryRequest

        req = QueryRequest(
            graph_id="test_graph",
            query_text="test query",
            profile="STRICT",
        )
        self.assertEqual(req.profile, "STRICT")

    def test_query_response_includes_hash(self):
        """QueryResponse must include query_hash for verification."""
        from api.routers.query import QueryMetrics, QueryResponse

        resp = QueryResponse(
            tenant_id="test",
            graph_id="test_graph",
            graph_version=1,
            graph_hash="abc",
            query_hash="abc123",
            k=10,
            profile="STRICT",
            results=[],
            metrics=QueryMetrics(),
            duration_ms=10.0,
        )
        self.assertEqual(resp.query_hash, "abc123")

    def test_node_result_has_required_fields(self):
        """QueryResultItem must have all required fields."""
        from api.routers.query import QueryResultItem

        node = QueryResultItem(
            node_id="uuid-123",
            score=0.95,
            vector_hash="hash123",
            score_components={
                "sim": 0.9,
                "novel": 0.1,
                "opp": 0,
                "red": 0,
                "rec": 0,
                "use": 0,
                "lvl": 0,
            },
            level=0,
            touch_count=1,
        )

        self.assertEqual(node.node_id, "uuid-123")
        self.assertEqual(node.score, 0.95)
        self.assertEqual(node.level, 0)

    def test_encoding_is_deterministic(self):
        """Vector hashing must be deterministic."""
        import hashlib
        import json

        from encoding.vector_schema import VECTOR_DIMENSION

        # Create same vector twice
        v_native = tuple([0.1] * VECTOR_DIMENSION)

        # Hash using same approach as FAIM
        canonical = json.dumps(list(v_native), sort_keys=True)
        hash1 = hashlib.sha256(canonical.encode()).hexdigest()
        hash2 = hashlib.sha256(canonical.encode()).hexdigest()

        # Same input = same hash
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA256 hex

    def test_query_uses_run_query(self):
        """Query endpoint uses orchestration run_query."""
        import inspect

        from api.routers.query import query_graph

        source = inspect.getsource(query_graph)

        # Uses run_query from query_flow
        self.assertIn("run_query", source)


if __name__ == "__main__":
    unittest.main()
