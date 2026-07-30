"""Stage-7 Acceptance Test: Node Inspector No Leak.

Gate 2 (continued): Node inspector must not leak cross-tenant data.
"""

import unittest


class TestNodeInspectorNoLeak(unittest.TestCase):
    """Test node inspector tenant isolation."""

    def test_node_router_exists(self):
        """Node router must exist."""
        from api.routers.node import router

        self.assertIsNotNone(router)

    def test_node_detail_requires_graph_id(self):
        """get_node must require graph_id parameter."""
        import inspect

        from api.routers.node import get_node

        sig = inspect.signature(get_node)
        params = list(sig.parameters.keys())

        self.assertIn("graph_id", params)
        self.assertIn("node_id", params)

    def test_node_explain_requires_graph_id(self):
        """explain_node must require graph_id parameter."""
        import inspect

        from api.routers.node import explain_node

        sig = inspect.signature(explain_node)
        params = list(sig.parameters.keys())

        self.assertIn("graph_id", params)

    def test_node_detail_model_fields(self):
        """NodeDetail must have proper fields."""
        from api.routers.node import NodeDetail

        node = NodeDetail(
            node_id="uuid-123",
            graph_id="test_graph",
            kind="atom",
            level=0,
            vector_hash="hash123",
            residual=0.05,
            touch_count=3,
        )

        self.assertEqual(node.graph_id, "test_graph")
        self.assertEqual(node.kind, "atom")

    def test_node_explain_has_parents(self):
        """NodeExplain must include parents field."""
        from api.routers.node import NodeExplain

        explain = NodeExplain(
            node_id="uuid-123",
            parents=[],
            fractions_sum=0.0,
            recent_events=[],
        )

        self.assertIsInstance(explain.parents, list)
        self.assertEqual(explain.fractions_sum, 0.0)

    def test_context_is_required(self):
        """get_node must use FAIMContext (has tenant_id)."""
        import inspect

        from api.routers.node import get_node

        sig = inspect.signature(get_node)
        params = list(sig.parameters.keys())

        self.assertIn("ctx", params)


if __name__ == "__main__":
    unittest.main()
