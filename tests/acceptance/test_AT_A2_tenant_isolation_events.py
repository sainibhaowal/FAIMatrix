"""Stage-7 Acceptance Test: Tenant Isolation Events.

Gate 2: Tenant A cannot read Tenant B events/nodes/snapshots
"""

import unittest


class TestTenantIsolationEvents(unittest.TestCase):
    """Test tenant isolation for events."""

    def test_event_model_has_tenant_id(self):
        """EventModel must have tenant_id column."""
        from store.pg.models_faim import EventModel

        # Check tenant_id column exists
        columns = [c.name for c in EventModel.__table__.columns]
        self.assertIn("tenant_id", columns)

    def test_node_model_has_tenant_id(self):
        """NodeModel must have tenant_id column."""
        from store.pg.models_faim import NodeModel

        columns = [c.name for c in NodeModel.__table__.columns]
        self.assertIn("tenant_id", columns)

    def test_edge_model_has_tenant_id(self):
        """EdgeModel must have tenant_id column."""
        from store.pg.models_faim import EdgeModel

        columns = [c.name for c in EdgeModel.__table__.columns]
        self.assertIn("tenant_id", columns)

    def test_snapshot_model_has_tenant_id(self):
        """SnapshotModel must have tenant_id column."""
        from store.pg.models_faim import SnapshotModel

        columns = [c.name for c in SnapshotModel.__table__.columns]
        self.assertIn("tenant_id", columns)

    def test_graph_version_model_has_tenant_id(self):
        """GraphVersionModel must have tenant_id column."""
        from store.pg.models_faim import GraphVersionModel

        columns = [c.name for c in GraphVersionModel.__table__.columns]
        self.assertIn("tenant_id", columns)

    def test_cache_key_includes_tenant(self):
        """Cache keys must include tenant for isolation."""
        from cache.query_cache import make_cache_key

        key_a = make_cache_key("tenantA", "graph1", 1, "hash", "strict", 10)
        key_b = make_cache_key("tenantB", "graph1", 1, "hash", "strict", 10)

        # Different tenants = different keys
        self.assertNotEqual(key_a, key_b)
        self.assertIn("tenantA", key_a)
        self.assertIn("tenantB", key_b)

    def test_context_includes_tenant_id(self):
        """FAIMContext must include tenant_id."""
        from api.deps import FAIMContext

        ctx = FAIMContext(tenant_id="test_tenant", request_id="req123")
        self.assertEqual(ctx.tenant_id, "test_tenant")


if __name__ == "__main__":
    unittest.main()
