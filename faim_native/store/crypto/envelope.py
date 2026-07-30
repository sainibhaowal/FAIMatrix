"""
FAIM-Native Envelope Encryption (Stage-11).

Provides AES-256-GCM envelope encryption for raw files.

Architecture:
- Master Key: Stored in environment (FAIM_MASTER_KEY) or derived
- Data Encryption Keys (DEKs): Per-tenant, wrapped by master key
- Raw files encrypted with tenant DEK

Security:
- AES-256-GCM for authenticated encryption
- Unique nonce per encryption
- DEKs wrapped with master key for key rotation
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# =============================================================================
# Constants
# =============================================================================

KEY_SIZE = 32  # 256 bits
NONCE_SIZE = 12  # 96 bits (GCM standard)
TAG_SIZE = 16  # 128 bits (GCM standard)

# Environment variable for master key
MASTER_KEY_ENV = "FAIM_MASTER_KEY"
MASTER_KEY_SALT_ENV = "FAIM_MASTER_SALT"
MASTER_KEY_PASSWORD_ENV = "FAIM_MASTER_PASSWORD"
MASTER_KEY_PREVIOUS_ENV = "FAIM_MASTER_KEY_PREVIOUS_JSON"


# =============================================================================
# Encrypted Blob Format
# =============================================================================


@dataclass
class EncryptedBlob:
    """
    Container for encrypted data.

    Format: version (1 byte) + nonce (12 bytes) + ciphertext + tag (16 bytes)

    Attributes:
        version: Encryption version (for future algorithm changes).
        nonce: Unique nonce for this encryption.
        ciphertext: Encrypted data (includes GCM tag at end).
    """

    version: int
    nonce: bytes
    ciphertext: bytes

    def to_bytes(self) -> bytes:
        """Serialize to bytes for storage."""
        return bytes([self.version]) + self.nonce + self.ciphertext

    @classmethod
    def from_bytes(cls, data: bytes) -> "EncryptedBlob":
        """Deserialize from bytes."""
        if len(data) < 1 + NONCE_SIZE + TAG_SIZE:
            raise ValueError("Invalid encrypted blob: too short")

        version = data[0]
        nonce = data[1 : 1 + NONCE_SIZE]
        ciphertext = data[1 + NONCE_SIZE :]

        return cls(version=version, nonce=nonce, ciphertext=ciphertext)


# =============================================================================
# Runtime Flags
# =============================================================================


def encryption_at_rest_enabled() -> bool:
    """Check if tenant envelope encryption is enabled."""
    raw = os.getenv("FAIM_ENCRYPTION_AT_REST", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def encryption_fail_closed() -> bool:
    """If true, startup/request fails when encryption cannot initialize."""
    raw = os.getenv("FAIM_ENCRYPTION_FAIL_CLOSED", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


# =============================================================================
# Key Derivation
# =============================================================================


def derive_master_key(password: str, salt: bytes) -> bytes:
    """
    Derive master key from password using PBKDF2.

    Used when FAIM_MASTER_KEY is not provided directly.

    Args:
        password: The master password.
        salt: Random salt (store with the database).

    Returns:
        32-byte master key.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=100_000,
    )
    return kdf.derive(password.encode())


def get_master_key() -> bytes:
    """
    Get the master key from environment.

    Prefers FAIM_MASTER_KEY as hex-encoded key.
    Falls back to PBKDF2 derivation if salt is provided.

    Returns:
        32-byte master key.

    Raises:
        ValueError: If master key is not configured.
    """
    # Prefer direct key
    key_hex = os.getenv(MASTER_KEY_ENV)
    if key_hex:
        key = bytes.fromhex(key_hex)
        if len(key) == KEY_SIZE:
            return key
        raise ValueError(f"FAIM_MASTER_KEY must be {KEY_SIZE * 2} hex chars")

    # Fall back to derivation (for development)
    password = os.getenv(MASTER_KEY_PASSWORD_ENV)
    salt_hex = os.getenv(MASTER_KEY_SALT_ENV)

    if password and salt_hex:
        salt = bytes.fromhex(salt_hex)
        return derive_master_key(password, salt)

    raise ValueError(
        f"Encryption requires {MASTER_KEY_ENV} or "
        f"{MASTER_KEY_PASSWORD_ENV} + {MASTER_KEY_SALT_ENV}"
    )


