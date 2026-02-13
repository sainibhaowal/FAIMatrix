"""
FAIM-Native Auth Repository.

Stage-11: Security Hardening - API Key Management.
Phase K2: Scope/expiry lifecycle support + key audit log.

This module provides CRUD operations for secure API key storage.
All keys are hashed with Argon2id before storage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from runtime.secrets import (
    generate_api_key,
    get_key_prefix,
    hash_api_key,
    needs_rehash,
    verify_api_key,
)
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from store.pg.models_auth import AdminApiKey, AuthKeyAuditLog, TenantApiKey


class AuthRepo:
    """
    Repository for managing API keys.

    All keys are stored as Argon2id hashes. The plaintext key
    is only returned once during creation.
    """

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _normalize_scopes(scopes: Optional[List[str]]) -> List[str]:
        """Normalize scope list while preserving stable order."""
        if not scopes:
            return []

        normalized: List[str] = []
        seen: set[str] = set()
        for scope in scopes:
            value = str(scope or "").strip()
            if not value or value in seen:
                continue
            normalized.append(value)
            seen.add(value)
        return normalized

    # --- Tenant API Key Audit ---

    def append_key_audit(
        self,
        tenant_id: str,
        key_id: str,
        action: str,
        *,
        actor: Optional[str] = None,
        request_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> AuthKeyAuditLog:
        """Append a key lifecycle audit record."""
        record = AuthKeyAuditLog(
            tenant_id=tenant_id,
            key_id=key_id,
            action=action,
            actor=(actor or "").strip() or None,
            request_id=(request_id or "").strip() or None,
            meta=meta or {},
        )
        self.session.add(record)
        self.session.flush()
        return record

    def list_key_audit(
        self,
        tenant_id: str,
        *,
        key_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuthKeyAuditLog]:
        """List key lifecycle audit entries for a tenant."""
        query = self.session.query(AuthKeyAuditLog).filter(
            AuthKeyAuditLog.tenant_id == tenant_id
        )

        if key_id:
            query = query.filter(AuthKeyAuditLog.key_id == key_id)
        if action:
            query = query.filter(AuthKeyAuditLog.action == action)

        safe_limit = max(1, min(int(limit), 500))
        return query.order_by(AuthKeyAuditLog.created_at.desc()).limit(safe_limit).all()

    # --- Tenant API Keys ---

    def create_tenant_key(
        self,
        tenant_id: str,
        prefix: str = "faim",
        *,
        scopes: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
        rotated_from_key_id: Optional[str] = None,
        audit_actor: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Tuple[TenantApiKey, str]:
        """
        Create a new API key for a tenant.

        Args:
            tenant_id: The tenant identifier.
            prefix: Prefix for the key (default: "faim").
            scopes: Optional list of auth scopes for this key.
            expires_at: Optional key expiration timestamp.
            created_by: Optional actor/user identifier.
            rotated_from_key_id: Optional lineage key id.
            audit_actor: Optional audit actor.
            request_id: Optional request correlation id.

        Returns:
            Tuple of (key_record, plaintext_key).

            IMPORTANT: The plaintext_key is only returned ONCE.
            Store it securely or give it to the user immediately.
        """
        key_id, full_key = generate_api_key(prefix)
        key_hash = hash_api_key(full_key)
        key_prefix = get_key_prefix(full_key)

        scope_list = self._normalize_scopes(scopes)

        record = TenantApiKey(
            tenant_id=tenant_id,
            key_id=key_id,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=scope_list,
            expires_at=expires_at,
            created_by=(created_by or "").strip() or None,
            rotated_from_key_id=(rotated_from_key_id or "").strip() or None,
        )

        self.session.add(record)
        self.session.flush()

        self.append_key_audit(
            tenant_id=tenant_id,
            key_id=key_id,
            action="created",
            actor=audit_actor,
            request_id=request_id,
            meta={
                "scopes": scope_list,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "rotated_from_key_id": rotated_from_key_id,
            },
        )

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
            The key record if valid, None if invalid/revoked/expired.
        """
        now = self._utcnow()

        records = (
            self.session.query(TenantApiKey)
            .filter(TenantApiKey.tenant_id == tenant_id)
            .filter(TenantApiKey.revoked_at.is_(None))
            .filter(
                or_(
                    TenantApiKey.expires_at.is_(None),
                    TenantApiKey.expires_at > now,
                )
            )
            .all()
        )

        for record in records:
            if verify_api_key(key, record.key_hash):
                # Rehash and usage tracking are non-breaking metadata upgrades.
                if needs_rehash(record.key_hash):
                    record.key_hash = hash_api_key(key)
                record.touch_last_used()
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
        """
        now = self._utcnow()

        records = (
            self.session.query(TenantApiKey)
            .filter(TenantApiKey.revoked_at.is_(None))
            .filter(
                or_(
                    TenantApiKey.expires_at.is_(None),
                    TenantApiKey.expires_at > now,
                )
            )
            .all()
        )

        for record in records:
            if verify_api_key(key, record.key_hash):
                record.touch_last_used()
                self.session.flush()
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
            List of key records (without plaintext).
        """
        query = self.session.query(TenantApiKey).filter(
            TenantApiKey.tenant_id == tenant_id
        )

        if not include_revoked:
            query = query.filter(TenantApiKey.revoked_at.is_(None))

        return query.order_by(TenantApiKey.created_at.desc()).all()

    def get_tenant_key(
        self,
        tenant_id: str,
        key_id: str,
    ) -> Optional[TenantApiKey]:
        """Get one tenant key by id (including revoked keys)."""
        return (
            self.session.query(TenantApiKey)
            .filter(
                and_(
                    TenantApiKey.tenant_id == tenant_id,
                    TenantApiKey.key_id == key_id,
                )
            )
            .first()
        )

    def revoke_tenant_key(
        self,
        tenant_id: str,
        key_id: str,
        *,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
        request_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Optional[TenantApiKey]:
        """
        Revoke an API key.

        Args:
            tenant_id: The tenant identifier.
            key_id: The key identifier to revoke.
            reason: Optional revoke reason.
            actor: Optional actor id.
            request_id: Optional request correlation id.
            meta: Optional structured metadata.

        Returns:
            The revoked key record, or None if not found.
        """
        record = (
            self.session.query(TenantApiKey)
            .filter(
                and_(
                    TenantApiKey.tenant_id == tenant_id,
                    TenantApiKey.key_id == key_id,
                )
            )
            .first()
        )

        if record:
            record.revoke(reason=reason)
            self.session.flush()
            audit_meta = dict(meta or {})
            if reason:
                audit_meta["reason"] = reason
            self.append_key_audit(
                tenant_id=tenant_id,
                key_id=key_id,
                action="revoked",
                actor=actor,
                request_id=request_id,
                meta=audit_meta,
            )

        return record

    def rotate_tenant_key(
        self,
        tenant_id: str,
        key_id: str,
        *,
        prefix: str = "faim",
        scopes: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Optional[Tuple[TenantApiKey, TenantApiKey, str]]:
        """
        Rotate an active key by creating a replacement and revoking old key.

        Returns:
            Tuple of (old_record, new_record, new_plaintext_key), or None.
        """
        old_record = (
            self.session.query(TenantApiKey)
            .filter(
                and_(
                    TenantApiKey.tenant_id == tenant_id,
                    TenantApiKey.key_id == key_id,
                    TenantApiKey.revoked_at.is_(None),
                )
            )
            .first()
        )
        if old_record is None:
            return None

        inherited_scopes = (
            self._normalize_scopes(scopes)
            if scopes is not None
            else self._normalize_scopes(list(old_record.scopes or []))
        )
        inherited_expiry = expires_at if expires_at is not None else old_record.expires_at

        new_record, new_plaintext = self.create_tenant_key(
            tenant_id=tenant_id,
            prefix=prefix,
            scopes=inherited_scopes,
            expires_at=inherited_expiry,
            created_by=actor,
            rotated_from_key_id=old_record.key_id,
            audit_actor=actor,
            request_id=request_id,
        )

        old_record.revoke(reason=reason or "rotated")
        self.session.flush()

        self.append_key_audit(
            tenant_id=tenant_id,
            key_id=old_record.key_id,
            action="rotated",
            actor=actor,
            request_id=request_id,
            meta={
                "new_key_id": new_record.key_id,
                "reason": reason,
            },
        )

        return old_record, new_record, new_plaintext

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
