"""FAIM-Native Crypto Module."""

from store.crypto.envelope import (
    EncryptedBlob,
    TenantDEKManager,
    decrypt,
    decrypt_from_storage,
    encrypt,
    encrypt_for_storage,
    encryption_at_rest_enabled,
    encryption_fail_closed,
    generate_dek,
    get_master_key,
    get_master_key_ring,
    master_key_fingerprint,
    unwrap_dek,
    unwrap_dek_with_ring,
    wrap_dek,
    wrap_dek_with_current_key,
)

__all__ = [
    "EncryptedBlob",
    "TenantDEKManager",
    "generate_dek",
    "wrap_dek",
    "unwrap_dek",
    "encrypt",
    "decrypt",
    "encrypt_for_storage",
    "decrypt_from_storage",
    "get_master_key",
    "get_master_key_ring",
    "master_key_fingerprint",
    "encryption_at_rest_enabled",
    "encryption_fail_closed",
    "unwrap_dek_with_ring",
    "wrap_dek_with_current_key",
]
