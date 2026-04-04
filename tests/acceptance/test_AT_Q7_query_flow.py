"""Stage-8 Test: Full Query Flow.

End-to-end test of query flow:
- QueryResult structure
- Metrics included
- Score components included
"""

import unittest


class TestQueryResultStructure(unittest.TestCase):
    """Test QueryResult structure."""

    def test_query_result_has_required_fields(self):
        """QueryResult has all required fields."""
        from dataclasses import fields

        from orchestration.query_flow import QueryResult

        field_names = [f.name for f in fields(QueryResult)]

        self.assertIn("tenant_id", field_names)
        self.assertIn("graph_id", field_names)
        self.assertIn("graph_version", field_names)
        self.assertIn("query_hash", field_names)
        self.assertIn("k", field_names)
        self.assertIn("results", field_names)
        self.assertIn("metrics", field_names)
        self.assertIn("profile", field_names)
        self.assertIn("duration_ms", field_names)

    def test_query_result_to_dict(self):
        """QueryResult.to_dict() works."""
        from orchestration.ingest_flow import FAIMProfile
        from orchestration.query_flow import QueryResult

        result = QueryResult(
            tenant_id="test",
            graph_id="g1",
            graph_version=1,
            graph_hash="abc",
            query_hash="def",
            k=10,
            results=[],
            metrics={},
            profile=FAIMProfile.STRICT,
        )

        d = result.to_dict()

        self.assertEqual(d["tenant_id"], "test")
        self.assertEqual(d["graph_id"], "g1")


class TestQueryAPIContract(unittest.TestCase):
    """Test Query API contract."""

    def test_query_request_model(self):
        """QueryRequest has required fields."""
        from api.routers.query import QueryRequest

        fields = QueryRequest.model_fields

        self.assertIn("graph_id", fields)
        self.assertIn("query_text", fields)
        self.assertIn("k", fields)
        self.assertIn("profile", fields)
        self.assertIn("return_explain", fields)

    def test_query_response_model(self):
        """QueryResponse has required fields."""
        from api.routers.query import QueryResponse

        fields = QueryResponse.model_fields

        self.assertIn("tenant_id", fields)
        self.assertIn("graph_id", fields)
        self.assertIn("graph_version", fields)
        self.assertIn("graph_hash", fields)
        self.assertIn("query_hash", fields)
        self.assertIn("results", fields)
        self.assertIn("metrics", fields)

    def test_score_components_model(self):
        """ScoreComponents model exists."""
        from api.routers.query import ScoreComponents

        fields = ScoreComponents.model_fields

        self.assertIn("sim", fields)
        self.assertIn("novel", fields)
        self.assertIn("opp", fields)
        self.assertIn("red", fields)
        self.assertIn("rec", fields)
        self.assertIn("use", fields)
        self.assertIn("lvl", fields)


if __name__ == "__main__":
    unittest.main()
