from __future__ import annotations

import sys
import zlib
from pathlib import Path

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import RawRef
    from faim.Faim_Native.store.raw.crypto import PayloadCipher
    from faim.Faim_Native.store.raw.raw_store import RawStore
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import RawRef
    from store.raw.crypto import PayloadCipher
    from store.raw.raw_store import RawStore


# Version for this encryption wrapper
ENCRYPTED_STORE_VERSION = "v1"


class EncryptedRawStore:
    """Decorator that adds compression + encryption on top of RawStore.

    Behaviour:
    - store: payload -> zlib.compress -> cipher.encrypt -> inner.store
    - load:  inner.load -> cipher.decrypt -> zlib.decompress -> payload

    Attributes:
        inner: The underlying RawStore.
        cipher: The PayloadCipher for encryption/decryption.
        graph_id: Graph ID for per-graph key derivation.
    """

    def __init__(
        self,
        inner: RawStore,
        cipher: PayloadCipher,
        graph_id: str = "default",
    ) -> None:
        """Initialize encrypted store wrapper.

        Args:
            inner: Base RawStore to wrap.
            cipher: PayloadCipher for encryption (use NoopCipher to disable).
            graph_id: Graph ID for key derivation.
        """
        self._inner = inner
        self._cipher = cipher
        self._graph_id = graph_id

    def store(
        self,
        content: bytes,
        mime_type: str = "application/octet-stream",
        graph_id: str | None = None,
    ) -> RawRef:
        """Store content with compression and encryption.

        Args:
            content: Raw bytes to store.
            mime_type: MIME type of the content.

        Returns:
            RawRef pointing to the encrypted blob.
        """
        scope = graph_id or self._graph_id
        compressed = zlib.compress(content)
        encrypted = self._cipher.encrypt(scope, compressed)
        return self._inner.store(
            encrypted, mime_type=mime_type, graph_id=graph_id or self._graph_id
        )

    def load(
        self,
        raw_ref: RawRef,
        verify: bool = True,
        graph_id: str | None = None,
    ) -> bytes:
        """Load and decrypt content.

        Args:
            raw_ref: Reference to the blob.
            verify: If True, verify hash before decryption.

        Returns:
            Decrypted and decompressed content.
        """
        scope = graph_id or self._graph_id
        encrypted = self._inner.load(raw_ref, verify=verify)
        compressed = self._cipher.decrypt(scope, encrypted)
        return zlib.decompress(compressed)

    def exists(self, raw_ref: RawRef) -> bool:
        """Check if encrypted blob exists."""
        return self._inner.exists(raw_ref)

    def exists_by_sha(self, sha256: str) -> bool:
        """Check if encrypted blob exists by SHA."""
        exists_by_sha = getattr(self._inner, "exists_by_sha", None)
        if callable(exists_by_sha):
            return bool(exists_by_sha(sha256))
        return False

    def load_by_sha(
        self,
        sha256: str,
        verify: bool = True,
        graph_id: str | None = None,
    ) -> bytes:
        """Load and decrypt blob content by SHA."""
        scope = graph_id or self._graph_id
        load_by_sha = getattr(self._inner, "load_by_sha", None)
        if not callable(load_by_sha):
            raise AttributeError("Inner store does not support load_by_sha")
        encrypted = load_by_sha(sha256, verify=verify)
        compressed = self._cipher.decrypt(scope, encrypted)
        return zlib.decompress(compressed)

    def verify(self, raw_ref: RawRef) -> bool:
        """Verify encrypted blob integrity in underlying store."""
        verify_fn = getattr(self._inner, "verify", None)
        if callable(verify_fn):
            return bool(verify_fn(raw_ref))
        return self.exists(raw_ref)

    def get_stats(self) -> dict:
        """Delegate storage stats to underlying store."""
        get_stats = getattr(self._inner, "get_stats", None)
        if callable(get_stats):
            stats = dict(get_stats())
        else:
            stats = {}
        stats["encrypted"] = True
        stats["cipher_version"] = self._cipher.version()
        return stats

    def version(self) -> str:
        """Return version string including cipher version."""
        return f"{ENCRYPTED_STORE_VERSION}+{self._cipher.version()}"
