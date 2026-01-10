# =============================================================================
# FAIM JWT Authentication - Custom Token Management
# =============================================================================
# File: faim/api/auth/jwt_auth.py
#
# Security Features:
# - JWT signed with HMAC-SHA256 using FAIM_JWT_SECRET
# - 1-hour access tokens
# - 7-day refresh tokens
# - Token validation with expiration checking
#
# NOTE: This replaces NextAuth dependency with custom implementation.
# =============================================================================

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from faim.config.models import RefreshToken, User

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

# JWT secret - MUST be set in production
FAIM_JWT_SECRET = os.getenv("FAIM_JWT_SECRET") or os.getenv("NEXTAUTH_SECRET")
JWT_ALGORITHM = "HS256"

# Token expiration
ACCESS_TOKEN_EXPIRE = timedelta(hours=1)
REFRESH_TOKEN_EXPIRE = timedelta(days=7)

# Bearer token extractor
bearer_scheme = HTTPBearer(auto_error=False)


# =============================================================================
# Token Creation
# =============================================================================


def create_access_token(user_id: str, email: str, graph_id: Optional[str] = None) -> str:
    """
    Create a signed JWT access token.

    Args:
        user_id: User's UUID
        email: User's email
        graph_id: User's primary graph ID (optional)

    Returns:
        Signed JWT string
    """
    if not FAIM_JWT_SECRET:
        raise RuntimeError("FAIM_JWT_SECRET not configured")

    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "email": email,
        "graph_id": graph_id,
        "type": "access",
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRE,
    }

    return jwt.encode(payload, FAIM_JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(db: Session, user_id: str) -> str:
    """
    Create a refresh token and store its hash in the database.

    Args:
        db: Database session
        user_id: User's UUID

    Returns:
        Plaintext refresh token (only returned once)
    """
    if not FAIM_JWT_SECRET:
        raise RuntimeError("FAIM_JWT_SECRET not configured")

    # Generate secure random token
    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    # Store in database
    expires_at = datetime.utcnow() + REFRESH_TOKEN_EXPIRE
    refresh_record = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(refresh_record)
    db.commit()

    logger.info(f"Created refresh token for user {user_id}")
    return token


# =============================================================================
# Token Verification
# =============================================================================


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT access token.

    Returns:
        Decoded token payload

    Raises:
        HTTPException on invalid token
    """
    if not FAIM_JWT_SECRET:
        logger.error("FAIM_JWT_SECRET is not set!")
        raise HTTPException(status_code=500, detail="Server misconfiguration: missing auth secret")

    try:
        payload = jwt.decode(
            token,
            FAIM_JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={
                "verify_exp": True,
                "verify_iat": True,
            },
        )

        # Verify token type
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        return payload

    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def verify_refresh_token(db: Session, token: str) -> Optional[User]:
    """
    Verify a refresh token and return the associated user.

    Args:
        db: Database session
        token: Plaintext refresh token

    Returns:
        User if valid, None otherwise
    """
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    # Find token record
    record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .filter(RefreshToken.revoked_at.is_(None))
        .first()
    )

    if not record:
        return None

    # Check expiration
    if datetime.utcnow() > record.expires_at:
        return None

    # Return associated user
    return record.user


def revoke_refresh_token(db: Session, token: str) -> bool:
    """
    Revoke a refresh token (logout).

    Returns:
        True if revoked, False if not found
    """
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    record = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if record:
        record.revoked_at = datetime.utcnow()
        db.commit()
        logger.info(f"Revoked refresh token for user {record.user_id}")
        return True

    return False


# =============================================================================
# FastAPI Dependencies
# =============================================================================


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

    payload = verify_access_token(token)

    # Store in request state for downstream use
    request.state.jwt_payload = payload
    request.state.user_sub = payload.get("sub")
    request.state.user_email = payload.get("email")
    request.state.graph_id = payload.get("graph_id")

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
    """Get the user identifier from token."""
    sub = user.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token: missing subject")
    return str(sub)


# =============================================================================
# Utility Functions
# =============================================================================


def get_user_from_request(request: Request) -> Optional[str]:
    """Get user_sub from request state (set by middleware or dependency)."""
    return getattr(request.state, "user_sub", None)


def is_token_configured() -> bool:
    """Check if JWT secret is configured."""
    return bool(FAIM_JWT_SECRET)
