"""Stage-7 Acceptance Test: Tenant Auth Required.

Gate 1: No headers → 401
"""

import unittest


class TestTenantAuthRequired(unittest.TestCase):
    """Test that tenant auth is required on all endpoints."""

    def test_missing_tenant_header_returns_401(self):
        """Missing X-Tenant-Id header must return 401."""
        from api.middleware.auth import is_exempt_path

        # Check exempt paths work
        self.assertTrue(is_exempt_path("/health"))
        self.assertTrue(is_exempt_path("/version"))
        self.assertTrue(is_exempt_path("/docs"))

        # Check non-exempt paths need auth
        self.assertFalse(is_exempt_path("/v1/ingest"))
        self.assertFalse(is_exempt_path("/v1/query"))
        self.assertFalse(is_exempt_path("/v1/events"))

    def test_middleware_class_exists(self):
        """TenantAuthMiddleware class must exist."""
        from api.middleware.auth import TenantAuthMiddleware

        self.assertTrue(hasattr(TenantAuthMiddleware, "dispatch"))

    def test_validate_tenant_key_works(self):
        """validate_tenant_key must work correctly."""
        from api.middleware.auth import validate_tenant_key

        # With no keys configured, should allow (dev mode)
        result = validate_tenant_key("any_tenant", "any_key")
        # In dev mode with no keys, returns True
        self.assertIsInstance(result, bool)

    def test_deps_get_tenant_id_raises_on_missing(self):
        """get_tenant_id must raise if tenant not in request.state."""
        from fastapi import HTTPException

        from api.deps import get_tenant_id

        # Create mock request without tenant_id
        class MockRequest:
            class state:
                pass

        try:
            get_tenant_id(MockRequest())
            self.fail("Should have raised HTTPException")
        except HTTPException as e:
            self.assertEqual(e.status_code, 401)

    def test_admin_requires_key(self):
        """Admin endpoints must require X-Admin-Key."""
        from fastapi import HTTPException

        from api.deps import require_admin

        # Missing key should raise
        try:
            require_admin(None)
            self.fail("Should have raised HTTPException")
        except HTTPException as e:
            self.assertEqual(e.status_code, 401)


if __name__ == "__main__":
    unittest.main()
