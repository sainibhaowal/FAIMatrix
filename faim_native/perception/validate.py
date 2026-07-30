"""Validation module for FAIM-native perception.

Validates EvidenceBlocks and MemoryPackets for integrity and correctness.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import (
        BlockAnchor,
        EvidenceBlock,
        MemoryPacket,
        compute_packet_hash,
        sort_blocks,
    )
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import (
        BlockAnchor,
        EvidenceBlock,
        MemoryPacket,
        compute_packet_hash,
        sort_blocks,
    )


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_anchor(anchor: BlockAnchor) -> list[str]:
    """Validate a BlockAnchor.

    Rules:
    - doc_type must be set
    - At least one position field must be set
    - char_start < char_end if both are set
    - row_start <= row_end if both are set

    Args:
        anchor: BlockAnchor to validate.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors = []

    if not anchor.doc_type:
        errors.append("anchor.doc_type is required")

    # Check at least one position is set
    position_fields = [
        anchor.page,
        anchor.slide,
        anchor.sheet,
        anchor.row_start,
        anchor.char_start,
    ]
    if all(f is None for f in position_fields):
        errors.append("anchor must have at least one position field set")

    # Validate ranges
    if anchor.char_start is not None and anchor.char_end is not None:
        if anchor.char_start >= anchor.char_end:
            errors.append(
                f"anchor.char_start ({anchor.char_start}) must be < char_end ({anchor.char_end})"
            )

    if anchor.row_start is not None and anchor.row_end is not None:
        if anchor.row_start > anchor.row_end:
            errors.append(
                f"anchor.row_start ({anchor.row_start}) must be <= row_end ({anchor.row_end})"
            )

    return errors


def validate_block(block: EvidenceBlock) -> list[str]:
    """Validate an EvidenceBlock.

    Rules:
    - id must be set
    - raw_id must be set
    - anchor must be valid
    - content must be set (can be empty string but not None)
    - confidence must be 0.0-1.0

    Args:
        block: EvidenceBlock to validate.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors = []

    if not block.id:
        errors.append("block.id is required")

    if not block.raw_id:
        errors.append("block.raw_id is required")

    if block.content is None:
        errors.append("block.content is required (can be empty string)")

    if not (0.0 <= block.confidence <= 1.0):
        errors.append(f"block.confidence ({block.confidence}) must be 0.0-1.0")

    # Validate anchor
    anchor_errors = validate_anchor(block.anchor)
    errors.extend([f"block[{block.id}]: {e}" for e in anchor_errors])

    return errors


def validate_blocks(blocks: list[EvidenceBlock]) -> list[str]:
    """Validate a list of EvidenceBlocks.

    Rules:
    - Each block must be valid
    - Blocks should be sorted by anchor (warning, not error)

    Args:
        blocks: List of EvidenceBlocks to validate.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors = []

    for _i, block in enumerate(blocks):
        block_errors = validate_block(block)
        errors.extend(block_errors)

    # Check sorted order
    sorted_blocks = sort_blocks(blocks)
    if blocks and [b.id for b in blocks] != [b.id for b in sorted_blocks]:
        errors.append("blocks are not sorted by anchor (use sort_blocks())")

    return errors


def validate_packet(
    packet: MemoryPacket,
    blocks: Optional[list[EvidenceBlock]] = None,
) -> list[str]:
    """Validate a MemoryPacket.

    Rules:
    - id must be set
    - raw_id must be set
    - block_ids must match block_count
    - packet_hash must be set
    - If blocks provided: hash must match computed hash
    - If blocks provided: block_ids must match sorted block IDs

    Args:
        packet: MemoryPacket to validate.
        blocks: Optional list of blocks to verify hash against.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors = []

    if not packet.id:
        errors.append("packet.id is required")

    if not packet.raw_id:
        errors.append("packet.raw_id is required")

    if len(packet.block_ids) != packet.block_count:
        errors.append(
            f"packet.block_count ({packet.block_count}) doesn't match "
            f"len(block_ids) ({len(packet.block_ids)})"
        )

    if not packet.packet_hash:
        errors.append("packet.packet_hash is required")

    # If blocks provided, verify integrity
    if blocks is not None:
        # Verify hash
        expected_hash = compute_packet_hash(blocks)
        if packet.packet_hash != expected_hash:
            errors.append(
                f"packet_hash mismatch: stored={packet.packet_hash[:16]}... "
                f"computed={expected_hash[:16]}..."
            )

        # Verify block_ids match
        sorted_blocks = sort_blocks(blocks)
        expected_ids = tuple(str(b.id) for b in sorted_blocks)
        if packet.block_ids != expected_ids:
            errors.append("packet.block_ids don't match sorted block IDs")

    return errors


def validate_all(
    packet: MemoryPacket,
    blocks: list[EvidenceBlock],
) -> list[str]:
    """Validate packet and all blocks together.

    Args:
        packet: MemoryPacket to validate.
        blocks: Associated EvidenceBlocks.

    Returns:
        List of all validation error messages.
    """
    errors = []
    errors.extend(validate_blocks(blocks))
    errors.extend(validate_packet(packet, blocks))
    return errors


def assert_valid(packet: MemoryPacket, blocks: list[EvidenceBlock]) -> None:
    """Assert that packet and blocks are valid, raise if not.

    Args:
        packet: MemoryPacket to validate.
        blocks: Associated EvidenceBlocks.

    Raises:
        ValidationError: If any validation errors found.
    """
    errors = validate_all(packet, blocks)
    if errors:
        raise ValidationError(
            f"Validation failed with {len(errors)} errors:\n" + "\n".join(errors)
        )
