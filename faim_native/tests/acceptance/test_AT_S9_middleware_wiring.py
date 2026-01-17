"""Stage-9 Acceptance Tests: Middleware and Payload Bounds.

Tests for:
- RateLimitMiddleware registered in app.py
- JSON logging setup
- Payload truncation
"""

import inspect
import unittest


class TestMiddlewareRegistered(unittest.TestCase):
    """Test middleware is registered in app.py."""

    def test_rate_limit_middleware_in_app(self):
        """RateLimitMiddleware is registered."""
        from api.app import create_app

        source = inspect.getsource(create_app)

        self.assertIn("RateLimitMiddleware", source)
        self.assertIn("app.add_middleware(RateLimitMiddleware)", source)

    def test_json_logging_setup_in_app(self):
        """JSON logging is configured in create_app."""
        from api.app import create_app

        source = inspect.getsource(create_app)

        self.assertIn("setup_logging", source)
        self.assertIn("FAIM_LOG_LEVEL", source)

    def test_app_version_is_0_9_0(self):
        """App version is 0.9.0."""
        from api.app import create_app

        source = inspect.getsource(create_app)

        self.assertIn('"0.10.0"', source)


class TestPayloadBounds(unittest.TestCase):
    """Test payload truncation."""

    def test_truncate_payload_exists(self):
        """truncate_payload function exists."""
        from store.journal.event_journal import truncate_payload

        self.assertTrue(callable(truncate_payload))

    def test_default_max_bytes(self):
        """DEFAULT_MAX_PAYLOAD_BYTES is 4096."""
        from store.journal.event_journal import DEFAULT_MAX_PAYLOAD_BYTES

        self.assertEqual(DEFAULT_MAX_PAYLOAD_BYTES, 4096)

    def test_small_payload_not_truncated(self):
        """Small payload is not truncated."""
        from store.journal.event_journal import truncate_payload

        payload = {"key": "value"}
        result = truncate_payload(payload)

        self.assertEqual(result, payload)
        self.assertNotIn("_truncated", result)

    def test_large_payload_truncated(self):
        """Large payload is truncated."""
        from store.journal.event_journal import truncate_payload

        # Create large payload
        payload = {"big_string": "x" * 5000}
        result = truncate_payload(payload, max_bytes=100)

        self.assertIn("_truncated", result)
        self.assertTrue(result["_truncated"])

    def test_long_string_truncated(self):
        """Long string values are truncated."""
        from store.journal.event_journal import truncate_payload

        payload = {"long": "x" * 200}
        result = truncate_payload(payload, max_bytes=50)

        self.assertIn("[truncated]", result["long"])

    def test_get_max_payload_bytes(self):
        """get_max_payload_bytes returns config value."""
        from store.journal.event_journal import get_max_payload_bytes

        result = get_max_payload_bytes()

        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)


if __name__ == "__main__":
    unittest.main()
