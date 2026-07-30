"""Store-related types for FAIM-Native.

This module defines the core types used by the store layer.
All types are immutable (frozen dataclasses) and use deterministic IDs.

Types:
    RawRef: Immutable reference to a raw blob (sha256-based).
    EventRecord: Single journal event with deterministic ID.
    SnapshotRecord: Snapshot metadata with graph hash receipt.
    GraphVersion: Version tracking for cache invalidation.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, NewType, Optional
from uuid import UUID

# -----------------------------------------------------------------------------
# UUID7 Implementation (deterministic, time-ordered)
# -----------------------------------------------------------------------------


def uuid7(timestamp_ms: Optional[int] = None) -> UUID:
    """Generate a UUID version 7 (time-ordered, random).

    UUID7 provides:
    - Time-ordered IDs (sortable by creation time)
    - Millisecond precision timestamp
    - Random suffix for uniqueness

    Args:
        timestamp_ms: Optional timestamp in milliseconds. If None, uses current time.

    Returns:
        A UUID7 instance.
    """
    import os

    if timestamp_ms is None:
        timestamp_ms = int(time.time() * 1000)

    # UUID7 structure (128 bits):
    # - 48 bits: timestamp (milliseconds since Unix epoch)
    # - 4 bits: version (0111 = 7)
    # - 12 bits: random
    # - 2 bits: variant (10)
    # - 62 bits: random

    rand_bytes = os.urandom(10)

    # Build the UUID bytes
    uuid_bytes = bytearray(16)

    # Timestamp (48 bits = 6 bytes)
    uuid_bytes[0] = (timestamp_ms >> 40) & 0xFF
    uuid_bytes[1] = (timestamp_ms >> 32) & 0xFF
    uuid_bytes[2] = (timestamp_ms >> 24) & 0xFF
    uuid_bytes[3] = (timestamp_ms >> 16) & 0xFF
    uuid_bytes[4] = (timestamp_ms >> 8) & 0xFF
    uuid_bytes[5] = timestamp_ms & 0xFF

    # Version (4 bits) + random (12 bits)
    uuid_bytes[6] = 0x70 | (rand_bytes[0] & 0x0F)  # Version 7
    uuid_bytes[7] = rand_bytes[1]

    # Variant (2 bits) + random (62 bits)
    uuid_bytes[8] = 0x80 | (rand_bytes[2] & 0x3F)  # Variant 10
    uuid_bytes[9:16] = rand_bytes[3:10]

    return UUID(bytes=bytes(uuid_bytes))


def uuid7_from_bytes(data: bytes) -> UUID:
    """Generate a deterministic UUID7 from bytes (for testing).

    Uses SHA256 of the data to generate a deterministic random component.
    The timestamp is derived from the first 6 bytes of the hash.

    Args:
        data: Bytes to hash for deterministic UUID generation.

    Returns:
        A deterministic UUID7 instance.
    """
    digest = hashlib.sha256(data).digest()

    uuid_bytes = bytearray(16)

    # Use first 6 bytes as "timestamp" (deterministic but not real time)
    uuid_bytes[0:6] = digest[0:6]

    # Version 7
    uuid_bytes[6] = 0x70 | (digest[6] & 0x0F)
    uuid_bytes[7] = digest[7]

    # Variant 10
    uuid_bytes[8] = 0x80 | (digest[8] & 0x3F)
    uuid_bytes[9:16] = digest[9:16]

    return UUID(bytes=bytes(uuid_bytes))


# -----------------------------------------------------------------------------
# Type Aliases
# -----------------------------------------------------------------------------

GraphId = NewType("GraphId", str)
Sha256Hex = NewType("Sha256Hex", str)


# -----------------------------------------------------------------------------
# RawRef - Immutable reference to raw blob
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RawRef:
    """Immutable reference to a raw blob in the blob store.

    RawRef represents the metadata for an immutable piece of raw content.
    The actual bytes are stored in the filesystem blob store, never in Postgres.

    Attributes:
        id: UUID7 identifier for this reference (deterministic, time-ordered).
        sha256: SHA256 hex digest of the raw content (immutable hash).
        uri: Location of the blob (e.g., file://path or s3://bucket/key).
        mime_type: MIME type of the content (e.g., "text/plain").
        size_bytes: Size of the raw content in bytes.
        created_at: Timestamp when this reference was created.
        graph_id: Optional graph ID for scoping.
    """

    id: UUID
    sha256: Sha256Hex
    uri: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    graph_id: Optional[GraphId] = None

    @classmethod
    def create(
        cls,
        sha256: str,
        uri: str,
        size_bytes: int,
        mime_type: str = "application/octet-stream",
        graph_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> "RawRef":
        """Create a new RawRef with a fresh UUID7.

        Args:
            sha256: SHA256 hex digest of the content.
            uri: Location of the blob.
            size_bytes: Size in bytes.
            mime_type: MIME type.
            graph_id: Optional graph scope.
            created_at: Optional creation timestamp.

        Returns:
            A new RawRef instance.
        """
        return cls(
            id=uuid7(),
            sha256=Sha256Hex(sha256),
            uri=uri,
            mime_type=mime_type,
            size_bytes=size_bytes,
            created_at=created_at or datetime.now(timezone.utc),
            graph_id=GraphId(graph_id) if graph_id else None,
        )


# -----------------------------------------------------------------------------
# EventRecord - Append-only journal event
# -----------------------------------------------------------------------------


def _compute_event_checksum(
    ts: datetime,
    graph_id: str,
    kind: str,
    payload: Dict[str, Any],
) -> str:
    """Compute checksum for event integrity verification.

    Args:
        ts: Event timestamp.
        graph_id: Graph identifier.
        kind: Event kind/type.
        payload: Event payload.

    Returns:
        SHA256 hex digest of the concatenated fields.
    """
    ts_str = ts.isoformat()
    payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    data = f"{ts_str}|{graph_id}|{kind}|{payload_str}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class EventRecord:
    """Single append-only journal event.

    EventRecords are immutable and ordered by sequence number.
    The checksum field ensures integrity and allows verification.

    Attributes:
        id: UUID7 identifier (deterministic, time-ordered).
        seq: Sequence number for strict ordering (assigned by database).
        ts: Timestamp of the event.
        graph_id: Graph this event belongs to.
        kind: Type of event (e.g., "node_created", "edge_added").
        payload: Event data as a dictionary.
        checksum: SHA256 of ts||graph_id||kind||payload for integrity.
        created_at: When this record was persisted.
    """

    id: UUID
    seq: Optional[int]  # Assigned by database, None before persist
    ts: datetime
    graph_id: GraphId
    kind: str
    payload: Dict[str, Any]
    checksum: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        graph_id: str,
        kind: str,
        payload: Dict[str, Any],
        ts: Optional[datetime] = None,
    ) -> "EventRecord":
        """Create a new EventRecord with computed checksum.

        Args:
            graph_id: Graph identifier.
            kind: Event type.
            payload: Event data.
            ts: Optional timestamp (defaults to now).

        Returns:
            A new EventRecord instance with computed checksum.
        """
        event_ts = ts or datetime.now(timezone.utc)
        checksum = _compute_event_checksum(event_ts, graph_id, kind, payload)

        return cls(
            id=uuid7(),
            seq=None,
            ts=event_ts,
            graph_id=GraphId(graph_id),
            kind=kind,
            payload=payload,
            checksum=checksum,
        )

    def verify_checksum(self) -> bool:
        """Verify the event checksum matches the computed value.

        Returns:
            True if checksum is valid, False otherwise.
        """
        expected = _compute_event_checksum(
            self.ts, self.graph_id, self.kind, self.payload
        )
        return self.checksum == expected


# -----------------------------------------------------------------------------
# SnapshotRecord - Snapshot metadata with graph hash receipt
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SnapshotRecord:
    """Snapshot metadata with graph hash receipt.

    Snapshots capture a point-in-time view of the graph state.
    The graph_hash is a receipt that can verify the snapshot integrity.

    Attributes:
        id: UUID7 identifier.
        graph_id: Graph this snapshot belongs to.
        graph_version: Version of the graph at snapshot time.
        graph_hash: Hash receipt for integrity verification.
        node_count: Number of nodes in the graph at snapshot time.
        created_at: When this snapshot was created.
        metadata: Optional additional metadata.
    """

    id: UUID
    graph_id: GraphId
    graph_version: int
    graph_hash: str
    node_count: int
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def create(
        cls,
        graph_id: str,
        graph_version: int,
        graph_hash: str,
        node_count: int,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
    ) -> "SnapshotRecord":
        """Create a new SnapshotRecord.

        Args:
            graph_id: Graph identifier.
            graph_version: Current graph version.
            graph_hash: Computed hash receipt.
            node_count: Number of nodes.
            metadata: Optional metadata.
            created_at: Optional creation timestamp.

        Returns:
            A new SnapshotRecord instance.
        """
        return cls(
            id=uuid7(),
            graph_id=GraphId(graph_id),
            graph_version=graph_version,
            graph_hash=graph_hash,
            node_count=node_count,
            created_at=created_at or datetime.now(timezone.utc),
            metadata=metadata,
        )


# -----------------------------------------------------------------------------
# GraphVersion - Version tracking for cache invalidation
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GraphVersion:
    """Version tracking for a graph (supports cache invalidation).

    Attributes:
        graph_id: Graph identifier.
        version: Current version number (monotonically increasing).
        reason: Reason for the last version bump.
        updated_at: When this version was last updated.
    """

    graph_id: GraphId
    version: int
    reason: Optional[str]
    updated_at: datetime

    @classmethod
    def initial(cls, graph_id: str) -> "GraphVersion":
        """Create initial version (0) for a new graph.

        Args:
            graph_id: Graph identifier.

        Returns:
            A new GraphVersion instance at version 0.
        """
        return cls(
            graph_id=GraphId(graph_id),
            version=0,
            reason="initial",
            updated_at=datetime.now(timezone.utc),
        )

    def bump(self, reason: str) -> "GraphVersion":
        """Create a new version with incremented number.

        Args:
            reason: Reason for the version bump.

        Returns:
            A new GraphVersion instance with incremented version.
        """
        return GraphVersion(
            graph_id=self.graph_id,
            version=self.version + 1,
            reason=reason,
            updated_at=datetime.now(timezone.utc),
        )


# -----------------------------------------------------------------------------
# BlockAnchor - Location anchor within source document
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BlockAnchor:
    """Location anchor within source document.

    Provides deterministic positioning for EvidenceBlocks.
    At least one anchor field must be set based on doc_type.

    Attributes:
        doc_type: Document type ("pdf", "docx", "pptx", "xlsx", "text", "image").
        page: PDF page number (1-indexed).
        slide: PPTX slide number (1-indexed).
        sheet: XLSX sheet name.
        row_start: Starting row (1-indexed).
        row_end: Ending row (inclusive, 1-indexed).
        char_start: Character offset start (0-indexed).
        char_end: Character offset end (exclusive).
        section: Optional section name (for markdown/docx headings).
    """

    doc_type: str
    page: Optional[int] = None
    slide: Optional[int] = None
    sheet: Optional[str] = None
    row_start: Optional[int] = None
    row_end: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    section: Optional[str] = None

    def sort_key(self) -> tuple:
        """Return a sortable key for deterministic ordering.

        Order: page > slide > sheet > row_start > char_start
        """
        return (
            self.page or 0,
            self.slide or 0,
            self.sheet or "",
            self.row_start or 0,
            self.char_start or 0,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "doc_type": self.doc_type,
            "page": self.page,
            "slide": self.slide,
            "sheet": self.sheet,
            "row_start": self.row_start,
            "row_end": self.row_end,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "section": self.section,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BlockAnchor":
        """Create from dictionary."""
        return cls(
            doc_type=data["doc_type"],
            page=data.get("page"),
            slide=data.get("slide"),
            sheet=data.get("sheet"),
            row_start=data.get("row_start"),
            row_end=data.get("row_end"),
            char_start=data.get("char_start"),
            char_end=data.get("char_end"),
            section=data.get("section"),
        )


# -----------------------------------------------------------------------------
# EvidenceBlock - Single extracted evidence block with anchor
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EvidenceBlock:
    """Single extracted evidence block with deterministic anchor.

    EvidenceBlocks are the atomic units of extracted content.
    Each block has a mandatory anchor and clean text content.

    Attributes:
        id: UUID7 identifier (deterministic, time-ordered).
        raw_id: Reference to source RawRef ID.
        anchor: Location anchor within source document.
        content: Clean text content (no HTML, no base64).
        block_type: Type of content ("text", "table", "heading", "code", "image_stub").
        confidence: Extraction confidence (0.0-1.0). OCR=0.2, text=1.0.
        metadata: Optional additional metadata.
    """

    id: UUID
    raw_id: str
    anchor: BlockAnchor
    content: str
    block_type: str
    confidence: float
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def create(
        cls,
        raw_id: str,
        anchor: BlockAnchor,
        content: str,
        block_type: str = "text",
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "EvidenceBlock":
        """Create a new EvidenceBlock with a fresh UUID7.

        Args:
            raw_id: Reference to source RawRef.
            anchor: Location anchor.
            content: Clean text content.
            block_type: Type of content.
            confidence: Extraction confidence.
            metadata: Optional metadata.

        Returns:
            A new EvidenceBlock instance.
        """
        return cls(
            id=uuid7(),
            raw_id=raw_id,
            anchor=anchor,
            content=content,
            block_type=block_type,
            confidence=confidence,
            metadata=metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "raw_id": self.raw_id,
            "anchor": self.anchor.to_dict(),
            "content": self.content,
            "block_type": self.block_type,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceBlock":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]),
            raw_id=data["raw_id"],
            anchor=BlockAnchor.from_dict(data["anchor"]),
            content=data["content"],
            block_type=data["block_type"],
            confidence=data["confidence"],
            metadata=data.get("metadata"),
        )


# -----------------------------------------------------------------------------
# MemoryPacket - Deterministic packet of evidence blocks
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MemoryPacket:
    """Deterministic packet of evidence blocks.

    A MemoryPacket aggregates EvidenceBlocks from a single source
    with a stable ordering and integrity hash.

    Attributes:
        id: UUID7 identifier.
        raw_id: Reference to source RawRef.
        block_ids: Ordered list of block IDs (deterministic).
        block_count: Number of blocks in the packet.
        packet_hash: SHA256 of canonical JSON (for integrity).
        created_at: When this packet was created.
        metadata: Optional additional metadata.
    """

    id: UUID
    raw_id: str
    block_ids: tuple  # Use tuple for immutability
    block_count: int
    packet_hash: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def create(
        cls,
        raw_id: str,
        block_ids: list[str],
        packet_hash: str,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
    ) -> "MemoryPacket":
        """Create a new MemoryPacket.

        Args:
            raw_id: Reference to source RawRef.
            block_ids: Ordered list of block IDs.
            packet_hash: Computed hash receipt.
            metadata: Optional metadata.
            created_at: Optional creation timestamp.

        Returns:
            A new MemoryPacket instance.
        """
        return cls(
            id=uuid7(),
            raw_id=raw_id,
            block_ids=tuple(block_ids),
            block_count=len(block_ids),
            packet_hash=packet_hash,
            created_at=created_at or datetime.now(timezone.utc),
            metadata=metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "raw_id": self.raw_id,
            "block_ids": list(self.block_ids),
            "block_count": self.block_count,
            "packet_hash": self.packet_hash,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryPacket":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]),
            raw_id=data["raw_id"],
            block_ids=tuple(data["block_ids"]),
            block_count=data["block_count"],
            packet_hash=data["packet_hash"],
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata"),
        )


# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------


def compute_sha256(data: bytes) -> Sha256Hex:
    """Compute SHA256 hex digest of bytes.

    Args:
        data: Bytes to hash.

    Returns:
        SHA256 hex digest string.
    """
    return Sha256Hex(hashlib.sha256(data).hexdigest())


def compute_graph_hash(node_hashes: list[str]) -> str:
    """Compute a deterministic graph hash from sorted node hashes.

    Args:
        node_hashes: List of node hash strings.

    Returns:
        SHA256 hex digest of the sorted, concatenated hashes.
    """
    sorted_hashes = sorted(node_hashes)
    combined = "|".join(sorted_hashes)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def compute_packet_hash(blocks: list["EvidenceBlock"]) -> str:
    """Compute a deterministic packet hash from blocks.

    The hash is computed from canonical JSON representation
    of all blocks in sorted order.

    Args:
        blocks: List of EvidenceBlocks.

    Returns:
        SHA256 hex digest of canonical JSON.
    """
    # Sort blocks by anchor for deterministic ordering
    sorted_blocks = sorted(blocks, key=lambda b: b.anchor.sort_key())

    # Create canonical JSON representation
    canonical = []
    for block in sorted_blocks:
        canonical.append(
            {
                "id": str(block.id),
                "raw_id": block.raw_id,
                "anchor": block.anchor.to_dict(),
                "content": block.content,
                "block_type": block.block_type,
                "confidence": block.confidence,
            }
        )

    json_str = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def sort_blocks(blocks: list["EvidenceBlock"]) -> list["EvidenceBlock"]:
    """Sort blocks by anchor for deterministic ordering.

    Args:
        blocks: List of EvidenceBlocks.

    Returns:
        Sorted list of EvidenceBlocks.
    """
    return sorted(blocks, key=lambda b: b.anchor.sort_key())
