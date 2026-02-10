"""FAIM-Native API: JWT Auth Middleware (Stage-12).

Verifies JWT tokens issued by the frontend NextAuth system.

Security Features:
- HS256 signature verification with NEXTAUTH_SECRET
- Token expiration checking
- Constant-time signature comparison (via PyJWT)
- Seamless fallback to API key auth if no Bearer token

Flow:
1. Check for Authorization: Bearer <token> header
2. If present, verify JWT signature and expiry
3. Extract user_id and graph_id from claims
4. Set tenant_id = "user:<user_id>" for isolation
5. If no Bearer token, fall through to API key middleware
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


def _get_jwt_secret() -> Optional[str]:
    """Get JWT secret from environment."""
    s = os.getenv("NEXTAUTH_SECRET")
    if s:
        logger.info(f"Loaded NEXTAUTH_SECRET (len: {len(s)})")
    return s


# =============================================================================
# JWT Verification
# =============================================================================


def verify_jwt(token: str) -> Optional[dict]:
    """
    Verify a JWT token and return claims if valid.

    Returns None if:
    - Token is malformed
    - Signature is invalid
    - Token is expired
    """
    secret = _get_jwt_secret()
    if not secret:
        logger.warning("NEXTAUTH_SECRET not configured, JWT auth disabled")
        return None

    try:
        import jwt

        # Verify signature and decode
        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={
                "require": ["sub", "exp"],
                "verify_signature": True,
                "verify_exp": True,
            },
        )

        return claims

    except jwt.ExpiredSignatureError:
        logger.warning(f"[JWT] Token EXPIRED. Secret len: {len(secret) if secret else 0}")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"[JWT] Invalid Token: {e}. Secret len: {len(secret) if secret else 0}. Token preview: {token[:10]}...{token[-10:]}")
        return None
    except Exception as e:
        logger.error(f"[JWT] Unexpected error during verification: {type(e).__name__}: {e}")
        return None
    except ImportError:
        logger.error("PyJWT not installed, JWT auth disabled")
        return None


def extract_bearer_token(request: Request) -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return None

    return auth_header[7:]  # Remove "Bearer " prefix


# =============================================================================
# JWT Auth Middleware
# =============================================================================

# Paths exempt from JWT auth (same as tenant auth)
JWT_EXEMPT_PATHS = {
    "/health",
    "/ready",
    "/version",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/health",
    "/api/v1/ready",
    "/api/v1/auth/otp/request",
    "/api/v1/auth/otp/verify",
    "/v1/auth/otp/request",
    "/v1/auth/otp/verify",
}

JWT_EXEMPT_PREFIXES = []


def is_jwt_exempt(path: str) -> bool:
    """Check if path is exempt from JWT auth."""
    if path in JWT_EXEMPT_PATHS or path.startswith("/docs"):
        return True
    for prefix in JWT_EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for JWT-based authentication.

    Verifies Bearer tokens from NextAuth frontend.
    Falls back to API key auth if no Bearer token present.

    Stage-12: Production-hardened JWT verification.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip for exempt paths
        if is_jwt_exempt(request.url.path):
            return await call_next(request)

        # Check for Bearer token
        token = extract_bearer_token(request)

        if not token:
            # No Bearer token, fall through to API key auth
            return await call_next(request)

        # Verify JWT
        claims = verify_jwt(token)

        if not claims:
            # Invalid token - reject immediately
            logger.warning(f"[JWT] Rejecting request to {request.url.path} (Invalid/Expired token)")
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid or expired token"},
            )

        # Extract user info from claims
        email = claims.get("email")
        user_id = claims.get("userId") or claims.get("sub") or claims.get("id")
        graph_id = claims.get("graphId")

        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"error": "Token missing user identifier"},
            )

        # Set tenant_id for isolation (prefix with "user:" to distinguish from API tenants)
        # This ensures complete isolation between users
        tenant_id = f"user:{user_id}"

        # Attach to request state
        request.state.tenant_id = tenant_id
        request.state.user_id = user_id
        request.state.email = email
        request.state.graph_id = graph_id
        request.state.auth_method = "jwt"
        
        # Consistent user object for routers
        request.state.user = {
            "id": user_id,
            "email": email,
            "name": claims.get("name") or email.split("@")[0] if email else "User",
            "graph_id": graph_id,
        }

        logger.info(f"JWT auth successful: email={email}, derived_id={user_id}, graph_id={graph_id}")

        return await call_next(request)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "JWTAuthMiddleware",
    "verify_jwt",
    "extract_bearer_token",
]
