"""
FAIM-Native Auth Models.

Stage-11: Security Hardening - Hashed API Key Storage.
Phase K2: Scope/expiry lifecycle metadata + key audit trail.

This module defines database models for secure API key storage.
Keys are stored as Argon2id hashes, never plaintext.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Index, String, Text

from store.pg.models_faim import Base, JSONBType, UUIDType


class TenantApiKey(Base):
    """
    Secure API key storage for tenants.

    Keys are stored as Argon2id hashes. The key_prefix allows
    UI display without exposing the full key.

    Phase K2 adds per-key scope and lifecycle metadata.
    """

    __tablename__ = "tenant_api_keys"

    id = Column(UUIDType, primary_key=True, default=uuid4)
    tenant_id = Column(Text, nullable=False, index=True)
    key_id = Column(Text, nullable=False)
    key_prefix = Column(String(20), nullable=False)  # e.g., "faim_abc123"
    key_hash = Column(Text, nullable=False)

    scopes = Column(JSONBType, nullable=False, default=list)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_by = Column(Text, nullable=True)

    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(Text, nullable=True)

    rotated_from_key_id = Column(Text, nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_tenant_api_keys_tenant_key", "tenant_id", "key_id", unique=True),
        Index("ix_tenant_api_keys_active", "tenant_id", "revoked_at"),
        Index("ix_tenant_api_keys_expires_at", "expires_at"),
    )

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        """Check if key is expired."""
        if self.expires_at is None:
            return False
        now = now or datetime.now(timezone.utc)
        return bool(now >= self.expires_at)

    def is_active(self) -> bool:
        """Check if key is active (not revoked and not expired)."""
        return self.revoked_at is None and not self.is_expired()

    def revoke(self, reason: Optional[str] = None) -> None:
        """Mark this key as revoked."""
        self.revoked_at = datetime.now(timezone.utc)
        self.revoked_reason = (reason or "").strip() or None

    def touch_last_used(self) -> None:
        """Update key usage timestamp for audit/ops signals."""
        self.last_used_at = datetime.now(timezone.utc)

    def to_dict(self, include_hash: bool = False) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        result: dict[str, Any] = {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "key_id": self.key_id,
            "key_prefix": self.key_prefix,
            "scopes": list(self.scopes or []),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revoked_reason": self.revoked_reason,
            "rotated_from_key_id": self.rotated_from_key_id,
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
            "is_active": self.is_active(),
        }
        if include_hash:
            result["key_hash"] = self.key_hash
        return result


class AuthKeyAuditLog(Base):
    """Append-only key lifecycle audit entries."""

    __tablename__ = "auth_key_audit_log"

    id = Column(UUIDType, primary_key=True, default=uuid4)
    tenant_id = Column(Text, nullable=False, index=True)
    key_id = Column(Text, nullable=False, index=True)
    action = Column(Text, nullable=False, index=True)
    actor = Column(Text, nullable=True)
    request_id = Column(Text, nullable=True)
    meta = Column(JSONBType, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_auth_key_audit_tenant_key_time", "tenant_id", "key_id", "created_at"),
        Index("ix_auth_key_audit_action_time", "action", "created_at"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert audit row to API-safe dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "key_id": self.key_id,
            "action": self.action,
            "actor": self.actor,
            "request_id": self.request_id,
            "meta": self.meta or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AdminApiKey(Base):
    """
    Secure API key storage for admin users.

    Same structure as TenantApiKey but for admin endpoints.
    """

    __tablename__ = "admin_api_keys"

    id = Column(UUIDType, primary_key=True, default=uuid4)
    admin_id = Column(Text, nullable=False, index=True)
    key_id = Column(Text, nullable=False)
    key_prefix = Column(String(20), nullable=False)
    key_hash = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_admin_api_keys_admin_key", "admin_id", "key_id", unique=True),
    )

    def is_active(self) -> bool:
        """Check if this key is still active (not revoked)."""
        return self.revoked_at is None

    def revoke(self) -> None:
        """Mark this key as revoked."""
        self.revoked_at = datetime.now(timezone.utc)


class UserModel(Base):
    """
    Formal user registry for identity management.

    Attributes:
        id: Unique identifier (UUID5 deterministic).
        email: Verified email address.
        full_name: Display name.
        created_at: When the user first signed up.
        updated_at: Last profile update.
    """

    __tablename__ = "users"

    id = Column(UUIDType, primary_key=True)
    email = Column(Text, nullable=False, unique=True, index=True)
    full_name = Column(Text, nullable=True)
    totp_enabled = Column(Boolean, nullable=False, default=False)
    totp_secret_encrypted = Column(Text, nullable=True)
    totp_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    recovery_code_hashes = Column(JSONBType, nullable=False, default=list)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "email": self.email,
            "name": self.full_name,
            "totp_enabled": bool(self.totp_enabled),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
