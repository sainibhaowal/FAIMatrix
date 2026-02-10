"""FAIM-Native Orchestration: Ingest Flow.

Pure wiring layer that uses Stage-1..4.1.1 components.

NO CHUNKING. NO ML. DETERMINISTIC.

Pipeline:
1. perception.router.route_extraction → EvidenceBlocks
2. perception.packetize.create_packet → MemoryPacket (with hash)
3. perception.validate.assert_valid → Validation
4. encoding.encode_packet → FAIMVectors (256 dim)
5. core.engine.write_atoms → Write to graph

Events emitted: INGEST_START, PACKET_CREATED, ENCODED, WRITE_ATOMS_DONE
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

logger = logging.getLogger(__name__)


# =============================================================================
# Types
# =============================================================================


class PersistMode(str, Enum):
    """Durability mode for writes."""

    STRICT = "strict"  # Wait for all writes to commit
    RELAXED = "relaxed"  # Async writes (faster but less durable)


class FAIMProfile(str, Enum):
    """FAIM execution profile."""

    STRICT = "strict"  # Deterministic, no GPU, exact algorithms
    FAST = "fast"  # May use GPU, approximate algorithms
    RELAXED = "relaxed"  # Most permissive


@dataclass(frozen=True)
class IngestResult:
    """Result returned by run_ingest.

    Attributes:
        status: "completed", "dedup_hit", or "error"
        packet_hash: Idempotency key (SHA256 of packet)
        graph_version: Graph version after write
        nodes_written: Number of nodes created/updated
        merges: Number of antisymmetric merges
        block_count: Number of EvidenceBlocks extracted
        vector_count: Number of vectors encoded
        diagnostics_hash: Hash of diagnostics snapshot (if available)
        events_emitted: List of event types emitted
        latency_ms: Total latency in milliseconds
        dedup_hit: True if this was a duplicate (no processing done)
        raw_id: Raw file ID
        error: Error message if status is "error"
    """

    status: str
    packet_hash: str
    graph_version: int
    nodes_written: int
    merges: int
    block_count: int
    vector_count: int
    diagnostics_hash: Optional[str]
    events_emitted: List[str]
    latency_ms: int
    dedup_hit: bool = False
    raw_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for API response."""
        return {
            "status": self.status,
            "packet_hash": self.packet_hash,
            "graph_version": self.graph_version,
            "nodes_written": self.nodes_written,
            "merges": self.merges,
            "block_count": self.block_count,
            "vector_count": self.vector_count,
            "diagnostics_hash": self.diagnostics_hash,
            "events_emitted": self.events_emitted,
            "latency_ms": self.latency_ms,
            "dedup_hit": self.dedup_hit,
            "raw_id": self.raw_id,
            "error": self.error,
        }


# =============================================================================
# Event Emission (for UI timeline)
# =============================================================================


