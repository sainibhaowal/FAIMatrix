"""Unit tests for packet determinism.

Verifies that same input produces same output across runs.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Setup paths for isolated testing
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.contracts.types import (  # noqa: E402
    BlockAnchor,
    EvidenceBlock,
    compute_packet_hash,
    sort_blocks,
    uuid7,
)
from perception.packetize import create_packet  # noqa: E402
from perception.router import route_extraction  # noqa: E402


class TestPacketDeterminism:
    """Unit tests for deterministic packet generation."""

    def test_same_content_same_blocks(self):
        """Same content should produce same number of blocks."""
        content = b"Deterministic test content."
        raw_id = "test_001"

        blocks1 = route_extraction(content, "test.txt", raw_id)
        blocks2 = route_extraction(content, "test.txt", raw_id)

        assert len(blocks1) == len(blocks2)

    def test_same_blocks_same_hash(self):
        """Same blocks should produce same packet hash."""
        # Create identical blocks with fixed IDs
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)

        # Use same content
        block1 = EvidenceBlock(
            id=uuid7(),
            raw_id="test",
            anchor=anchor,
            content="Same content",
            block_type="text",
            confidence=1.0,
        )

        block2 = EvidenceBlock(
            id=block1.id,  # Same ID
            raw_id="test",
            anchor=anchor,
            content="Same content",
            block_type="text",
            confidence=1.0,
        )

        hash1 = compute_packet_hash([block1])
        hash2 = compute_packet_hash([block2])

        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Different content should produce different hash."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)

        block1 = EvidenceBlock.create(
            raw_id="test",
            anchor=anchor,
            content="Content A",
        )

        block2 = EvidenceBlock.create(
            raw_id="test",
            anchor=anchor,
            content="Content B",
        )

        hash1 = compute_packet_hash([block1])
        hash2 = compute_packet_hash([block2])

        assert hash1 != hash2

    def test_sort_order_is_stable(self):
        """Block sorting should be stable and deterministic."""
        anchor1 = BlockAnchor(doc_type="pdf", page=1)
        anchor2 = BlockAnchor(doc_type="pdf", page=2)
        anchor3 = BlockAnchor(doc_type="pdf", page=3)

        block1 = EvidenceBlock.create(raw_id="test", anchor=anchor1, content="Page 1")
        block2 = EvidenceBlock.create(raw_id="test", anchor=anchor2, content="Page 2")
        block3 = EvidenceBlock.create(raw_id="test", anchor=anchor3, content="Page 3")

        # Sort in different orders
        unsorted1 = [block3, block1, block2]
        unsorted2 = [block2, block3, block1]

        sorted1 = sort_blocks(unsorted1)
        sorted2 = sort_blocks(unsorted2)

        # Should produce same order
        assert [b.anchor.page for b in sorted1] == [1, 2, 3]
        assert [b.anchor.page for b in sorted2] == [1, 2, 3]

    def test_hash_depends_on_order(self):
        """Blocks in different order should produce same hash after sorting."""
        anchor1 = BlockAnchor(doc_type="pdf", page=1)
        anchor2 = BlockAnchor(doc_type="pdf", page=2)

        # Use deterministic IDs
        block1_id = uuid7()
        block2_id = uuid7()

        block1 = EvidenceBlock(
            id=block1_id,
            raw_id="test",
            anchor=anchor1,
            content="First",
            block_type="text",
            confidence=1.0,
        )
        block2 = EvidenceBlock(
            id=block2_id,
            raw_id="test",
            anchor=anchor2,
            content="Second",
            block_type="text",
            confidence=1.0,
        )

        # compute_packet_hash sorts internally
        hash_order1 = compute_packet_hash([block1, block2])
        hash_order2 = compute_packet_hash([block2, block1])

        assert hash_order1 == hash_order2

    def test_anchor_sort_key_ordering(self):
        """Anchor sort keys should order correctly."""
        # Page ordering
        a1 = BlockAnchor(doc_type="pdf", page=1)
        a2 = BlockAnchor(doc_type="pdf", page=2)
        assert a1.sort_key() < a2.sort_key()

        # Slide ordering
        a3 = BlockAnchor(doc_type="pptx", slide=1)
        a4 = BlockAnchor(doc_type="pptx", slide=2)
        assert a3.sort_key() < a4.sort_key()

        # Char offset ordering
        a5 = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        a6 = BlockAnchor(doc_type="text", char_start=10, char_end=20)
        assert a5.sort_key() < a6.sort_key()

    def test_packet_block_ids_match_sorted_order(self):
        """Packet block_ids should match sorted block order."""
        anchor1 = BlockAnchor(doc_type="pdf", page=2)
        anchor2 = BlockAnchor(doc_type="pdf", page=1)

        block1 = EvidenceBlock.create(raw_id="test", anchor=anchor1, content="Page 2")
        block2 = EvidenceBlock.create(raw_id="test", anchor=anchor2, content="Page 1")

        # Pass in unsorted order
        packet = create_packet("test", [block1, block2])

        # Sorted order should be block2, block1 (page 1 before page 2)
        sorted_blocks = sort_blocks([block1, block2])
        expected_ids = [str(b.id) for b in sorted_blocks]

        assert list(packet.block_ids) == expected_ids

    def test_empty_blocks_deterministic_hash(self):
        """Empty block list should produce consistent hash."""
        hash1 = compute_packet_hash([])
        hash2 = compute_packet_hash([])

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_block_to_dict_roundtrip(self):
        """Block should survive dict roundtrip."""
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=10)
        block = EvidenceBlock.create(
            raw_id="test",
            anchor=anchor,
            content="Test content",
            metadata={"key": "value"},
        )

        data = block.to_dict()
        restored = EvidenceBlock.from_dict(data)

        assert restored.id == block.id
        assert restored.raw_id == block.raw_id
        assert restored.content == block.content
        assert restored.anchor.doc_type == block.anchor.doc_type
        assert restored.metadata == block.metadata
