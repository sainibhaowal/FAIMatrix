"""FAIM-Native Crypto Module."""

from store.crypto.envelope import (
    EncryptedBlob,
    generate_dek,
    wrap_dek,
    unwrap_dek,
    encrypt,
    decrypt,
    encrypt_for_storage,
    decrypt_from_storage,
    get_master_key,
)

__all__ = [
    "EncryptedBlob",
    "generate_dek",
    "wrap_dek",
    "unwrap_dek",
    "encrypt",
    "decrypt",
    "encrypt_for_storage",
    "decrypt_from_storage",
    "get_master_key",
]
