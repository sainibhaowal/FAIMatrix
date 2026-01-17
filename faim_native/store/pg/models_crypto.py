"""
FAIM-Native Crypto Models (Stage-11).

Database models for encryption key management.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, LargeBinary
from sqlalchemy.dialects.postgresql import UUID

from store.pg.models_faim import Base


class TenantCryptoKey(Base):
    """
    Per-tenant Data Encryption Key (DEK).
    
    The DEK is wrapped (encrypted) using the master key.
    This allows key rotation without re-encrypting all data.
    
    Attributes:
        tenant_id: The tenant this key belongs to.
        dek_wrapped: The DEK encrypted with the master key.
        created_at: When the key was created.
        rotated_at: When the key was last rotated.
    """
    __tablename__ = "tenant_crypto_keys"
    
    tenant_id = Column(String, primary_key=True)
    dek_wrapped = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    
    def to_dict(self) -> dict:
        """Convert to dictionary (without key data)."""
        return {
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "rotated_at": self.rotated_at.isoformat() if self.rotated_at else None,
        }