def _parse_uuid_or_none(value: Optional[str]) -> Optional[UUID]:
    """Parse UUID value safely for DB models that require UUID type."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return UUID(text)
    except (ValueError, TypeError, AttributeError):
        return None


def _emit_event(
    event_type: str,
    graph_id: str,
    payload: Dict[str, Any],
    event_repo: Optional[Any] = None,
    session: Optional[Any] = None,
) -> None:
    """Emit event for UI/API consumption.

    Events are the primary way to build an "alive" UI timeline.
    """
    datetime.now(timezone.utc).isoformat()

    logger.info(f"[Event] {event_type}: {payload}")

    if event_repo is not None and session is not None:
        try:
            event_repo.emit(session, graph_id, event_type, payload)
        except Exception as e:
            logger.warning(f"Failed to persist event: {e}")


# =============================================================================
# Main Ingest Function
# =============================================================================


def run_ingest(
    graph_id: str,
    raw_id: str,
    filename: str,
    file_bytes: bytes,
    *,
    tenant_id: str = "default",
    session: Optional[Any] = None,
    persist_mode: Union[PersistMode, str] = PersistMode.RELAXED,
    profile: Union[FAIMProfile, str] = FAIMProfile.STRICT,
    node_repo: Optional[Any] = None,
    edge_repo: Optional[Any] = None,
    event_repo: Optional[Any] = None,
    gv_repo: Optional[Any] = None,
) -> IngestResult:
    """Run the FAIM-native ingest pipeline.

    This is the SINGLE entry point for ingesting files into FAIM.

    Pipeline (exactly this order):
    1. blocks = perception.router.route_extraction(file_bytes, filename, raw_id)
    2. packet = perception.packetize.create_packet(raw_id, blocks)
    3. perception.validate.assert_valid(packet, blocks)
    4. vectors = encoding.encode_packet(packet, blocks, profile=...)
    5. engine = core.engine.FAIMNativeEngine(...)
    6. write_result = engine.write_atoms(graph_id, vectors, raw_id, packet_hash)

    Args:
        graph_id: Target graph identifier.
        raw_id: Raw file identifier (from RawStore).
        filename: Original filename.
        file_bytes: Raw file content.
        persist_mode: STRICT (wait for commit) or RELAXED (async).
        profile: STRICT (deterministic) or FAST (may use GPU).
        node_repo: Node repository (optional, will create default if None).
        edge_repo: Edge repository (optional).
        event_repo: Event repository for logging.
        gv_repo: Graph version repository.

    Returns:
        IngestResult with packet_hash as idempotency key.

    Important:
        packet_hash is the idempotency key: repeated ingest with same
        content will not create duplicate nodes.
    """
    start_time = time.time()
    events_emitted: List[str] = []
    raw_id = str(raw_id or "").strip()

    # Normalize profile
    if isinstance(profile, str):
        profile = FAIMProfile(profile.lower())
    if isinstance(persist_mode, str):
        persist_mode = PersistMode(persist_mode.lower())

    logger.info(
        f"[Ingest] Starting: {filename} → graph={graph_id}, profile={profile.value}"
    )

    try:
        if not raw_id:
            raise ValueError("raw_id is required and cannot be empty")

        # =====================================================================
        # STEP 0: Emit INGEST_START
        # =====================================================================
        _emit_event(
            "INGEST_START",
            graph_id,
            {
                "raw_id": raw_id,
                "filename": filename,
                "file_size": len(file_bytes),
                "profile": profile.value,
                "persist_mode": persist_mode.value,
            },
            event_repo,
            session=session,
        )
        events_emitted.append("INGEST_START")

        # =====================================================================
        # STEP 1: Extract EvidenceBlocks (NO CHUNKING!)
        # =====================================================================
        from perception.router import route_extraction

        blocks = route_extraction(file_bytes, filename, raw_id)

        if not blocks:
            return IngestResult(
                status="error",
                packet_hash="",
                graph_version=0,
                nodes_written=0,
                merges=0,
                block_count=0,
                vector_count=0,
                diagnostics_hash=None,
                events_emitted=events_emitted,
                latency_ms=int((time.time() - start_time) * 1000),
                error="No blocks extracted from file",
            )

        logger.info(f"[Ingest] Extracted {len(blocks)} EvidenceBlocks")

        # =====================================================================
        # STEP 2: Create MemoryPacket with hash (idempotency key)
        # =====================================================================
        from perception.packetize import create_packet

        packet = create_packet(raw_id, blocks)
        packet_hash = packet.packet_hash

        _emit_event(
            "PACKET_CREATED",
            graph_id,
            {
                "raw_id": raw_id,
                "packet_hash": packet_hash,
                "block_count": len(blocks),
            },
            event_repo,
            session=session,
        )
        events_emitted.append("PACKET_CREATED")

        logger.info(f"[Ingest] Packet created: hash={packet_hash[:16]}...")

        # =====================================================================
        # STEP 2.5: DEDUP CHECK (Stage-9 idempotency)
        # =====================================================================
        if session is not None:
            try:
                from store.pg.models_faim import IngestDedupModel

                existing = IngestDedupModel.check_exists(
                    session, tenant_id, graph_id, packet_hash
                )
                if existing:
                    # Already processed - return cached result
                    _emit_event(
                        "INGEST_DEDUP_HIT",
                        graph_id,
                        {
                            "packet_hash": packet_hash,
                            "original_raw_id": (
                                str(existing.raw_id) if existing.raw_id else None
                            ),
                            "original_node_count": existing.node_count,
                        },
                        event_repo,
                        session=session,
                    )
                    events_emitted.append("INGEST_DEDUP_HIT")

                    logger.info(
                        "[Ingest] DEDUP HIT: packet already processed, returning cached result"
                    )

                    return IngestResult(
                        status="dedup_hit",
                        packet_hash=packet_hash,
                        graph_version=0,  # Not re-computed
                        nodes_written=0,
                        merges=0,
                        block_count=len(blocks),
                        vector_count=0,
                        diagnostics_hash=None,
                        events_emitted=events_emitted,
                        latency_ms=int((time.time() - start_time) * 1000),
                        dedup_hit=True,
                        raw_id=str(existing.raw_id) if existing.raw_id else raw_id,
                    )
            except Exception as e:
                logger.warning(f"[Ingest] Dedup check failed (continuing): {e}")

        # =====================================================================
        # STEP 3: Validate packet + blocks
        # =====================================================================
        from perception.validate import assert_valid

        assert_valid(packet, blocks)
        logger.info("[Ingest] Packet validation passed")

        # =====================================================================
        # STEP 4: Encode blocks to vectors (256 dim, NO ML)
        # =====================================================================
        from encoding import vectorize_blocks
        from encoding.vector_schema import VECTOR_DIMENSION

        vectors = vectorize_blocks(blocks)

        # Verify dimension
        if vectors and len(vectors[0].v_native) != VECTOR_DIMENSION:
            raise ValueError(
                f"Vector dimension mismatch: got {len(vectors[0].v_native)}, "
                f"expected {VECTOR_DIMENSION}"
            )

        _emit_event(
            "ENCODED",
            graph_id,
            {
                "packet_hash": packet_hash,
                "vector_count": len(vectors),
                "vector_dim": VECTOR_DIMENSION,
            },
            event_repo,
            session=session,
        )
        events_emitted.append("ENCODED")

        logger.info(f"[Ingest] Encoded {len(vectors)} vectors ({VECTOR_DIMENSION} dim)")

        # =====================================================================
        # STEP 5: Write atoms to graph via FAIM-native engine
        # =====================================================================
        from core.engine import FAIMNativeEngine

        engine = FAIMNativeEngine(
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            graph_version_repo=gv_repo,
        )

        write_result = engine.write_atoms(
            graph_id=graph_id,
            vectors=vectors,
            raw_id=raw_id,
            packet_hash=packet_hash,
        )

        _emit_event(
            "WRITE_ATOMS_DONE",
            graph_id,
            {
                "packet_hash": packet_hash,
                "nodes_written": write_result.nodes_written,
                "merges": write_result.merges,
                "graph_version": write_result.graph_version,
            },
            event_repo,
            session=session,
        )
        events_emitted.append("WRITE_ATOMS_DONE")

        logger.info(
            f"[Ingest] Write complete: {write_result.nodes_written} nodes, "
            f"{write_result.merges} merges, version={write_result.graph_version}"
        )

        # =====================================================================
        # STEP 5b: Index upsert (STRICT mode disabled)
        # =====================================================================
        # Index is acceleration only, never affects truth
        # STRICT mode = deterministic, so skip index writes
        index_enabled = profile != FAIMProfile.STRICT

        if index_enabled and vectors:
            try:
                from uuid import UUID

                from index.qdrant_index import FAIMIndex

                # Get project_id from node_repo or use a default
                project_id = getattr(node_repo, "project_id", None)
                if project_id is None:
                    # Use graph_id as project_id fallback
                    try:
                        project_id = UUID(graph_id)
                    except (ValueError, TypeError):
                        project_id = UUID("00000000-0000-0000-0000-000000000000")

                index = FAIMIndex(project_id)

                # WriteResult carries canonical node UUIDs in the same order as vectors.
                node_ids = [str(nid) for nid in (write_result.node_ids or [])]
                for idx, vector in enumerate(vectors):
                    if idx < len(node_ids):
                        node_id = node_ids[idx]
                    else:
                        # Defensive fallback if engine contract changes.
                        node_id = str(getattr(vector, "node_id", "") or vector.vector_hash)
                    index.add(
                        graph_id=graph_id,
                        node_id=node_id,
                        vector=vector.v_native,
                        level=0,
                        kind="atom",
                    )

                _emit_event(
                    "INDEX_UPSERTED",
                    graph_id,
                    {
                        "vector_count": len(vectors),
                        "profile": profile.value,
                    },
                    event_repo,
                )
                events_emitted.append("INDEX_UPSERTED")
                logger.info(f"[Ingest] Indexed {len(vectors)} vectors")

            except Exception as e:
                # Index failures are non-fatal (acceleration only)
                logger.warning(f"[Ingest] Index upsert failed (non-fatal): {e}")
        elif profile == FAIMProfile.STRICT:
            logger.info("[Ingest] STRICT mode: skipping index writes")

        # =====================================================================
        # STEP 6: Build result
        # =====================================================================
        latency_ms = int((time.time() - start_time) * 1000)

        # Record successful ingest for future dedup (Stage-9)
        if session is not None:
            try:
                from store.pg.models_faim import IngestDedupModel

                IngestDedupModel.record_ingest(
                    session=session,
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    packet_hash=packet_hash,
                    raw_id=_parse_uuid_or_none(raw_id),
                    node_count=write_result.nodes_written,
                )
                logger.info("[Ingest] Recorded in dedup table for future retry safety")
            except Exception as e:
                logger.warning(f"[Ingest] Failed to record dedup (non-fatal): {e}")

        return IngestResult(
            status="completed",
            packet_hash=packet_hash,
            graph_version=write_result.graph_version,
            nodes_written=write_result.nodes_written,
            merges=write_result.merges,
            block_count=len(blocks),
            vector_count=len(vectors),
            diagnostics_hash=getattr(write_result, "diagnostics_hash", None),
            events_emitted=events_emitted,
            latency_ms=latency_ms,
            dedup_hit=False,
            raw_id=raw_id,
        )

    except Exception as e:
        logger.error(f"[Ingest] Error: {e}")
        latency_ms = int((time.time() - start_time) * 1000)

        _emit_event(
            "INGEST_ERROR",
            graph_id,
            {
                "raw_id": raw_id,
                "error": str(e),
            },
            event_repo,
            session=session,
        )
        events_emitted.append("INGEST_ERROR")

        return IngestResult(
            status="error",
            packet_hash="",
            graph_version=0,
            nodes_written=0,
            merges=0,
            block_count=0,
            vector_count=0,
            diagnostics_hash=None,
            events_emitted=events_emitted,
            latency_ms=latency_ms,
            error=str(e),
        )


# =============================================================================
# Idempotency Check
# =============================================================================


def check_idempotency(
    graph_id: str,
    packet_hash: str,
    event_repo: Optional[Any] = None,
) -> bool:
    """Check if packet_hash was already ingested.

    Uses event log to check for existing WRITE_ATOMS_DONE with same packet_hash.

    Returns:
        True if already ingested, False otherwise.
    """
    if event_repo is None:
        return False

    try:
        events = event_repo.get_all(graph_id)
        for event in events:
            if event.get("type") == "WRITE_ATOMS_DONE":
                if event.get("payload", {}).get("packet_hash") == packet_hash:
                    return True
        return False
    except Exception:
        return False


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "PersistMode",
    "FAIMProfile",
    "IngestResult",
    "run_ingest",
    "check_idempotency",
]
