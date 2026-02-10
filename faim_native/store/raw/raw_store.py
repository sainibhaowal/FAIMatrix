"""Filesystem-based immutable blob store for FAIM-Native.

This module implements a content-addressable blob store where:
- Files are stored using their SHA256 hash as the filename
- Content is immutable: once stored, never modified or deleted
- Two-level directory structure prevents filesystem limits: {base}/{sha[:2]}/{sha}

Usage:
    store = RawStore("/path/to/blobs")
    raw_ref = store.store(content_bytes)
    content = store.load(raw_ref)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# Use try/except for flexible import (standalone vs package)
try:
    from faim.Faim_Native.core.contracts.types import RawRef  # noqa: F401, I001
    from faim.Faim_Native.core.contracts.types import Sha256Hex  # noqa: F401
    from faim.Faim_Native.core.contracts.types import (
        compute_sha256,
    )
except (ImportError, RuntimeError):
    # Fallback for standalone testing
    import sys

    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import RawRef, compute_sha256


class RawStoreError(Exception):
    """Base exception for RawStore errors."""

    pass


class BlobNotFoundError(RawStoreError):
    """Raised when a blob is not found in the store."""

    pass


class BlobVerificationError(RawStoreError):
    """Raised when blob content doesn't match expected hash."""

    pass


class RawStore:
    """Immutable filesystem blob store with SHA256-based naming.

    Blobs are stored in a two-level directory structure to avoid filesystem
    limits on directory entries:
        {base_path}/{sha256[:2]}/{sha256}

    All operations are idempotent and safe for concurrent access:
    - store() of same content always returns same RawRef
    - load() verifies content hash before returning
    - Blobs are never modified or deleted

    Attributes:
        base_path: Root directory for blob storage.
    """

    STORE_VERSION = "v1"

    def __init__(self, base_path: str | Path) -> None:
        """Initialize the blob store.

        Args:
            base_path: Root directory for storing blobs.
                       Will be created if it doesn't exist.
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _blob_path(self, sha256: str) -> Path:
        """Compute the filesystem path for a blob.

        Uses two-level structure: {base}/{sha[:2]}/{sha}

        Args:
            sha256: SHA256 hex digest.

        Returns:
            Path to the blob file.
        """
        prefix = sha256[:2]
        return self.base_path / prefix / sha256

    def store(
        self,
        content: bytes,
        mime_type: str = "application/octet-stream",
        graph_id: Optional[str] = None,
    ) -> RawRef:
        """Store content and return an immutable RawRef.

        If content with the same hash already exists, returns a RawRef
        pointing to the existing blob (idempotent).

        Args:
            content: Raw bytes to store.
            mime_type: MIME type of the content.
            graph_id: Optional graph scope for the reference.

        Returns:
            RawRef with the blob's metadata.

        Raises:
            RawStoreError: If write fails.
        """
        sha256 = compute_sha256(content)
        blob_path = self._blob_path(sha256)

        # Create parent directory if needed
        blob_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if blob already exists (idempotent)
        if not blob_path.exists():
            # Write atomically using temp file
            temp_path = blob_path.with_suffix(".tmp")
            try:
                temp_path.write_bytes(content)
                temp_path.rename(blob_path)
            except Exception as e:
                # Clean up temp file on failure
                temp_path.unlink(missing_ok=True)
                raise RawStoreError(f"Failed to store blob: {e}") from e

        uri = f"file://{blob_path.absolute()}"

        return RawRef.create(
            sha256=sha256,
            uri=uri,
            size_bytes=len(content),
            mime_type=mime_type,
            graph_id=graph_id,
        )

    def load(self, raw_ref: RawRef, verify: bool = True) -> bytes:
        """Load blob content by RawRef.

        Args:
            raw_ref: Reference to the blob.
            verify: If True, verify SHA256 matches before returning.

        Returns:
            Raw bytes of the blob.

        Raises:
            BlobNotFoundError: If blob doesn't exist.
            BlobVerificationError: If verify=True and hash doesn't match.
        """
        blob_path = self._blob_path(raw_ref.sha256)

        if not blob_path.exists():
            raise BlobNotFoundError(f"Blob not found: {raw_ref.sha256}")

        content = blob_path.read_bytes()

        if verify:
            actual_sha256 = compute_sha256(content)
            if actual_sha256 != raw_ref.sha256:
                raise BlobVerificationError(
                    f"Hash mismatch: expected {raw_ref.sha256}, got {actual_sha256}"
                )

        return content

    def load_by_sha(self, sha256: str, verify: bool = True) -> bytes:
        """Load blob content by SHA256 hash directly.

        Args:
            sha256: SHA256 hex digest of the blob.
            verify: If True, verify SHA256 matches before returning.

        Returns:
            Raw bytes of the blob.

        Raises:
            BlobNotFoundError: If blob doesn't exist.
            BlobVerificationError: If verify=True and hash doesn't match.
        """
        blob_path = self._blob_path(sha256)

        if not blob_path.exists():
            raise BlobNotFoundError(f"Blob not found: {sha256}")

        content = blob_path.read_bytes()

        if verify:
            actual_sha256 = compute_sha256(content)
            if actual_sha256 != sha256:
                raise BlobVerificationError(
                    f"Hash mismatch: expected {sha256}, got {actual_sha256}"
                )

        return content

    def exists(self, raw_ref: RawRef) -> bool:
        """Check if a blob exists.

        Args:
            raw_ref: Reference to check.

        Returns:
            True if blob exists, False otherwise.
        """
        return self._blob_path(raw_ref.sha256).exists()

    def exists_by_sha(self, sha256: str) -> bool:
        """Check if a blob exists by SHA256.

        Args:
            sha256: SHA256 hex digest to check.

        Returns:
            True if blob exists, False otherwise.
        """
        return self._blob_path(sha256).exists()

    def verify(self, raw_ref: RawRef) -> bool:
        """Verify blob integrity by comparing stored hash to content hash.

        Args:
            raw_ref: Reference to verify.

        Returns:
            True if blob exists and hash matches, False otherwise.
        """
        try:
            self.load(raw_ref, verify=True)
            return True
        except (BlobNotFoundError, BlobVerificationError):
            return False

    def delete(self, raw_ref: RawRef) -> bool:
        """Physically delete blob by RawRef.

        Returns:
            True if file existed and was removed, False if already missing.
        """
        return self.delete_by_sha(raw_ref.sha256)

    def delete_by_sha(self, sha256: str) -> bool:
        """Physically delete blob by SHA256.

        Note:
            This is reserved for retention workflows. Normal ingest path remains immutable.
        """
        blob_path = self._blob_path(sha256)
        if not blob_path.exists():
            return False
        blob_path.unlink()
        return True

    def get_stats(self) -> dict:
        """Get storage statistics.

        Returns:
            Dictionary with blob_count, total_size_bytes.
        """
        blob_count = 0
        total_size = 0

        for prefix_dir in self.base_path.iterdir():
            if prefix_dir.is_dir() and len(prefix_dir.name) == 2:
                for blob_file in prefix_dir.iterdir():
                    if blob_file.is_file():
                        blob_count += 1
                        total_size += blob_file.stat().st_size

        return {
            "blob_count": blob_count,
            "total_size_bytes": total_size,
            "store_version": self.STORE_VERSION,
        }
