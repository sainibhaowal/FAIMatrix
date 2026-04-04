"""Unit tests for packet validation.

Tests validation rules for anchors, blocks, and packets.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Setup paths for isolated testing
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.contracts.types import (  # noqa: E402
    BlockAnchor,
    EvidenceBlock,
    MemoryPacket,
    uuid7,
)
from perception.packetize import create_packet  # noqa: E402
from perception.validate import (  # noqa: E402
    ValidationError,
    assert_valid,
    validate_anchor,
    validate_block,
    validate_blocks,
    validate_packet,
)


class TestAnchorValidation:
    """Tests for anchor validation."""

    def test_valid_page_anchor(self):
        """Page anchor should be valid."""
        anchor = BlockAnchor(doc_type="pdf", page=1)
        errors = validate_anchor(anchor)
        assert errors == []

    def test_valid_slide_anchor(self):
        """Slide anchor should be valid."""
        anchor = BlockAnchor(doc_type="pptx", slide=1)
        errors = validate_anchor(anchor)
        assert errors == []

    def test_valid_char_anchor(self):
        """Char offset anchor should be valid."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        errors = validate_anchor(anchor)
        assert errors == []

    def test_valid_sheet_row_anchor(self):
        """Sheet/row anchor should be valid."""
        anchor = BlockAnchor(doc_type="xlsx", sheet="Sheet1", row_start=1, row_end=10)
        errors = validate_anchor(anchor)
        assert errors == []

    def test_missing_doc_type(self):
        """Missing doc_type should fail."""
        anchor = BlockAnchor(doc_type="", page=1)
        errors = validate_anchor(anchor)
        assert any("doc_type" in e for e in errors)

    def test_no_position_fields(self):
        """Anchor with no position should fail."""
        anchor = BlockAnchor(doc_type="text")
        errors = validate_anchor(anchor)
        assert any("position field" in e for e in errors)

    def test_invalid_char_range(self):
        """char_start >= char_end should fail."""
        anchor = BlockAnchor(doc_type="text", char_start=10, char_end=5)
        errors = validate_anchor(anchor)
        assert any("char_start" in e and "char_end" in e for e in errors)

    def test_invalid_row_range(self):
        """row_start > row_end should fail."""
        anchor = BlockAnchor(doc_type="xlsx", sheet="Sheet1", row_start=10, row_end=5)
        errors = validate_anchor(anchor)
        assert any("row_start" in e and "row_end" in e for e in errors)


class TestBlockValidation:
    """Tests for block validation."""

    def test_valid_block(self):
        """Valid block should pass."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        block = EvidenceBlock.create(
            raw_id="test_raw",
            anchor=anchor,
            content="Valid content",
            confidence=1.0,
        )
        errors = validate_block(block)
        assert errors == []

    def test_missing_raw_id(self):
        """Missing raw_id should fail."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        block = EvidenceBlock(
            id=uuid7(),
            raw_id="",
            anchor=anchor,
            content="Content",
            block_type="text",
            confidence=1.0,
        )
        errors = validate_block(block)
        assert any("raw_id" in e for e in errors)

    def test_invalid_confidence_high(self):
        """Confidence > 1.0 should fail."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        block = EvidenceBlock(
            id=uuid7(),
            raw_id="test",
            anchor=anchor,
            content="Content",
            block_type="text",
            confidence=1.5,
        )
        errors = validate_block(block)
        assert any("confidence" in e for e in errors)

    def test_invalid_confidence_negative(self):
        """Negative confidence should fail."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        block = EvidenceBlock(
            id=uuid7(),
            raw_id="test",
            anchor=anchor,
            content="Content",
            block_type="text",
            confidence=-0.5,
        )
        errors = validate_block(block)
        assert any("confidence" in e for e in errors)

    def test_anchor_errors_propagate(self):
        """Anchor errors should be included in block errors."""
        anchor = BlockAnchor(doc_type="", page=1)  # Invalid doc_type
        block = EvidenceBlock.create(
            raw_id="test",
            anchor=anchor,
            content="Content",
        )
        errors = validate_block(block)
        assert any("doc_type" in e for e in errors)


