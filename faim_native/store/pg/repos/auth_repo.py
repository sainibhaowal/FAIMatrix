"""
FAIM-Native Auth Repository.

Stage-11: Security Hardening - API Key Management.

This module provides CRUD operations for secure API key storage.
All keys are hashed with Argon2id before storage.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session

from store.pg.models_auth import TenantApiKey, AdminApiKey
from runtime.secrets import (
    generate_api_key,
    get_key_prefix,
    hash_api_key,
    verify_api_key,
    needs_rehash,
)


class AuthRepo:
    """
    Repository for managing API keys.
    
    All keys are stored as Argon2id hashes. The plaintext key
    is only returned once during creation.
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    # --- Tenant API Keys ---
    
    def create_tenant_key(
        self,
        tenant_id: str,
        prefix: str = "faim",
    ) -> Tuple[TenantApiKey, str]:
        """
        Create a new API key for a tenant.
        
        Args:
            tenant_id: The tenant identifier.
            prefix: Prefix for the key (default: "faim").
            
        Returns:
            Tuple of (key_record, plaintext_key).
            
            IMPORTANT: The plaintext_key is only returned ONCE.
            Store it securely or give it to the user immediately.
        """
        key_id, full_key = generate_api_key(prefix)
        key_hash = hash_api_key(full_key)
        key_prefix = get_key_prefix(full_key)
        
        record = TenantApiKey(
            tenant_id=tenant_id,
            key_id=key_id,
            key_prefix=key_prefix,
            key_hash=key_hash,
        )
        
        self.session.add(record)
        self.session.flush()
        
        return record, full_key
    
    def verify_tenant_key(
        self,
        tenant_id: str,
        key: str,
    ) -> Optional[TenantApiKey]:
        """
        Verify a tenant API key.
        
        Args:
            tenant_id: The tenant identifier.
            key: The plaintext API key from the request.
            
        Returns:
            The key record if valid, None if invalid or revoked.
        """
        # Get all active keys for this tenant
        records = (
            self.session.query(TenantApiKey)
            .filter(TenantApiKey.tenant_id == tenant_id)
            .filter(TenantApiKey.revoked_at.is_(None))
            .all()
        )
        
        for record in records:
            if verify_api_key(key, record.key_hash):
                # Check if rehash needed (params changed)
                if needs_rehash(record.key_hash):
                    record.key_hash = hash_api_key(key)
                    self.session.flush()
                return record
        
        return None
    
    def find_tenant_key_by_any_key(
        self,
        key: str,
    ) -> Optional[Tuple[str, TenantApiKey]]:
        """
        Find tenant by verifying key against all tenants.
        
        Used when tenant_id is not provided in the request.
        
        Args:
            key: The plaintext API key.
            
        Returns:
            Tuple of (tenant_id, key_record) if found, None otherwise.
            
        Warning:
            This is slower than verify_tenant_key() because it
            must check keys across all tenants.
        """
        # Get all active keys
        records = (
            self.session.query(TenantApiKey)
            .filter(TenantApiKey.revoked_at.is_(None))
            .all()
        )
        
        for record in records:
            if verify_api_key(key, record.key_hash):
                return record.tenant_id, record
        
        return None
    
    def list_tenant_keys(
        self,
        tenant_id: str,
        include_revoked: bool = False,
    ) -> List[TenantApiKey]:
        """
        List all API keys for a tenant.
        
        Args:
            tenant_id: The tenant identifier.
            include_revoked: If True, include revoked keys.
            
        Returns:
            List of key records (without hashes).
        """
        query = (
            self.session.query(TenantApiKey)
            .filter(TenantApiKey.tenant_id == tenant_id)
        )
        
        if not include_revoked:
            query = query.filter(TenantApiKey.revoked_at.is_(None))
        
        return query.order_by(TenantApiKey.created_at.desc()).all()
    
    def revoke_tenant_key(
        self,
        tenant_id: str,
        key_id: str,
    ) -> Optional[TenantApiKey]:
        """
        Revoke an API key.
        
        Args:
            tenant_id: The tenant identifier.
            key_id: The key identifier to revoke.
            
        Returns:
            The revoked key record, or None if not found.
        """
        record = (
            self.session.query(TenantApiKey)
            .filter(TenantApiKey.tenant_id == tenant_id)
            .filter(TenantApiKey.key_id == key_id)
            .first()
        )
        
        if record:
            record.revoke()
            self.session.flush()
        
        return record
    
    # --- Admin API Keys ---
    
    def create_admin_key(
        self,
        admin_id: str,
        prefix: str = "admin",
    ) -> Tuple[AdminApiKey, str]:
        """Create a new API key for an admin."""
        key_id, full_key = generate_api_key(prefix)
        key_hash = hash_api_key(full_key)
        key_prefix = get_key_prefix(full_key)
        
        record = AdminApiKey(
            admin_id=admin_id,
            key_id=key_id,
            key_prefix=key_prefix,
            key_hash=key_hash,
        )
        
        self.session.add(record)
        self.session.flush()
        
        return record, full_key
    
    def verify_admin_key(self, key: str) -> Optional[AdminApiKey]:
        """
        Verify an admin API key.
        
        Args:
            key: The plaintext admin API key.
            
        Returns:
            The key record if valid, None if invalid or revoked.
        """
        records = (
            self.session.query(AdminApiKey)
            .filter(AdminApiKey.revoked_at.is_(None))
            .all()
        )
        
        for record in records:
            if verify_api_key(key, record.key_hash):
                if needs_rehash(record.key_hash):
                    record.key_hash = hash_api_key(key)
                    self.session.flush()
                return record
        
        return None
    
    def revoke_admin_key(
        self,
        admin_id: str,
        key_id: str,
    ) -> Optional[AdminApiKey]:
        """Revoke an admin API key."""
        record = (
            self.session.query(AdminApiKey)
            .filter(AdminApiKey.admin_id == admin_id)
            .filter(AdminApiKey.key_id == key_id)
            .first()
        )
        
        if record:
            record.revoke()
            self.session.flush()
        
        return record
