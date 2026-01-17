"""
FAIM-Native Auth Models.

Stage-11: Security Hardening - Hashed API Key Storage.

This module defines the database models for secure API key storage.
Keys are stored as Argon2id hashes, never plaintext.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID

from store.pg.models_faim import Base


class TenantApiKey(Base):
    """
    Secure API key storage for tenants.
    
    Keys are stored as Argon2id hashes. The key_prefix allows
    UI display without exposing the full key.
    
    Attributes:
        id: Unique identifier for this key record.
        tenant_id: The tenant this key belongs to.
        key_id: Short identifier for revocation (e.g., "faim_abc123").
        key_prefix: First 6 chars for UI display only.
        key_hash: Argon2id hash of the full key.
        created_at: When the key was created.
        revoked_at: When the key was revoked (None if active).
    """
    __tablename__ = "tenant_api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(Text, nullable=False, index=True)
    key_id = Column(Text, nullable=False)
    key_prefix = Column(String(20), nullable=False)  # e.g., "faim_abc123"
    key_hash = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index("ix_tenant_api_keys_tenant_key", "tenant_id", "key_id", unique=True),
        Index("ix_tenant_api_keys_active", "tenant_id", "revoked_at"),
    )
    
    def is_active(self) -> bool:
        """Check if this key is still active (not revoked)."""
        return self.revoked_at is None
    
    def revoke(self) -> None:
        """Mark this key as revoked."""
        self.revoked_at = datetime.utcnow()
    
    def to_dict(self, include_hash: bool = False) -> dict:
        """
        Convert to dictionary for API responses.
        
        Args:
            include_hash: If True, include the hash (for internal use only).
            
        Returns:
            Dictionary representation.
        """
        result = {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "key_id": self.key_id,
            "key_prefix": self.key_prefix,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "is_active": self.is_active(),
        }
        if include_hash:
            result["key_hash"] = self.key_hash
        return result


class AdminApiKey(Base):
    """
    Secure API key storage for admin users.
    
    Same structure as TenantApiKey but for admin endpoints.
    """
    __tablename__ = "admin_api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    admin_id = Column(Text, nullable=False, index=True)
    key_id = Column(Text, nullable=False)
    key_prefix = Column(String(20), nullable=False)
    key_hash = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index("ix_admin_api_keys_admin_key", "admin_id", "key_id", unique=True),
    )
    
    def is_active(self) -> bool:
        """Check if this key is still active (not revoked)."""
        return self.revoked_at is None
    
    def revoke(self) -> None:
        """Mark this key as revoked."""
        self.revoked_at = datetime.utcnow()