def _parse_hex_key(raw: str) -> bytes:
    key = bytes.fromhex(str(raw).strip())
    if len(key) != KEY_SIZE:
        raise ValueError(f"Master key must be {KEY_SIZE} bytes")
    return key


def get_master_key_ring(
    master_key: Optional[bytes] = None,
    previous_keys: Optional[Sequence[bytes]] = None,
) -> List[bytes]:
    """Return the current master key followed by any configured previous keys."""
    current = master_key or get_master_key()
    ring: List[bytes] = [current]

    previous_payload = os.getenv(MASTER_KEY_PREVIOUS_ENV, "").strip()
    if previous_payload:
        parsed: object
        try:
            parsed = json.loads(previous_payload)
        except json.JSONDecodeError:
            parsed = [
                item.strip()
                for item in previous_payload.split(",")
                if item.strip()
            ]

        if isinstance(parsed, str):
            parsed = [parsed]
        if isinstance(parsed, list):
            for item in parsed:
                if not item:
                    continue
                candidate = _parse_hex_key(str(item))
                if candidate not in ring:
                    ring.append(candidate)

    if previous_keys:
        for candidate in previous_keys:
            if len(candidate) != KEY_SIZE:
                raise ValueError(f"Master key must be {KEY_SIZE} bytes")
            if candidate not in ring:
                ring.append(candidate)

    return ring


def master_key_fingerprint(master_key: bytes) -> str:
    """Return a stable fingerprint for display and rotation bookkeeping."""
    return hashlib.sha256(master_key).hexdigest()


# =============================================================================
# Data Encryption Key Management
# =============================================================================


def generate_dek() -> bytes:
    """Generate a new Data Encryption Key."""
    return secrets.token_bytes(KEY_SIZE)


def wrap_dek(dek: bytes, master_key: bytes) -> bytes:
    """
    Wrap (encrypt) a DEK with the master key.

    Args:
        dek: The data encryption key to wrap.
        master_key: The master key.

    Returns:
        Wrapped DEK (nonce + ciphertext).
    """
    aesgcm = AESGCM(master_key)
    nonce = secrets.token_bytes(NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, dek, None)
    return nonce + ciphertext


def wrap_dek_with_current_key(
    dek: bytes,
    master_keys: Sequence[bytes],
) -> Tuple[bytes, str]:
    """Wrap a DEK with the first key in the configured ring."""
    if not master_keys:
        raise ValueError("At least one master key is required")
    current_key = master_keys[0]
    return wrap_dek(dek, current_key), master_key_fingerprint(current_key)


