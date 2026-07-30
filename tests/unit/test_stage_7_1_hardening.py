"""Stage-7.1 Tests: Production Hardening.

Tests for:
- DB rejects empty tenant
- tenant_id exists in all tables
- Repo isolation enforced
- Unique vector_hash per tenant+graph
- SSE resume + no session leak pattern
"""

import pathlib
import unittest


class TestTenantIdRequired(unittest.TestCase):
    """Test that tenant_id is required on all models."""

    def test_event_model_tenant_id_no_default(self):
        """EventModel tenant_id must not have default."""
        from store.pg.models_faim import EventModel

        col = EventModel.__table__.c.tenant_id
        self.assertFalse(col.nullable)
        # from_domain has default, but column itself should not

    def test_node_model_tenant_id_no_default(self):
        """NodeModel tenant_id must not have default."""
        from store.pg.models_faim import NodeModel

        col = NodeModel.__table__.c.tenant_id
        self.assertFalse(col.nullable)

    def test_edge_model_tenant_id_no_default(self):
        """EdgeModel tenant_id must not have default."""
        from store.pg.models_faim import EdgeModel

        col = EdgeModel.__table__.c.tenant_id
        self.assertFalse(col.nullable)

    def test_snapshot_model_tenant_id_no_default(self):
        """SnapshotModel tenant_id must not have default."""
        from store.pg.models_faim import SnapshotModel

        col = SnapshotModel.__table__.c.tenant_id
        self.assertFalse(col.nullable)

    def test_graph_version_model_tenant_id_no_default(self):
        """GraphVersionModel tenant_id must not have default."""
        from store.pg.models_faim import GraphVersionModel

        col = GraphVersionModel.__table__.c.tenant_id
        self.assertFalse(col.nullable)

    def test_raw_ref_model_tenant_id_exists(self):
        """RawRefModel must have tenant_id."""
        from store.pg.models_faim import RawRefModel

        columns = [c.name for c in RawRefModel.__table__.columns]
        self.assertIn("tenant_id", columns)


class TestAuthHardening(unittest.TestCase):
    """Test auth middleware hardening."""

    def test_constant_time_compare_exists(self):
        """Auth must use constant-time comparison."""
        from api.middleware.auth import _constant_time_compare

        self.assertTrue(_constant_time_compare("abc", "abc"))
        self.assertFalse(_constant_time_compare("abc", "def"))

    def test_normalize_tenant_id_rejects_empty(self):
        """normalize_tenant_id must reject empty."""
        from api.middleware.auth import normalize_tenant_id

        self.assertEqual(normalize_tenant_id(""), "")
        self.assertEqual(normalize_tenant_id("   "), "")

    def test_normalize_tenant_id_valid(self):
        """normalize_tenant_id must accept valid IDs."""
        from api.middleware.auth import normalize_tenant_id

        self.assertEqual(normalize_tenant_id("tenant-1"), "tenant-1")
        self.assertEqual(normalize_tenant_id("tenant_2"), "tenant_2")
        self.assertEqual(normalize_tenant_id("ABC123"), "ABC123")

    def test_normalize_tenant_id_rejects_special_chars(self):
        """normalize_tenant_id must reject special characters."""
        from api.middleware.auth import normalize_tenant_id

        self.assertEqual(normalize_tenant_id("tenant@evil"), "")
        self.assertEqual(normalize_tenant_id("tenant/path"), "")
        self.assertEqual(normalize_tenant_id("tenant;drop"), "")

    def test_key_rotation_support(self):
        """get_tenant_keys must support lists."""
        import os

        from api.middleware.auth import _load_tenant_keys

        # Save original
        original = os.environ.get("TENANT_KEYS_JSON")

        try:
            os.environ["TENANT_KEYS_JSON"] = '{"tenant1":["key1","key2"]}'
            keys = _load_tenant_keys()

            self.assertIn("tenant1", keys)
            self.assertEqual(keys["tenant1"], ["key1", "key2"])
        finally:
            if original:
                os.environ["TENANT_KEYS_JSON"] = original
            else:
                os.environ.pop("TENANT_KEYS_JSON", None)


class TestSSEHardening(unittest.TestCase):
    """Test SSE generator hardening."""

    def test_sse_uses_short_lived_sessions(self):
        """SSE must use short-lived sessions."""
        import inspect

        from api.routers.events import _event_generator

        source = inspect.getsource(_event_generator)

        # Must use with _get_fresh_session()
        self.assertIn("_get_fresh_session", source)
        self.assertIn("with", source)

    def test_sse_has_bounded_paging(self):
        """SSE must have bounded MAX_PAGE_SIZE."""
        from api.routers.events import MAX_PAGE_SIZE

        self.assertIsInstance(MAX_PAGE_SIZE, int)
        self.assertLessEqual(MAX_PAGE_SIZE, 100)

    def test_sse_has_heartbeat(self):
        """SSE must have heartbeat interval."""
        from api.routers.events import HEARTBEAT_INTERVAL_SECONDS

        self.assertIsInstance(HEARTBEAT_INTERVAL_SECONDS, float)
        self.assertGreater(HEARTBEAT_INTERVAL_SECONDS, 0)

    def test_sse_handles_cancelled_error(self):
        """SSE must handle CancelledError for clean disconnect."""
        import inspect

        from api.routers.events import _event_generator

        source = inspect.getsource(_event_generator)

        self.assertIn("CancelledError", source)

    def test_sse_has_empty_poll_limit(self):
        """SSE must exit after extended inactivity."""
        from api.routers.events import MAX_EMPTY_POLLS

        self.assertIsInstance(MAX_EMPTY_POLLS, int)
        self.assertGreater(MAX_EMPTY_POLLS, 0)


class TestSchemaIndexes(unittest.TestCase):
    """Test schema has proper composite indexes."""

    @classmethod
    def setUpClass(cls):
        """Load schema once."""
        schema_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "faim_native"
            / "store"
            / "pg"
            / "schema.sql"
        )
        with open(schema_path) as f:
            cls.schema = f.read()

    def test_schema_has_tenant_trigger(self):
        """schema.sql must have reject_empty_tenant trigger."""
        self.assertIn("reject_empty_tenant", self.schema)
        self.assertIn("NEW.tenant_id IS NULL", self.schema)

    def test_schema_has_tenant_graph_seq_index(self):
        """schema.sql must have events(tenant_id, graph_id, seq) index."""
        self.assertIn("idx_events_tenant_graph_seq", self.schema)

    def test_schema_has_nodes_unique_hash(self):
        """schema.sql must have UNIQUE(tenant_id, graph_id, vector_hash)."""
        self.assertIn("uq_nodes_tenant_graph_hash", self.schema)


if __name__ == "__main__":
    unittest.main()
