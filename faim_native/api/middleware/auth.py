"""FAIM-Native API: Auth Middleware (Stage-7.1 Hardened).

Tenant authentication with:
- Constant-time API key comparison
- Key rotation support (list of keys per tenant)
- Strict tenant validation (reject empty/missing)

Required headers:
- X-Tenant-Id: <uuid-or-string>
- X-Api-Key: <key>

Config via env:
- TENANT_KEYS_JSON='{"tenantA":["keyA1","keyA2"],"tenantB":["keyB"]}'
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import re
from typing import Dict, List, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


# =============================================================================
# Tenant Key Store (with rotation support)
# =============================================================================


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
        result = {}
        for tenant, keys in data.items():
            if isinstance(keys, str):
                result[tenant] = [keys]
            elif isinstance(keys, list):
                result[tenant] = keys
            else:
                logger.warning(f"Invalid key format for tenant {tenant}")
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


def validate_tenant_key(tenant_id: str, api_key: str) -> bool:
    """Validate tenant API key.
    
    Stage-11: Supports BOTH legacy (env var) and new (DB hashed) modes.
    
    Verification order:
    1. Check legacy TENANT_KEYS_JSON (for backward compatibility)
    2. Check database hashed keys (preferred for production)
    
    Args:
        tenant_id: Tenant identifier.
        api_key: API key provided.
        
    Returns:
        True if valid, False otherwise.
    """
    # --- Legacy Mode (TENANT_KEYS_JSON env var) ---
    # Will be deprecated after migration to DB hashes
    keys = get_tenant_keys()
    
    # For development: if no keys configured AND no DB, allow all
    if not keys:
        # Try DB verification (Stage-11)
        try:
            from store.pg.session import get_session
            from store.pg.repos.auth_repo import AuthRepo
            
            session = get_session()
            try:
                repo = AuthRepo(session)
                result = repo.verify_tenant_key(tenant_id, api_key)
                if result:
                    return True
            finally:
                session.close()
        except Exception as e:
            # DB not available or no hashed keys yet
            logger.debug(f"Hashed key verification failed: {e}")
            pass
        
        # No keys configured anywhere
        logger.warning("No tenant keys configured, allowing all requests (dev mode)")
        return True
    
    # Check legacy plaintext keys first
    valid_keys = keys.get(tenant_id, [])
    for valid_key in valid_keys:
        if _constant_time_compare(api_key, valid_key):
            return True
    
    # Legacy key not found, try DB hashed keys
    try:
        from store.pg.session import get_session
        from store.pg.repos.auth_repo import AuthRepo
        
        session = get_session()
        try:
            repo = AuthRepo(session)
            result = repo.verify_tenant_key(tenant_id, api_key)
            if result:
                return True
        finally:
            session.close()
    except Exception as e:
        logger.debug(f"Hashed key verification failed: {e}")
        pass
    
    return False


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
}


def is_exempt_path(path: str) -> bool:
    """Check if path is exempt from auth."""
    return path in EXEMPT_PATHS or path.startswith("/docs")


# =============================================================================
# Auth Middleware
# =============================================================================


class TenantAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for tenant authentication.

    Validates X-Tenant-Id and X-Api-Key headers.
    Attaches tenant_id to request.state.

    Stage-7.1 hardening:
    - Rejects empty/missing tenant
    - Constant-time key comparison
    - Supports key rotation
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth for exempt paths
        if is_exempt_path(request.url.path):
            return await call_next(request)

        # Get headers
        raw_tenant_id = request.headers.get("X-Tenant-Id", "")
        api_key = request.headers.get("X-Api-Key", "")

        # Normalize and validate tenant ID
        tenant_id = normalize_tenant_id(raw_tenant_id)

        # Stage-7.1: Reject empty/missing tenant
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

        # Validate key (constant-time)
        if not validate_tenant_key(tenant_id, api_key):
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid tenant credentials"},
            )

        # Attach to request state
        request.state.tenant_id = tenant_id

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
