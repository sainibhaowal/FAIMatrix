"""FAIM-Native API: Auth Middleware (K3 hardened).

Tenant authentication with:
- DB-backed API key validation as primary path
- Env-key fallback behind explicit compatibility flag
- Constant-time compare for env fallback path
- Strict tenant validation (reject empty/missing)

Required headers:
- X-Tenant-Id: <uuid-or-string>
- X-Api-Key: <key>

Config:
- TENANT_KEYS_JSON='{"tenantA":["keyA1","keyA2"],"tenantB":["keyB"]}'
- FAIM_AUTH_DB_PRIMARY=true|false
- FAIM_AUTH_ENV_FALLBACK_ENABLED=true|false
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


# =============================================================================
# Tenant Key Store (legacy env fallback, with rotation support)
# =============================================================================


def _parse_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _load_tenant_keys() -> Dict[str, List[str]]:
    """Load tenant keys from environment.

    Supports key rotation: each tenant can have multiple valid keys.
    Format: TENANT_KEYS_JSON='{"tenantA":["key1","key2"],"tenantB":["keyB"]}'
    Legacy format also supported: '{"tenantA":"keyA"}' (single key as string)
    """
    raw = os.getenv("TENANT_KEYS_JSON", "{}")
    try:
        data = json.loads(raw)
        # Normalize: convert string values to lists
        result: Dict[str, List[str]] = {}
        for tenant, keys in data.items():
            if isinstance(keys, str):
                result[tenant] = [keys]
            elif isinstance(keys, list):
                result[tenant] = [str(k) for k in keys if str(k)]
            else:
                logger.warning("Invalid key format for tenant %s", tenant)
                result[tenant] = []
        return result
    except json.JSONDecodeError:
        logger.error("Invalid TENANT_KEYS_JSON format")
        return {}


# Cache tenant keys at module load
_TENANT_KEYS: Dict[str, List[str]] = {}


def get_tenant_keys() -> Dict[str, List[str]]:
    """Get cached tenant keys."""
    global _TENANT_KEYS
    if not _TENANT_KEYS:
        _TENANT_KEYS = _load_tenant_keys()
    return _TENANT_KEYS


def reload_tenant_keys() -> None:
    """Force reload tenant keys (for key rotation)."""
    global _TENANT_KEYS
    _TENANT_KEYS = _load_tenant_keys()


def _constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(a.encode(), b.encode())


@dataclass(frozen=True)
class AuthDecision:
    """Auth result envelope for middleware context propagation."""

    valid: bool
    auth_method: Optional[str] = None
    key_id: Optional[str] = None
    scopes: List[str] = field(default_factory=list)
    reason: Optional[str] = None


def _verify_env_tenant_key(tenant_id: str, api_key: str) -> bool:
    """Legacy env-key verification path (explicit compatibility mode only)."""
    keys = get_tenant_keys()
    valid_keys = keys.get(tenant_id, [])
    for valid_key in valid_keys:
        if _constant_time_compare(api_key, valid_key):
            return True
    return False


def _verify_db_tenant_key(tenant_id: str, api_key: str):
    """DB-backed key verification returning TenantApiKey or None."""
    from store.pg.repos.auth_repo import AuthRepo
    from store.pg.session import get_session

    session = get_session()
    try:
        repo = AuthRepo(session)
        record = repo.verify_tenant_key(tenant_id, api_key)
        if record:
            try:
                repo.append_key_audit(
                    tenant_id=tenant_id,
                    key_id=record.key_id,
                    action="verified",
                    meta={"method": "db_primary"},
                )
            except Exception:  # nosec B110
                pass
            session.commit()
            return record
        session.rollback()
        return None
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def authenticate_tenant_key(tenant_id: str, api_key: str) -> AuthDecision:
    """Authenticate tenant API key and return decision/context data.

    K3 ordering policy:
    - Default: DB primary
    - Env fallback: optional behind explicit flag
    """
    db_primary = _parse_bool("FAIM_AUTH_DB_PRIMARY", True)
    env_fallback = _parse_bool("FAIM_AUTH_ENV_FALLBACK_ENABLED", False)

    # DB-primary path
    if db_primary:
        try:
            record = _verify_db_tenant_key(tenant_id, api_key)
            if record:
                return AuthDecision(
                    valid=True,
                    auth_method="api_key_db",
                    key_id=str(record.key_id),
                    scopes=list(record.scopes or []),
                )
        except Exception as exc:
            logger.warning("DB key verification failed for tenant=%s: %s", tenant_id, exc)

        if env_fallback and _verify_env_tenant_key(tenant_id, api_key):
            return AuthDecision(
                valid=True,
                auth_method="api_key_env",
                key_id=None,
                scopes=[],
            )

        return AuthDecision(valid=False, reason="invalid_credentials")

    # Legacy compatibility ordering (explicitly opted-in)
    if _verify_env_tenant_key(tenant_id, api_key):
        return AuthDecision(
            valid=True,
            auth_method="api_key_env",
            key_id=None,
            scopes=[],
        )

    try:
        record = _verify_db_tenant_key(tenant_id, api_key)
        if record:
            return AuthDecision(
                valid=True,
                auth_method="api_key_db",
                key_id=str(record.key_id),
                scopes=list(record.scopes or []),
            )
    except Exception as exc:
        logger.warning("DB key verification failed for tenant=%s: %s", tenant_id, exc)

    return AuthDecision(valid=False, reason="invalid_credentials")


def validate_tenant_key(tenant_id: str, api_key: str) -> bool:
    """Legacy-compatible bool validator wrapper."""
    return authenticate_tenant_key(tenant_id, api_key).valid


# =============================================================================
# Tenant ID Validation
# =============================================================================

# Valid tenant pattern: alphanumeric, hyphens, underscores
TENANT_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def normalize_tenant_id(tenant_id: str) -> str:
    """Normalize and validate tenant ID.

    Returns normalized tenant ID or empty string if invalid.
    """
    if not tenant_id:
        return ""

    # Trim whitespace
    normalized = tenant_id.strip()

    # Validate pattern
    if not TENANT_PATTERN.match(normalized):
        return ""

    return normalized


def is_valid_tenant_id(tenant_id: str) -> bool:
    """Check if tenant ID is valid (non-empty, matches pattern)."""
    if not tenant_id:
        return False
    return bool(TENANT_PATTERN.match(tenant_id.strip()))


# =============================================================================
# Exempt Paths
# =============================================================================

EXEMPT_PATHS = {
    "/health",
    "/ready",
    "/version",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/health",
    "/api/v1/ready",
}

# Auth paths that should be exempt from tenant auth
AUTH_PATH_PREFIXES = [
    "/api/v1/auth",
    "/v1/auth",
]


def is_exempt_path(path: str) -> bool:
    """Check if path is exempt from auth."""
    if path in EXEMPT_PATHS or path.startswith("/docs"):
        return True
    # Exempt auth endpoints
    for prefix in AUTH_PATH_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


# =============================================================================
# Auth Middleware
# =============================================================================


class TenantAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for tenant authentication.

    Validates X-Tenant-Id and X-Api-Key headers.
    Attaches tenant_id + auth context to request.state.

    K3 hardening:
    - DB-primary auth decision with explicit env fallback control
    - Context propagation: auth_method, auth_key_id, auth_scopes
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth for exempt paths
        if is_exempt_path(request.url.path):
            return await call_next(request)

        # Stage-12: JWT Bypass
        # If the request has already been authenticated by JWTAuthMiddleware,
        # skip the requirement for X-Tenant-Id and X-Api-Key.
        if getattr(request.state, "auth_method", None) == "jwt":
            return await call_next(request)

        # Get headers
        raw_tenant_id = request.headers.get("X-Tenant-Id", "")
        api_key = request.headers.get("X-Api-Key", "")

        # Normalize and validate tenant ID
        tenant_id = normalize_tenant_id(raw_tenant_id)

        # Reject empty/missing tenant
        if not tenant_id:
            return JSONResponse(
                status_code=401,
                content={"error": "Missing or invalid X-Tenant-Id header"},
            )

        # Check API key present
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"error": "Missing X-Api-Key header"},
            )

        # Authenticate key
        decision = authenticate_tenant_key(tenant_id, api_key)
        if not decision.valid:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid tenant credentials"},
            )

        # Attach auth context to request state
        request.state.tenant_id = tenant_id
        request.state.auth_method = decision.auth_method or "api_key"
        request.state.auth_key_id = decision.key_id
        request.state.auth_scopes = list(decision.scopes or [])

        # Continue processing
        response = await call_next(request)
        return response


# =============================================================================
# Admin Auth Check
# =============================================================================


def validate_admin_key(admin_key: str) -> bool:
    """Validate admin API key using constant-time comparison.

    Admin key is stored in FAIM_ADMIN_KEY env var.
    """
    expected = os.getenv("FAIM_ADMIN_KEY")
    if not expected:
        logger.warning("No admin key configured, admin endpoints disabled")
        return False
    return _constant_time_compare(admin_key, expected)


def get_admin_key_header(request: Request) -> Optional[str]:
    """Get X-Admin-Key header."""
    return request.headers.get("X-Admin-Key")
