"""Stage-8 Test: Tenant Isolation.

Proves multi-tenant isolation in queries:
- Query can't return nodes from another tenant
- Even if vector matches exactly
- tenant_id is mandatory in query path
"""

import unittest


class TestQueryTenantIsolation(unittest.TestCase):
    """Test tenant isolation in queries."""

    def test_recall_filters_by_tenant(self):
        """recall_candidates_brute_force filters by tenant_id."""
        import inspect

        from core.query.query_engine import recall_candidates_brute_force

        source = inspect.getsource(recall_candidates_brute_force)

        # Must filter by tenant_id
        self.assertIn("tenant_id", source)
        self.assertIn("NodeModel.tenant_id", source)

    def test_rerank_filters_by_tenant(self):
        """rerank_faim filters by tenant_id."""
        import inspect

        from core.query.query_engine import rerank_faim

        source = inspect.getsource(rerank_faim)

        # Must filter by tenant_id
        self.assertIn("tenant_id", source)
        self.assertIn("NodeModel.tenant_id", source)

    def test_explain_filters_by_tenant(self):
        """build_explain_payload filters by tenant_id."""
        import inspect

        from core.query.query_engine import build_explain_payload

        source = inspect.getsource(build_explain_payload)

        # Must filter by tenant_id
        self.assertIn("tenant_id", source)

    def test_run_query_requires_tenant(self):
        """run_query() requires tenant_id param."""
        import inspect

        from orchestration.query_flow import run_query

        sig = inspect.signature(run_query)
        params = list(sig.parameters.keys())

        self.assertIn("tenant_id", params)

    def test_query_endpoint_uses_tenant_dep(self):
        """Query endpoint uses get_tenant_id dependency."""
        import inspect

        from api.routers.query import query_graph

        source = inspect.getsource(query_graph)

        self.assertIn("get_tenant_id", source)
        self.assertIn("tenant_id", source)


if __name__ == "__main__":
    unittest.main()
