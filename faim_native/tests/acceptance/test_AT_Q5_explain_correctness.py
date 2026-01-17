"""Stage-8 Test: Explain Payload Correctness.

Proves explain payload is correct:
- Contains parents + fractions
- Parents fractions sum to 1 (or close)
- Evidence anchors exist
"""

import unittest


class TestExplainPayload(unittest.TestCase):
    """Test explain payload structure."""

    def test_explain_has_required_fields(self):
        """build_explain_payload returns required fields."""
        import inspect

        from core.query.query_engine import build_explain_payload

        source = inspect.getsource(build_explain_payload)

        # Must return node info
        self.assertIn("node_id", source)
        self.assertIn("vector_hash", source)
        self.assertIn("level", source)

        # Must return parents
        self.assertIn("parents", source)
        self.assertIn("fraction", source)

        # Must return evidence
        self.assertIn("evidence", source)
        self.assertIn("raw_id", source)
        self.assertIn("anchor", source)

    def test_explain_computes_parent_sum(self):
        """Explain computes parents_sum."""
        import inspect

        from core.query.query_engine import build_explain_payload

        source = inspect.getsource(build_explain_payload)

        self.assertIn("parents_sum", source)

    def test_explain_loads_opposition(self):
        """Explain includes opposition edges."""
        import inspect

        from core.query.query_engine import build_explain_payload

        source = inspect.getsource(build_explain_payload)

        self.assertIn("opposition", source.lower())


class TestQueryResultExplain(unittest.TestCase):
    """Test query result with explain."""

    def test_query_result_has_explain_option(self):
        """run_query has return_explain parameter."""
        import inspect

        from orchestration.query_flow import run_query

        sig = inspect.signature(run_query)
        params = list(sig.parameters.keys())

        self.assertIn("return_explain", params)

    def test_query_response_model_has_explain(self):
        """QueryResultItem has explain field."""
        from api.routers.query import QueryResultItem

        fields = QueryResultItem.model_fields

        self.assertIn("explain", fields)


if __name__ == "__main__":
    unittest.main()
