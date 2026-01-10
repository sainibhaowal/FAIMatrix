# =============================================================================
# FAIM API Key Management - Database-Backed
# =============================================================================
# File: faim/api/auth/keys.py
#
# Endpoints:
#     POST /api/v1/keys       - Generate new API key
#     GET  /api/v1/keys       - List user's API keys
#     DELETE /api/v1/keys/{id} - Revoke an API key
#
# Security:
#     - Keys hashed with Argon2 (industry standard)
#     - Original key shown ONCE on creation (never stored)
#     - Only hash stored in PostgreSQL
#     - User can only see their own keys
# =============================================================================

from __future__ import annotations

import logging
import secrets
from datetime import datetime
from typing import List, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from faim.api.auth.jwt_auth import get_current_user
from faim.config.database import get_db
from faim.config.models import APIKey, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api_keys", tags=["API Keys"])

# Argon2 hasher for API key hashing
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


# =============================================================================
# Schemas
# =============================================================================


class CreateKeyRequest(BaseModel):
    """Request to create a new API key."""

    name: Optional[str] = None
    scopes: List[str] = ["read", "write"]


class CreateKeyResponse(BaseModel):
    """Response containing the new API key (shown once)."""

    id: str
    name: Optional[str]
    key: str  # Full key - shown only once!
    key_prefix: str
    scopes: List[str]
    created_at: datetime
    message: str = "Save this key! It won't be shown again."


class KeyInfo(BaseModel):
    """API key information (without the actual key)."""

    id: str
    name: Optional[str]
    key_prefix: str
    scopes: List[str]
    created_at: datetime
    last_used_at: Optional[datetime]
    status: str


class KeyListResponse(BaseModel):
    """Response containing list of user's API keys."""

    keys: List[KeyInfo]
    total: int


class RevokeKeyResponse(BaseModel):
    """Response after revoking a key."""

    success: bool
    message: str


# =============================================================================
# Helper Functions
# =============================================================================


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (full_key, prefix)

    Format: sk_live_<48 random hex chars>
    """
    random_part = secrets.token_hex(24)  # 48 hex chars
    full_key = f"sk_live_{random_part}"
    prefix = full_key[:12]  # "sk_live_xxxx"
    return full_key, prefix


def hash_api_key(key: str) -> str:
    """Hash an API key using Argon2."""
    return ph.hash(key)


def verify_api_key(key: str, key_hash: str) -> bool:
    """Verify an API key against its hash."""
    try:
        ph.verify(key_hash, key)
        return True
    except VerifyMismatchError:
        return False


def get_user_from_token(db: Session, token_payload: dict) -> User:
    """Get User object from token payload."""
    user_id = token_payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("", response_model=CreateKeyResponse)
async def create_api_key(
    request: CreateKeyRequest,
    db: Session = Depends(get_db),
    token_payload: dict = Depends(get_current_user),
):
    """
    Create a new API key for the authenticated user.

    The full key is returned ONLY ONCE in this response.
    Store it securely - it cannot be recovered!
    """
    user = get_user_from_token(db, token_payload)

    # Generate key
    full_key, prefix = generate_api_key()
    key_hash = hash_api_key(full_key)

    # Create database record
    api_key = APIKey(
        user_id=user.id,
        name=request.name,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=request.scopes,
        status="active",
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    logger.info(f"API key created for user {user.id}: {prefix}...")

    return CreateKeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        key=full_key,  # Only time the full key is revealed
        key_prefix=prefix,
        scopes=api_key.scopes or [],
        created_at=api_key.created_at,
    )


@router.get("", response_model=KeyListResponse)
async def list_api_keys(
    db: Session = Depends(get_db),
    token_payload: dict = Depends(get_current_user),
):
    """
    List all API keys for the authenticated user.

    Note: Only metadata is returned, not the actual keys.
    """
    user = get_user_from_token(db, token_payload)

    keys = db.query(APIKey).filter(APIKey.user_id == user.id).order_by(APIKey.created_at.desc()).all()

    return KeyListResponse(
        keys=[
            KeyInfo(
                id=str(k.id),
                name=k.name,
                key_prefix=k.key_prefix,
                scopes=k.scopes or [],
                created_at=k.created_at,
                last_used_at=k.last_used_at,
                status=k.status,
            )
            for k in keys
        ],
        total=len(keys),
    )


@router.delete("/{key_id}", response_model=RevokeKeyResponse)
async def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    token_payload: dict = Depends(get_current_user),
):
    """
    Revoke an API key.

    The key will no longer work for authentication.
    This cannot be undone.
    """
    user = get_user_from_token(db, token_payload)

    # Find the key
    api_key = (
        db.query(APIKey)
        .filter(APIKey.id == key_id)
        .filter(APIKey.user_id == user.id)  # Security: only owner can revoke
        .first()
    )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    if api_key.status == "revoked":
        return RevokeKeyResponse(
            success=True,
            message="Key was already revoked.",
        )

    # Revoke the key
    api_key.status = "revoked"
    db.commit()

    logger.info(f"API key revoked for user {user.id}: {api_key.key_prefix}...")

    return RevokeKeyResponse(
        success=True,
        message="API key has been revoked and can no longer be used.",
    )


# =============================================================================
# Verification Function (used by middleware)
# =============================================================================


def verify_key_from_db(db: Session, key: str) -> Optional[APIKey]:
    """
    Verify an API key and return the APIKey record if valid.

    Used by auth_middleware.py for API key authentication.
    """
    if not key or not key.startswith("sk_live_"):
        return None

    prefix = key[:12]

    # Find candidate keys with matching prefix
    candidates = db.query(APIKey).filter(APIKey.key_prefix == prefix).filter(APIKey.status == "active").all()

    for candidate in candidates:
        if verify_api_key(key, candidate.key_hash):
            # Update last_used_at
            candidate.last_used_at = datetime.utcnow()
            db.commit()
            return candidate

    return None