class TestBlocksValidation:
    """Tests for validating list of blocks."""

    def test_sorted_blocks_pass(self):
        """Sorted blocks should pass."""
        anchor1 = BlockAnchor(doc_type="pdf", page=1)
        anchor2 = BlockAnchor(doc_type="pdf", page=2)

        block1 = EvidenceBlock.create(raw_id="test", anchor=anchor1, content="Page 1")
        block2 = EvidenceBlock.create(raw_id="test", anchor=anchor2, content="Page 2")

        errors = validate_blocks([block1, block2])
        assert errors == []

    def test_unsorted_blocks_fail(self):
        """Unsorted blocks should fail."""
        anchor1 = BlockAnchor(doc_type="pdf", page=1)
        anchor2 = BlockAnchor(doc_type="pdf", page=2)

        block1 = EvidenceBlock.create(raw_id="test", anchor=anchor1, content="Page 1")
        block2 = EvidenceBlock.create(raw_id="test", anchor=anchor2, content="Page 2")

        # Pass in wrong order
        errors = validate_blocks([block2, block1])
        assert any("not sorted" in e for e in errors)

    def test_empty_blocks_pass(self):
        """Empty block list should pass."""
        errors = validate_blocks([])
        assert errors == []


class TestPacketValidation:
    """Tests for packet validation."""

    def test_valid_packet(self):
        """Valid packet should pass."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        block = EvidenceBlock.create(raw_id="test", anchor=anchor, content="Content")

        packet = create_packet("test", [block])
        errors = validate_packet(packet, [block])

        assert errors == []

    def test_hash_mismatch_fails(self):
        """Tampered hash should fail."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        block = EvidenceBlock.create(raw_id="test", anchor=anchor, content="Content")

        packet = create_packet("test", [block])

        # Tamper with packet hash
        tampered_packet = MemoryPacket(
            id=packet.id,
            raw_id=packet.raw_id,
            block_ids=packet.block_ids,
            block_count=packet.block_count,
            packet_hash="0" * 64,  # Wrong hash
            created_at=packet.created_at,
        )

        errors = validate_packet(tampered_packet, [block])
        assert any("hash mismatch" in e for e in errors)

    def test_block_count_mismatch_fails(self):
        """Wrong block_count should fail."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        block = EvidenceBlock.create(raw_id="test", anchor=anchor, content="Content")

        packet = create_packet("test", [block])

        # Create packet with wrong count
        bad_packet = MemoryPacket(
            id=packet.id,
            raw_id=packet.raw_id,
            block_ids=packet.block_ids,
            block_count=999,  # Wrong count
            packet_hash=packet.packet_hash,
            created_at=packet.created_at,
        )

        errors = validate_packet(bad_packet)
        assert any("block_count" in e for e in errors)


class TestAssertValid:
    """Tests for assert_valid function."""

    def test_valid_raises_nothing(self):
        """Valid packet should not raise."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        block = EvidenceBlock.create(raw_id="test", anchor=anchor, content="Content")
        packet = create_packet("test", [block])

        # Should not raise
        assert_valid(packet, [block])

    def test_invalid_raises_validation_error(self):
        """Invalid packet should raise ValidationError."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        block = EvidenceBlock.create(raw_id="test", anchor=anchor, content="Content")

        # Create packet with wrong hash
        bad_packet = MemoryPacket(
            id=uuid7(),
            raw_id="test",
            block_ids=(str(block.id),),
            block_count=1,
            packet_hash="wrong_hash",
            created_at=block.anchor.sort_key(),  # type: ignore
        )

        with pytest.raises(ValidationError) as exc_info:
            assert_valid(bad_packet, [block])

        assert "Validation failed" in str(exc_info.value)
