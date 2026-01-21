"""FAIM-Native Crypto Module."""

from store.crypto.envelope import (
    EncryptedBlob,
    decrypt,
    decrypt_from_storage,
    encrypt,
    encrypt_for_storage,
    generate_dek,
    get_master_key,
    unwrap_dek,
    wrap_dek,
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
