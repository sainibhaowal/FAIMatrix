"""Store raw __init__.py for FAIM-Native."""

from __future__ import annotations

__all__ = [
    "RawStore",
    "RawStoreError",
    "BlobNotFoundError",
    "BlobVerificationError",
    "PayloadCipher",
    "NoopCipher",
    "FernetCipher",
    "CRYPTO_VERSION",
    "build_cipher_from_env",
    "EncryptedRawStore",
]


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name in (
        "RawStore",
        "RawStoreError",
        "BlobNotFoundError",
        "BlobVerificationError",
    ):
        from .raw_store import (
            BlobNotFoundError,
            BlobVerificationError,
            RawStore,
            RawStoreError,
        )

        mapping = {
            "RawStore": RawStore,
            "RawStoreError": RawStoreError,
            "BlobNotFoundError": BlobNotFoundError,
            "BlobVerificationError": BlobVerificationError,
        }
        return mapping[name]
    elif name in (
        "PayloadCipher",
        "NoopCipher",
        "FernetCipher",
        "CRYPTO_VERSION",
        "build_cipher_from_env",
    ):
        from .crypto import (
            CRYPTO_VERSION,
            FernetCipher,
            NoopCipher,
            PayloadCipher,
            build_cipher_from_env,
        )

        mapping = {
            "PayloadCipher": PayloadCipher,
            "NoopCipher": NoopCipher,
            "FernetCipher": FernetCipher,
            "CRYPTO_VERSION": CRYPTO_VERSION,
            "build_cipher_from_env": build_cipher_from_env,
        }
        return mapping[name]
    elif name == "EncryptedRawStore":
        from .encrypted_payload_store import EncryptedRawStore

        return EncryptedRawStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