def unwrap_dek(wrapped_dek: bytes, master_key: bytes) -> bytes:
    """
    Unwrap (decrypt) a DEK with the master key.

    Args:
        wrapped_dek: The wrapped DEK (nonce + ciphertext).
        master_key: The master key.

    Returns:
        The unwrapped DEK.
    """
    if len(wrapped_dek) < NONCE_SIZE + TAG_SIZE:
        raise ValueError("Invalid wrapped DEK")

    nonce = wrapped_dek[:NONCE_SIZE]
    ciphertext = wrapped_dek[NONCE_SIZE:]

    aesgcm = AESGCM(master_key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def unwrap_dek_with_ring(
    wrapped_dek: bytes,
    master_keys: Sequence[bytes],
) -> Tuple[bytes, int]:
    """Try a wrapped DEK against a master-key ring."""
    if not master_keys:
        raise ValueError("At least one master key is required")

    last_error: Optional[Exception] = None
    for index, master_key in enumerate(master_keys):
        try:
            return unwrap_dek(wrapped_dek, master_key), index
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    raise ValueError("Unable to unwrap DEK with configured master key ring") from last_error


# =============================================================================
# Encryption/Decryption
# =============================================================================


def encrypt(plaintext: bytes, key: bytes) -> EncryptedBlob:
    """
    Encrypt data using AES-256-GCM.

    Args:
        plaintext: Data to encrypt.
        key: 32-byte encryption key.

    Returns:
        EncryptedBlob containing the encrypted data.
    """
    if len(key) != KEY_SIZE:
        raise ValueError(f"Key must be {KEY_SIZE} bytes")

    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    return EncryptedBlob(version=1, nonce=nonce, ciphertext=ciphertext)


def decrypt(blob: EncryptedBlob, key: bytes) -> bytes:
    """
    Decrypt data using AES-256-GCM.

    Args:
        blob: EncryptedBlob to decrypt.
        key: 32-byte encryption key.

    Returns:
        Decrypted plaintext.

    Raises:
        InvalidTag: If authentication fails (tampered data).
    """
    if len(key) != KEY_SIZE:
        raise ValueError(f"Key must be {KEY_SIZE} bytes")

    if blob.version != 1:
        raise ValueError(f"Unsupported encryption version: {blob.version}")

    aesgcm = AESGCM(key)
    return aesgcm.decrypt(blob.nonce, blob.ciphertext, None)


# =============================================================================
# Convenience Functions
# =============================================================================


def encrypt_for_storage(plaintext: bytes, key: bytes) -> bytes:
    """
    Encrypt and serialize for database storage.

    Args:
        plaintext: Data to encrypt.
        key: 32-byte encryption key.

    Returns:
        Serialized encrypted blob.
    """
    blob = encrypt(plaintext, key)
    return blob.to_bytes()


def decrypt_from_storage(data: bytes, key: bytes) -> bytes:
    """
    Deserialize and decrypt from database storage.

    Args:
        data: Serialized encrypted blob.
        key: 32-byte encryption key.

    Returns:
        Decrypted plaintext.
    """
    blob = EncryptedBlob.from_bytes(data)
    return decrypt(blob, key)


# =============================================================================
# Tenant DEK Manager
# =============================================================================


class TenantDEKManager:
    """Manage wrapped tenant DEKs using table tenant_crypto_keys.

    This class is intentionally lightweight and request-safe:
    - Each call uses a short-lived session from session_factory
    - A small in-process cache avoids repeated DB round-trips
    """

    def __init__(
        self,
        session_factory: Callable[[], Any],
        master_key: Optional[bytes] = None,
        previous_master_keys: Optional[Sequence[bytes]] = None,
    ) -> None:
        if session_factory is None:
            raise ValueError("session_factory is required")

        self._session_factory = session_factory
        self._master_keys = get_master_key_ring(master_key, previous_master_keys)
        self._master_key = self._master_keys[0]
        self._dek_cache: Dict[str, bytes] = {}

    @property
    def current_master_key_fingerprint(self) -> str:
        return master_key_fingerprint(self._master_key)

    def clear_cache(self) -> None:
        """Clear in-memory DEK cache."""
        self._dek_cache.clear()

    def _get_or_create_wrapped(self, tenant_id: str) -> bytes:
        # Local import avoids heavy DB import unless encryption is enabled.
        from sqlalchemy.exc import IntegrityError

        from store.pg.models_crypto import TenantCryptoKey

        session = self._session_factory()
        try:
            model = (
                session.query(TenantCryptoKey)
                .filter(TenantCryptoKey.tenant_id == tenant_id)
                .first()
            )
            if model is not None:
                return bytes(model.dek_wrapped)

            wrapped, fingerprint = wrap_dek_with_current_key(
                generate_dek(), self._master_keys
            )
            created = TenantCryptoKey(
                tenant_id=tenant_id,
                dek_wrapped=wrapped,
                master_key_fingerprint=fingerprint,
                created_at=datetime.now(timezone.utc),
                rotated_at=datetime.now(timezone.utc),
            )
            session.add(created)
            try:
                session.commit()
                return wrapped
            except IntegrityError:
                # Concurrent create won race; fetch canonical row.
                session.rollback()
                existing = (
                    session.query(TenantCryptoKey)
                    .filter(TenantCryptoKey.tenant_id == tenant_id)
                    .first()
                )
                if existing is None:
                    raise
                return bytes(existing.dek_wrapped)
        finally:
            session.close()

    def get_or_create_dek(self, tenant_id: str) -> bytes:
        """Return unwrapped DEK for tenant, creating if needed."""
        tid = str(tenant_id or "").strip()
        if not tid:
            raise ValueError("tenant_id is required for DEK lookup")

        cached = self._dek_cache.get(tid)
        if cached is not None:
            return cached

        wrapped = self._get_or_create_wrapped(tid)
        dek, _ = unwrap_dek_with_ring(wrapped, self._master_keys)
        self._dek_cache[tid] = dek
        return dek

    def rewrap_tenant_dek(self, tenant_id: str) -> Dict[str, Any]:
        """Rewrap a tenant DEK under the current master key."""
        from store.pg.models_crypto import TenantCryptoKey

        tid = str(tenant_id or "").strip()
        if not tid:
            raise ValueError("tenant_id is required for DEK rotation")

        session = self._session_factory()
        try:
            model = (
                session.query(TenantCryptoKey)
                .filter(TenantCryptoKey.tenant_id == tid)
                .first()
            )
            if model is None:
                model = TenantCryptoKey(tenant_id=tid)
                session.add(model)

            existing_fingerprint = str(
                getattr(model, "master_key_fingerprint", "") or ""
            ).strip()
            current_fingerprint = self.current_master_key_fingerprint
            if model.dek_wrapped and existing_fingerprint == current_fingerprint:
                session.commit()
                return {
                    "tenant_id": tid,
                    "status": "already_current",
                    "master_key_fingerprint": current_fingerprint,
                    "source_master_key_fingerprint": existing_fingerprint,
                }

            wrapped = bytes(model.dek_wrapped) if model.dek_wrapped else b""
            if wrapped:
                dek, source_index = unwrap_dek_with_ring(wrapped, self._master_keys)
                source_fingerprint = master_key_fingerprint(
                    self._master_keys[source_index]
                )
            else:
                dek = generate_dek()
                source_fingerprint = None

            new_wrapped, fingerprint = wrap_dek_with_current_key(
                dek, self._master_keys
            )
            model.dek_wrapped = new_wrapped
            model.master_key_fingerprint = fingerprint
            model.rotated_at = datetime.now(timezone.utc)
            session.commit()
            self._dek_cache.pop(tid, None)
            return {
                "tenant_id": tid,
                "status": "rewrapped",
                "master_key_fingerprint": fingerprint,
                "source_master_key_fingerprint": source_fingerprint,
            }
        finally:
            session.close()

    def rotate_tenant_dek(self, tenant_id: str) -> Dict[str, Any]:
        """Backward-compatible alias for tenant DEK rewrap."""
        return self.rewrap_tenant_dek(tenant_id)

    def encrypt_for_tenant(self, tenant_id: str, plaintext: bytes) -> bytes:
        """Encrypt bytes with tenant DEK."""
        key = self.get_or_create_dek(tenant_id)
        return encrypt_for_storage(plaintext, key)

    def decrypt_for_tenant(self, tenant_id: str, data: bytes) -> bytes:
        """Decrypt bytes with tenant DEK."""
        key = self.get_or_create_dek(tenant_id)
        return decrypt_from_storage(data, key)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "EncryptedBlob",
    "generate_dek",
    "wrap_dek",
    "wrap_dek_with_current_key",
    "unwrap_dek",
    "unwrap_dek_with_ring",
    "encrypt",
    "decrypt",
    "encrypt_for_storage",
    "decrypt_from_storage",
    "get_master_key",
    "get_master_key_ring",
    "master_key_fingerprint",
    "derive_master_key",
    "encryption_at_rest_enabled",
    "encryption_fail_closed",
    "TenantDEKManager",
]
