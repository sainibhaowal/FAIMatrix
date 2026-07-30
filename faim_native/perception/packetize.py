"""Packetize module for FAIM-native perception.

Creates MemoryPackets from EvidenceBlocks with deterministic ordering and hashing.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import (
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
        EvidenceBlock,
        MemoryPacket,
        compute_packet_hash,
        sort_blocks,
    )


def create_packet(
    raw_id: str,
    blocks: list[EvidenceBlock],
    *,
    metadata: Optional[dict] = None,
) -> MemoryPacket:
    """Create a MemoryPacket from EvidenceBlocks.

    Blocks are sorted deterministically by anchor before hashing.

    Args:
        raw_id: Reference to source RawRef.
        blocks: List of EvidenceBlocks.
        metadata: Optional additional metadata.

    Returns:
        A MemoryPacket with stable ordering and hash.
    """
    if not blocks:
        return MemoryPacket.create(
            raw_id=raw_id,
            block_ids=[],
            packet_hash=compute_packet_hash([]),
            metadata=metadata,
        )

    # Sort blocks by anchor for deterministic ordering
    sorted_blocks = sort_blocks(blocks)

    # Extract block IDs in sorted order
    block_ids = [str(block.id) for block in sorted_blocks]

    # Compute packet hash
    packet_hash = compute_packet_hash(sorted_blocks)

    return MemoryPacket.create(
        raw_id=raw_id,
        block_ids=block_ids,
        packet_hash=packet_hash,
        metadata=metadata,
    )


def packet_to_json(packet: MemoryPacket, blocks: list[EvidenceBlock]) -> dict:
    """Convert packet and blocks to JSON-serializable dict.

    Args:
        packet: The MemoryPacket.
        blocks: Associated EvidenceBlocks.

    Returns:
        Dictionary ready for JSON serialization.
    """
    sorted_blocks = sort_blocks(blocks)

    return {
        "packet": packet.to_dict(),
        "blocks": [block.to_dict() for block in sorted_blocks],
    }


def packet_from_json(data: dict) -> tuple[MemoryPacket, list[EvidenceBlock]]:
    """Reconstruct packet and blocks from JSON.

    Args:
        data: Dictionary from packet_to_json().

    Returns:
        Tuple of (MemoryPacket, list[EvidenceBlock]).
    """
    packet = MemoryPacket.from_dict(data["packet"])
    blocks = [EvidenceBlock.from_dict(b) for b in data["blocks"]]

    return packet, blocks
