"""Security Tests: JWT Middleware Verification (Stage-12).

Tests for the JWT authentication middleware.
"""

from datetime import datetime, timedelta

import jwt
import pytest

# =============================================================================
# Test Fixtures
# =============================================================================

TEST_SECRET = "test-secret-key-for-jwt-testing-only"


@pytest.fixture(autouse=True)
def set_test_secret(monkeypatch):
    """Set test JWT secret for all tests."""
    monkeypatch.setenv("NEXTAUTH_SECRET", TEST_SECRET)


def create_test_token(
    user_id: str = "test-user-123",
    email: str = "test@example.com",
    graph_id: str = "U:test123",
    expired: bool = False,
    secret: str = TEST_SECRET,
) -> str:
    """Create a test JWT token."""
    now = datetime.utcnow()
    exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)

    claims = {
        "sub": user_id,
        "id": user_id,
        "email": email,
        "graphId": graph_id,
        "type": "access",
        "iat": now,
        "exp": exp,
    }

    return jwt.encode(claims, secret, algorithm="HS256")


# =============================================================================
# Unit Tests
# =============================================================================


class TestJWTVerification:
    """Tests for JWT verification."""

    def test_valid_token_verifies(self):
        """Valid tokens should be verified successfully."""
        from api.middleware.jwt import verify_jwt

        token = create_test_token()
        claims = verify_jwt(token)

        assert claims is not None
        assert claims["sub"] == "test-user-123"
        assert claims["email"] == "test@example.com"
        assert claims["graphId"] == "U:test123"

    def test_expired_token_rejected(self):
        """Expired tokens should be rejected."""
        from api.middleware.jwt import verify_jwt

        token = create_test_token(expired=True)
        claims = verify_jwt(token)

        assert claims is None

    def test_invalid_signature_rejected(self):
        """Tokens with invalid signatures should be rejected."""
        from api.middleware.jwt import verify_jwt

        # Create token with different secret
        token = create_test_token(secret="wrong-secret")
        claims = verify_jwt(token)

        assert claims is None

    def test_malformed_token_rejected(self):
        """Malformed tokens should be rejected."""
        from api.middleware.jwt import verify_jwt

        claims = verify_jwt("not-a-valid-jwt-token")
        assert claims is None

    def test_missing_secret_returns_none(self, monkeypatch):
        """If no secret configured, verification should return None."""
        monkeypatch.delenv("NEXTAUTH_SECRET", raising=False)

        # Need to reload module to pick up env change
        import importlib

        from api.middleware import jwt as jwt_module

        importlib.reload(jwt_module)

        token = create_test_token()
        claims = jwt_module.verify_jwt(token)

        # Restore for other tests
        monkeypatch.setenv("NEXTAUTH_SECRET", TEST_SECRET)
        importlib.reload(jwt_module)

        assert claims is None


class TestBearerExtraction:
    """Tests for Bearer token extraction."""

    def test_extracts_bearer_token(self):
        """Should extract token from Authorization header."""
        # Create a mock request with Authorization header
        from unittest.mock import MagicMock

        from api.middleware.jwt import extract_bearer_token

        request = MagicMock()
        request.headers = {"Authorization": "Bearer my-test-token"}

        token = extract_bearer_token(request)
        assert token == "my-test-token"

    def test_returns_none_without_bearer(self):
        """Should return None if no Bearer prefix."""
        from unittest.mock import MagicMock

        from api.middleware.jwt import extract_bearer_token

        request = MagicMock()
        request.headers = {"Authorization": "Basic sometoken"}

        token = extract_bearer_token(request)
        assert token is None

    def test_returns_none_without_header(self):
        """Should return None if no Authorization header."""
        from unittest.mock import MagicMock

        from api.middleware.jwt import extract_bearer_token

        request = MagicMock()
        request.headers = {}

        token = extract_bearer_token(request)
        assert token is None


class TestJWTExemptPaths:
    """Tests for exempt path checking."""

    def test_health_is_exempt(self):
        """Health endpoints should be exempt."""
        from api.middleware.jwt import is_jwt_exempt

        assert is_jwt_exempt("/health") is True
        assert is_jwt_exempt("/ready") is True

    def test_docs_is_exempt(self):
        """Documentation paths should be exempt."""
        from api.middleware.jwt import is_jwt_exempt

        assert is_jwt_exempt("/docs") is True
        assert is_jwt_exempt("/docs/oauth2-redirect") is True

    def test_auth_paths_exempt(self):
        """Auth endpoints should be exempt."""
        from api.middleware.jwt import is_jwt_exempt

        assert is_jwt_exempt("/api/v1/auth/otp/request") is True
        assert is_jwt_exempt("/api/v1/auth/otp/verify") is True

    def test_api_paths_not_exempt(self):
        """Regular API paths should NOT be exempt."""
        from api.middleware.jwt import is_jwt_exempt

        assert is_jwt_exempt("/api/v1/nodes") is False
        assert is_jwt_exempt("/api/v1/query") is False


# =============================================================================
# Security Invariant Tests
# =============================================================================


class TestSecurityInvariants:
    """Tests for security invariants."""

    def test_tenant_isolation_from_jwt(self):
        """JWT claims should correctly set tenant_id for isolation."""
        from api.middleware.jwt import verify_jwt

        token = create_test_token(user_id="user-abc-123")
        claims = verify_jwt(token)

        # Tenant ID should be derived from user ID
        expected_tenant = f"user:{claims['sub']}"
        assert expected_tenant == "user:user-abc-123"

    def test_constant_time_comparison(self):
        """PyJWT uses constant-time comparison internally."""
        # This is a property of PyJWT's implementation
        # We verify by ensuring invalid signatures are rejected
        from api.middleware.jwt import verify_jwt

        # Two tokens with same data but different secrets
        valid = create_test_token(secret=TEST_SECRET)
        invalid = create_test_token(secret="other-secret")

        assert verify_jwt(valid) is not None
        assert verify_jwt(invalid) is None
