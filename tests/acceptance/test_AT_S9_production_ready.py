"""Stage-9 Acceptance Tests: Production Readiness.

Tests for:
- /ready endpoint
- Logging with request_id
- Schema has required tables
- Payload bounds
"""

import inspect
import unittest


class TestReadyEndpoint(unittest.TestCase):
    """Test /ready endpoint."""

    def test_ready_endpoint_exists(self):
        """GET /ready endpoint exists."""
        from api.routers.health import readiness_check

        self.assertTrue(callable(readiness_check))

    def test_required_tables_defined(self):
        """Required tables list is defined."""
        from api.routers.health import REQUIRED_TABLES

        self.assertIn("raw_refs", REQUIRED_TABLES)
        self.assertIn("events", REQUIRED_TABLES)
        self.assertIn("nodes", REQUIRED_TABLES)
        self.assertIn("edges", REQUIRED_TABLES)
        self.assertIn("ingest_dedup", REQUIRED_TABLES)

    def test_readiness_response_model(self):
        """ReadinessResponse model has required fields."""
        from api.routers.health import ReadinessResponse

        resp = ReadinessResponse(
            status="ready",
            db_connected=True,
            tables_ok=True,
            migrations_ok=True,
        )

        self.assertEqual(resp.status, "ready")
        self.assertTrue(resp.db_connected)


class TestLogging(unittest.TestCase):
    """Test structured logging."""

    def test_json_formatter_exists(self):
        """JSONFormatter class exists."""
        from runtime.logging import JSONFormatter

        self.assertTrue(callable(JSONFormatter))

    def test_context_logger_exists(self):
        """ContextLogger class exists."""
        from runtime.logging import ContextLogger, get_logger

        logger = get_logger("test")
        self.assertIsInstance(logger, ContextLogger)

    def test_logger_bind_context(self):
        """Logger can bind context."""
        from runtime.logging import get_logger

        logger = get_logger("test")
        bound = logger.bind(request_id="req123", tenant_id="t1")

        self.assertEqual(bound._context["request_id"], "req123")


class TestSchemaCompleteness(unittest.TestCase):
    """Test schema contains Stage-9 tables."""

    def test_schema_has_ingest_dedup(self):
        """Schema contains ingest_dedup table."""
        schema_path = "faim_native/store/pg/schema.sql"

        with open(schema_path) as f:
            content = f.read()

        self.assertIn("CREATE TABLE IF NOT EXISTS ingest_dedup", content)
        self.assertIn("packet_hash", content)

    def test_schema_has_jobs(self):
        """Schema contains jobs table."""
        schema_path = "faim_native/store/pg/schema.sql"

        with open(schema_path) as f:
            content = f.read()

        self.assertIn("CREATE TABLE IF NOT EXISTS jobs", content)
        self.assertIn("job_id", content)


class TestPayloadBounds(unittest.TestCase):
    """Test payload size bounds."""

    def test_config_has_payload_limits(self):
        """Config has payload limit settings."""

        import os

        os.environ["DATABASE_URL"] = "postgresql://localhost/test"
        os.environ["TENANT_KEYS_JSON"] = '{"t1": ["k1"]}'

        from runtime.config import load_config, reset_config

        reset_config()
        config = load_config()

        self.assertEqual(config.event_payload_max_bytes, 4096)
        self.assertEqual(config.explain_max_items, 25)

        reset_config()
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("TENANT_KEYS_JSON", None)


class TestVersionInfo(unittest.TestCase):
    """Test version endpoint."""

    def test_version_is_0_9_0(self):
        """Version is 0.9.0 for Stage-9."""
        from api.routers.health import version_info

        source = inspect.getsource(version_info)
        self.assertIn('"0.10.0"', source)
        self.assertIn('"10"', source)


if __name__ == "__main__":
    unittest.main()
