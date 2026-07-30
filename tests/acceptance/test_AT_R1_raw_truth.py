"""Acceptance test: AT-R1 Raw Truth Doctrine.

Verifies the core FAIM doctrine: RawTruth is immutable.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Setup path for isolated imports
_FAIM_NATIVE_ROOT = Path(__file__).parent.parent.parent
if str(_FAIM_NATIVE_ROOT) not in sys.path:
    sys.path.insert(0, str(_FAIM_NATIVE_ROOT))

from core.contracts.types import compute_sha256  # noqa: E402
from store.pg.repos.raw_repo import RawRepo  # noqa: E402
from store.pg.session import SessionFactory  # noqa: E402
from store.raw.raw_store import RawStore  # noqa: E402


@pytest.mark.acceptance
class TestAT_R1_RawTruth:
    """Acceptance tests for RawTruth immutability doctrine."""

    def test_ingest_creates_blob_on_disk(
        self,
        raw_store: RawStore,
        sample_bytes: bytes,
    ):
        """Ingesting content creates a blob file on disk."""
        raw_ref = raw_store.store(sample_bytes)
        assert raw_store.exists(raw_ref), "Blob should exist after store"

        blob_path = raw_store._blob_path(raw_ref.sha256)
        assert blob_path.exists(), f"Blob file should exist at {blob_path}"

    def test_blob_sha256_matches_original(
        self,
        raw_store: RawStore,
        sample_bytes: bytes,
        sample_bytes_sha256: str,
    ):
        """Blob on disk has same SHA256 as original content."""
        raw_ref = raw_store.store(sample_bytes)
        loaded = raw_store.load(raw_ref, verify=False)
        loaded_sha256 = compute_sha256(loaded)

        assert loaded_sha256 == sample_bytes_sha256
        assert raw_ref.sha256 == sample_bytes_sha256

    def test_blob_verification_succeeds(
        self,
        raw_store: RawStore,
        sample_bytes: bytes,
    ):
        """Verify() confirms blob integrity."""
        raw_ref = raw_store.store(sample_bytes)
        assert raw_store.verify(raw_ref), "Blob verification should succeed"

    def test_rawref_stored_in_database(
        self,
        raw_store: RawStore,
        session_factory: SessionFactory,
        sample_bytes: bytes,
    ):
        """RawRef is correctly stored in database."""
        raw_ref = raw_store.store(sample_bytes, graph_id="test_graph")
        raw_repo = RawRepo()

        with session_factory.atomic() as session:
            raw_repo.create(session, raw_ref)
            fetched = raw_repo.get_by_sha(session, raw_ref.sha256)

        assert fetched is not None, "RawRef should be in database"
        assert fetched.sha256 == raw_ref.sha256
        assert fetched.uri == raw_ref.uri
        assert fetched.size_bytes == len(sample_bytes)
        assert fetched.graph_id == "test_graph"

    def test_idempotent_store(
        self,
        raw_store: RawStore,
        sample_bytes: bytes,
    ):
        """Storing same content twice is idempotent."""
        ref1 = raw_store.store(sample_bytes)
        ref2 = raw_store.store(sample_bytes)

        assert ref1.sha256 == ref2.sha256
        assert ref1.uri == ref2.uri

    def test_idempotent_db_create(
        self,
        raw_store: RawStore,
        session_factory: SessionFactory,
        sample_bytes: bytes,
    ):
        """Creating RawRef in database twice returns same record."""
        raw_ref = raw_store.store(sample_bytes)
        raw_repo = RawRepo()

        with session_factory.atomic() as session:
            saved1 = raw_repo.create(session, raw_ref)
            saved2 = raw_repo.create(session, raw_ref)

        assert saved1.sha256 == saved2.sha256
        assert saved1.id == saved2.id

    def test_content_matches_after_roundtrip(
        self,
        raw_store: RawStore,
        sample_bytes: bytes,
    ):
        """Content is unchanged after store/load roundtrip."""
        raw_ref = raw_store.store(sample_bytes)
        loaded = raw_store.load(raw_ref)
        assert loaded == sample_bytes, "Content should match after roundtrip"

    def test_large_content_integrity(
        self,
        raw_store: RawStore,
        large_sample_bytes: bytes,
    ):
        """Large content maintains integrity through store/load."""
        raw_ref = raw_store.store(large_sample_bytes)
        loaded = raw_store.load(raw_ref)

        assert loaded == large_sample_bytes
        assert raw_ref.size_bytes == len(large_sample_bytes)
