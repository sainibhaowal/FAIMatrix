"""Acceptance tests for FAIM-native atom encoding.

Tests end-to-end encoding pipeline and determinism.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.contracts.types import sort_blocks  # noqa: E402
from encoding.text_vectorizer import vectorize_blocks  # noqa: E402
from encoding.vector_schema import (  # noqa: E402
    SCHEMA_VERSION,
    VECTOR_DIMENSION,
    FAIMVector,
)
from perception.packetize import create_packet  # noqa: E402
from perception.router import route_extraction  # noqa: E402


class TestAT_E1_EncodeAtoms:
    """Acceptance tests for atom encoding."""

    def test_text_produces_vectors(self):
        """Text file should produce FAIMVectors."""
        content = b"Hello, this is a test document for FAIM encoding."
        raw_id = "test_raw_enc_001"

        blocks = route_extraction(content, "test.txt", raw_id)
        vectors = vectorize_blocks(blocks)

        assert len(vectors) >= 1
        assert all(isinstance(v, FAIMVector) for v in vectors)

    def test_vector_has_correct_schema(self):
        """Vector should have v1 schema."""
        content = b"Schema test content."
        raw_id = "test_raw_enc_002"

        blocks = route_extraction(content, "test.txt", raw_id)
        vectors = vectorize_blocks(blocks)

        for v in vectors:
            assert v.schema_version == SCHEMA_VERSION
            assert v.schema_version == "v1"

    def test_vector_has_correct_dimension(self):
        """Vector should have fixed dimension."""
        content = b"Dimension test content."
        raw_id = "test_raw_enc_003"

        blocks = route_extraction(content, "test.txt", raw_id)
        vectors = vectorize_blocks(blocks)

        for v in vectors:
            assert len(v.v_native) == VECTOR_DIMENSION
            assert len(v.v_native) == 256

    def test_vector_has_valid_hash(self):
        """Vector hash should be verifiable."""
        content = b"Hash verification test."
        raw_id = "test_raw_enc_004"

        blocks = route_extraction(content, "test.txt", raw_id)
        vectors = vectorize_blocks(blocks)

        for v in vectors:
            assert v.verify_hash(), f"Hash verification failed for {v.block_id}"

    def test_encoding_is_deterministic(self):
        """Same block should produce same vector hash."""
        content = b"Determinism test content."
        raw_id = "test_raw_enc_005"

        blocks = route_extraction(content, "test.txt", raw_id)

        vectors1 = vectorize_blocks(blocks)
        vectors2 = vectorize_blocks(blocks)

        assert len(vectors1) == len(vectors2)
        for v1, v2 in zip(vectors1, vectors2, strict=False):
            assert v1.vector_hash == v2.vector_hash

    def test_vector_references_block(self):
        """Vector should reference source block and raw."""
        content = b"Reference test content."
        raw_id = "test_raw_enc_006"

        blocks = route_extraction(content, "test.txt", raw_id)
        vectors = vectorize_blocks(blocks)

        for v, b in zip(vectors, blocks, strict=False):
            assert v.raw_id == raw_id
            assert v.block_id == str(b.id)
            assert v.block_type == b.block_type

    def test_vector_has_opp_signature(self):
        """Vector should have opposition signature."""
        content = b"Opposition signature test."
        raw_id = "test_raw_enc_007"

        blocks = route_extraction(content, "test.txt", raw_id)
        vectors = vectorize_blocks(blocks)

        for v in vectors:
            assert v.opp_signature is not None
            assert "norm" in v.opp_signature
            assert "density" in v.opp_signature

    def test_vector_has_provenance(self):
        """Vector should have provenance metadata."""
        content = b"Provenance test content."
        raw_id = "test_raw_enc_008"

        blocks = route_extraction(content, "test.txt", raw_id)
        vectors = vectorize_blocks(blocks)

        for v in vectors:
            assert v.provenance is not None
            assert v.provenance["raw_id"] == raw_id
            assert "anchor" in v.provenance
            assert "extractor" in v.provenance
            assert "confidence" in v.provenance

    def test_atoms_have_level_zero(self):
        """Atom vectors should have level 0."""
        content = b"Level test content."
        raw_id = "test_raw_enc_009"

        blocks = route_extraction(content, "test.txt", raw_id)
        vectors = vectorize_blocks(blocks)

        for v in vectors:
            assert v.level == 0

    def test_atoms_have_empty_parents(self):
        """Atom vectors should have no parents."""
        content = b"Parents test content."
        raw_id = "test_raw_enc_010"

        blocks = route_extraction(content, "test.txt", raw_id)
        vectors = vectorize_blocks(blocks)

        for v in vectors:
            assert len(v.parents) == 0
            assert len(v.fractions) == 0

    def test_full_pipeline_integration(self):
        """Full pipeline: extract → packet → encode."""
        content = b"Full pipeline integration test content for FAIM-native encoding."
        raw_id = "test_raw_enc_011"

        # Extract
        blocks = route_extraction(content, "test.txt", raw_id)
        sorted_blocks = sort_blocks(blocks)

        # Packet
        packet = create_packet(raw_id, sorted_blocks)

        # Encode
        vectors = vectorize_blocks(sorted_blocks)

        assert len(vectors) == packet.block_count
        assert all(v.verify_hash() for v in vectors)
