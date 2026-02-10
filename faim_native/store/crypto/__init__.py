"""FAIM-Native Crypto Module."""

from store.crypto.envelope import (
    EncryptedBlob,
    TenantDEKManager,
    decrypt,
    decrypt_from_storage,
    encryption_at_rest_enabled,
    encryption_fail_closed,
    encrypt,
    encrypt_for_storage,
    generate_dek,
    get_master_key,
    unwrap_dek,
    wrap_dek,
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
    "encryption_at_rest_enabled",
    "encryption_fail_closed",
]
