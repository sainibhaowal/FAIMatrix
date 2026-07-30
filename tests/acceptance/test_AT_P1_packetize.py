"""Acceptance tests for FAIM-native packetization.

Tests end-to-end packet creation from various file types.
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
    EvidenceBlock,
    compute_packet_hash,
    sort_blocks,
)
from perception.packetize import (  # noqa: E402
    create_packet,
    packet_from_json,
    packet_to_json,
)
from perception.router import get_doc_type, route_extraction  # noqa: E402
from perception.validate import validate_all  # noqa: E402


class TestAT_P1_Packetize:
    """Acceptance tests for packetization."""

    def test_text_file_produces_blocks(self):
        """Text file should produce at least one block."""
        content = b"Hello, this is a test document.\n\nIt has multiple paragraphs."
        raw_id = "test_raw_001"

        blocks = route_extraction(content, "test.txt", raw_id)

        assert len(blocks) >= 1
        assert all(isinstance(b, EvidenceBlock) for b in blocks)
        assert all(b.raw_id == raw_id for b in blocks)

    def test_blocks_have_anchors(self):
        """All blocks must have valid anchors."""
        content = b"Test content for anchor validation."
        raw_id = "test_raw_002"

        blocks = route_extraction(content, "test.txt", raw_id)

        for block in blocks:
            assert block.anchor is not None
            assert block.anchor.doc_type == "text"

    def test_packet_created_from_blocks(self):
        """Packet should be created from blocks."""
        content = b"Packet test content."
        raw_id = "test_raw_003"

        blocks = route_extraction(content, "test.txt", raw_id)
        packet = create_packet(raw_id, blocks)

        assert packet is not None
        assert packet.raw_id == raw_id
        assert packet.block_count == len(blocks)
        assert len(packet.block_ids) == len(blocks)

    def test_packet_hash_is_deterministic(self):
        """Same blocks should produce same hash."""
        content = b"Deterministic hash test."
        raw_id = "test_raw_004"

        blocks = route_extraction(content, "test.txt", raw_id)

        hash1 = compute_packet_hash(blocks)
        hash2 = compute_packet_hash(blocks)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex

    def test_packet_json_roundtrip(self):
        """Packet should survive JSON serialization."""
        content = b"JSON roundtrip test."
        raw_id = "test_raw_005"

        blocks = route_extraction(content, "test.txt", raw_id)
        packet = create_packet(raw_id, blocks)

        # Serialize
        json_data = packet_to_json(packet, blocks)

        # Deserialize
        packet2, blocks2 = packet_from_json(json_data)

        assert packet2.id == packet.id
        assert packet2.raw_id == packet.raw_id
        assert packet2.packet_hash == packet.packet_hash
        assert len(blocks2) == len(blocks)

    def test_validation_passes_for_valid_packet(self):
        """Valid packet should pass validation."""
        content = b"Validation test content."
        raw_id = "test_raw_006"

        blocks = route_extraction(content, "test.txt", raw_id)
        sorted_blocks = sort_blocks(blocks)
        packet = create_packet(raw_id, sorted_blocks)

        errors = validate_all(packet, sorted_blocks)

        assert errors == [], f"Validation failed: {errors}"

    def test_markdown_produces_section_blocks(self):
        """Markdown should produce section-aware blocks."""
        content = b"""# Header 1

This is the first section.

## Header 2

This is the second section.
"""
        raw_id = "test_raw_007"

        blocks = route_extraction(content, "test.md", raw_id)

        assert len(blocks) >= 2
        # Check that sections are captured
        sections = [b.anchor.section for b in blocks if b.anchor.section]
        assert len(sections) >= 1

    def test_image_produces_stub_block(self):
        """Image file should produce OCR stub with low confidence."""
        # Fake image bytes (PNG header)
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        raw_id = "test_raw_008"

        blocks = route_extraction(content, "test.png", raw_id)

        assert len(blocks) == 1
        assert blocks[0].block_type == "image_stub"
        assert blocks[0].confidence == 0.2

    def test_doc_type_detection(self):
        """Document types should be correctly detected."""
        assert get_doc_type("test.pdf") == "pdf"
        assert get_doc_type("test.docx") == "docx"
        assert get_doc_type("test.pptx") == "pptx"
        assert get_doc_type("test.xlsx") == "xlsx"
        assert get_doc_type("test.txt") == "text"
        assert get_doc_type("test.py") == "text"
        assert get_doc_type("test.png") == "image"

    def test_no_html_in_content(self):
        """Content should be clean text, no HTML."""
        content = b"Clean text content without any markup."
        raw_id = "test_raw_009"

        blocks = route_extraction(content, "test.txt", raw_id)

        for block in blocks:
            assert "<html>" not in block.content.lower()
            assert "<body>" not in block.content.lower()
            assert "<div>" not in block.content.lower()
            assert "base64" not in block.content.lower()

    def test_empty_file_produces_fallback(self):
        """Empty file should produce at least one fallback block."""
        content = b""
        raw_id = "test_raw_010"

        blocks = route_extraction(content, "test.txt", raw_id)

        # Should have at least one block (fallback)
        assert len(blocks) >= 1
