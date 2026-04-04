"""Unit tests for FAIMVector v1 schema.

Tests schema fields, canonical JSON, and hash stability.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.contracts.types import BlockAnchor  # noqa: E402
from encoding.vector_schema import (  # noqa: E402
    SCHEMA_VERSION,
    VECTOR_DIMENSION,
    FAIMVector,
)


class TestVectorSchemaV1:
    """Unit tests for FAIMVector v1 schema."""

    def test_schema_version_is_v1(self):
        """Schema version should be v1."""
        assert SCHEMA_VERSION == "v1"

    def test_vector_dimension_is_256(self):
        """Vector dimension should be 256."""
        assert VECTOR_DIMENSION == 256

    def test_create_vector(self):
        """Should create a valid FAIMVector."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        v_native = [0.0] * VECTOR_DIMENSION

        vector = FAIMVector.create(
            raw_id="test_raw",
            block_id="test_block",
            block_type="text",
            anchor=anchor,
            v_native=v_native,
            opp_signature={"norm": 0.0},
        )

        assert vector.schema_version == "v1"
        assert vector.raw_id == "test_raw"
        assert vector.block_id == "test_block"

    def test_vector_is_frozen(self):
        """FAIMVector should be immutable."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        v_native = [0.0] * VECTOR_DIMENSION

        vector = FAIMVector.create(
            raw_id="test_raw",
            block_id="test_block",
            block_type="text",
            anchor=anchor,
            v_native=v_native,
            opp_signature={"norm": 0.0},
        )

        with pytest.raises(AttributeError):
            vector.raw_id = "modified"  # type: ignore

    def test_v_native_is_tuple(self):
        """v_native should be stored as tuple."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        v_native = [0.1] * VECTOR_DIMENSION

        vector = FAIMVector.create(
            raw_id="test_raw",
            block_id="test_block",
            block_type="text",
            anchor=anchor,
            v_native=v_native,
            opp_signature={"norm": 0.0},
        )

        assert isinstance(vector.v_native, tuple)
        assert len(vector.v_native) == VECTOR_DIMENSION

    def test_wrong_dimension_raises(self):
        """Wrong dimension should raise AssertionError."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        v_native = [0.0] * 100  # Wrong dimension

        with pytest.raises(AssertionError):
            FAIMVector.create(
                raw_id="test_raw",
                block_id="test_block",
                block_type="text",
                anchor=anchor,
                v_native=v_native,
                opp_signature={"norm": 0.0},
            )

    def test_canonical_dict_excludes_usage(self):
        """Canonical dict should not include usage."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        v_native = [0.0] * VECTOR_DIMENSION

        vector = FAIMVector.create(
            raw_id="test_raw",
            block_id="test_block",
            block_type="text",
            anchor=anchor,
            v_native=v_native,
            opp_signature={"norm": 0.0},
        )

        canonical = vector.to_canonical_dict()
        assert "usage" not in canonical
        assert "id" not in canonical

    def test_canonical_dict_has_sorted_keys(self):
        """Canonical dict should have deterministic key order."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        v_native = [0.0] * VECTOR_DIMENSION

        vector = FAIMVector.create(
            raw_id="test_raw",
            block_id="test_block",
            block_type="text",
            anchor=anchor,
            v_native=v_native,
            opp_signature={"z": 1.0, "a": 0.0},
        )

        canonical = vector.to_canonical_dict()

        # opp_signature should be sorted
        opp_keys = list(canonical["opp_signature"].keys())
        assert opp_keys == sorted(opp_keys)

    def test_vector_hash_computed(self):
        """Vector should have computed hash."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        v_native = [0.0] * VECTOR_DIMENSION

        vector = FAIMVector.create(
            raw_id="test_raw",
            block_id="test_block",
            block_type="text",
            anchor=anchor,
            v_native=v_native,
            opp_signature={"norm": 0.0},
        )

        assert vector.vector_hash is not None
        assert len(vector.vector_hash) == 64  # SHA256 hex

    def test_verify_hash_succeeds(self):
        """Hash verification should succeed for valid vector."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        v_native = [0.1] * VECTOR_DIMENSION

        vector = FAIMVector.create(
            raw_id="test_raw",
            block_id="test_block",
            block_type="text",
            anchor=anchor,
            v_native=v_native,
            opp_signature={"norm": 1.0},
        )

        assert vector.verify_hash() is True

    def test_to_dict_roundtrip(self):
        """Vector should survive dict roundtrip."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        v_native = [0.5] * VECTOR_DIMENSION

        vector = FAIMVector.create(
            raw_id="test_raw",
            block_id="test_block",
            block_type="text",
            anchor=anchor,
            v_native=v_native,
            opp_signature={"norm": 0.5},
        )

        data = vector.to_dict()
        restored = FAIMVector.from_dict(data)

        assert restored.vector_hash == vector.vector_hash
        assert restored.v_native == vector.v_native
        assert restored.raw_id == vector.raw_id

    def test_json_roundtrip(self):
        """Vector should survive JSON roundtrip."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        v_native = [0.25] * VECTOR_DIMENSION

        vector = FAIMVector.create(
            raw_id="test_raw",
            block_id="test_block",
            block_type="text",
            anchor=anchor,
            v_native=v_native,
            opp_signature={"norm": 0.25},
        )

        json_str = json.dumps(vector.to_dict())
        data = json.loads(json_str)
        restored = FAIMVector.from_dict(data)

        assert restored.verify_hash() is True

    def test_has_usage_field(self):
        """Vector should have usage tracking field."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        v_native = [0.0] * VECTOR_DIMENSION

        vector = FAIMVector.create(
            raw_id="test_raw",
            block_id="test_block",
            block_type="text",
            anchor=anchor,
            v_native=v_native,
            opp_signature={"norm": 0.0},
        )

        assert "touch_count" in vector.usage
        assert "last_access" in vector.usage
        assert vector.usage["touch_count"] == 0

    def test_has_provenance_field(self):
        """Vector should have provenance field."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        v_native = [0.0] * VECTOR_DIMENSION

        vector = FAIMVector.create(
            raw_id="test_raw",
            block_id="test_block",
            block_type="text",
            anchor=anchor,
            v_native=v_native,
            opp_signature={"norm": 0.0},
            extractor="test_extractor",
            confidence=0.9,
        )

        assert vector.provenance["raw_id"] == "test_raw"
        assert vector.provenance["extractor"] == "test_extractor"
        assert vector.provenance["confidence"] == 0.9
