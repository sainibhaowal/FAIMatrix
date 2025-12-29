"""
FAIM Keycloak JWT Authentication

Verifies OIDC tokens issued by Keycloak.
- Fetches JWKS from Keycloak's well-known endpoint
- Caches keys with TTL
- Provides FastAPI dependencies for auth
"""
import os
import time
import logging
from typing import Optional, Dict, Any
from functools import lru_cache

import httpx
from jose import jwt, JWTError, jwk
from jose.exceptions import JWKError
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# Configuration from environment
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "faim")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "faim-api")
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "faim-api")

# Derived URLs
KEYCLOAK_ISSUER = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
KEYCLOAK_JWKS_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"
KEYCLOAK_OPENID_CONFIG = f"{KEYCLOAK_ISSUER}/.well-known/openid-configuration"

# JWKS cache
_jwks_cache: Dict[str, Any] = {}
_jwks_cache_time: float = 0
JWKS_CACHE_TTL = 300  # 5 minutes

# Bearer token extractor
bearer_scheme = HTTPBearer(auto_error=False)


def get_jwks() -> Dict[str, Any]:
    """Fetch JWKS from Keycloak with caching."""
    global _jwks_cache, _jwks_cache_time
    
    now = time.time()
    if _jwks_cache and (now - _jwks_cache_time) < JWKS_CACHE_TTL:
        return _jwks_cache
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(KEYCLOAK_JWKS_URL)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_cache_time = now
            logger.info(f"Refreshed JWKS from {KEYCLOAK_JWKS_URL}")
            return _jwks_cache
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        # Return cached keys if available (stale is better than nothing)
        if _jwks_cache:
            logger.warning("Using stale JWKS cache")
            return _jwks_cache
        raise HTTPException(status_code=503, detail="Authentication service unavailable")


def get_signing_key(kid: str) -> Optional[Dict[str, Any]]:
    """Get the signing key for a specific key ID."""
    jwks = get_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


def verify_jwt(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException on invalid token
    """
    try:
        # Decode header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise HTTPException(status_code=401, detail="Invalid token: missing key ID")
        
        # Get the signing key
        signing_key = get_signing_key(kid)
        if not signing_key:
            # Refresh cache and retry
            global _jwks_cache_time
            _jwks_cache_time = 0
            signing_key = get_signing_key(kid)
            
        if not signing_key:
            raise HTTPException(status_code=401, detail="Invalid token: unknown signing key")
        
        # Verify and decode
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=KEYCLOAK_AUDIENCE,
            issuer=KEYCLOAK_ISSUER,
            options={
                "verify_aud": bool(KEYCLOAK_AUDIENCE),
                "verify_iss": True,
                "verify_exp": True,
            }
        )
        
        return payload
        
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except JWKError as e:
        logger.warning(f"JWK error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token signature")


async def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency that extracts and verifies JWT if present.
    Returns None if no token provided (for optional auth endpoints).
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    if not token:
        return None
    
    payload = verify_jwt(token)
    
    # Store in request state for downstream use
    request.state.jwt_payload = payload
    request.state.user_sub = payload.get("sub")  # Keycloak subject ID
    request.state.user_email = payload.get("email")
    request.state.user_name = payload.get("name") or payload.get("preferred_username")
    
    return payload


async def get_current_user(
    request: Request,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    """
    FastAPI dependency that requires a valid JWT.
    Raises 401 if no token or invalid token.
    """
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_user_sub(
    user: Dict[str, Any] = Depends(get_current_user),
) -> str:
    """Get the Keycloak subject ID (user identifier)."""
    sub = user.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token: missing subject")
    return sub


def is_keycloak_enabled() -> bool:
    """Check if Keycloak authentication is configured."""
    url = os.getenv("KEYCLOAK_URL", "").strip()
    return bool(url) and url != "http://localhost:8080"


# Utility for getting user from request state (after middleware runs)
def get_user_from_request(request: Request) -> Optional[str]:
    """Get user_sub from request state (set by middleware or dependency)."""
    return getattr(request.state, "user_sub", None)
