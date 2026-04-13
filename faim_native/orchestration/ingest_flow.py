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
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from orchestration.profile_persist_policy import (
    PolicyOperation,
    resolve_profile_persist_policy,
)

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
        phase_latency_ms: Per-phase latency breakdown in milliseconds
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
    phase_latency_ms: Dict[str, int] = field(default_factory=dict)
    requested_profile: str = "strict"
    requested_persist_mode: str = "relaxed"
    effective_profile: str = "strict"
    effective_persist_mode: str = "relaxed"
    durability_path: str = "core_sync_secondary_async"
    index_write_mode: str = "skipped"
    secondary_task_status: str = "not_required"
    secondary_task_job_id: Optional[str] = None

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
            "phase_latency_ms": self.phase_latency_ms,
            "requested_profile": self.requested_profile,
            "requested_persist_mode": self.requested_persist_mode,
            "effective_profile": self.effective_profile,
            "effective_persist_mode": self.effective_persist_mode,
            "durability_path": self.durability_path,
            "index_write_mode": self.index_write_mode,
            "secondary_task_status": self.secondary_task_status,
            "secondary_task_job_id": self.secondary_task_job_id,
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


def _jobs_enabled() -> bool:
    """Read FAIM_ENABLE_JOBS in a runtime-safe way."""
    raw = os.getenv("FAIM_ENABLE_JOBS", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _project_id_from_graph_or_default(graph_id: str, fallback: Optional[Any] = None) -> UUID:
    """Resolve project UUID for index partitioning."""
    if fallback is not None:
        try:
            return UUID(str(fallback))
        except (ValueError, TypeError, AttributeError):
            pass
    try:
        return UUID(str(graph_id))
    except (ValueError, TypeError, AttributeError):
        return UUID("00000000-0000-0000-0000-000000000000")


def _upsert_index_sync(
    *,
    graph_id: str,
    vectors: List[Any],
    write_result: Any,
    node_repo: Optional[Any],
) -> int:
    """Synchronous index upsert path used by strict durability mode."""
    from index.qdrant_index import FAIMIndex

    project_id = _project_id_from_graph_or_default(
        graph_id=graph_id,
        fallback=getattr(node_repo, "project_id", None),
    )
    index = FAIMIndex(project_id)

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
    return len(vectors)


def _enqueue_async_index_upsert_job(
    *,
    session: Any,
    tenant_id: str,
    graph_id: str,
    raw_id: str,
    packet_hash: str,
    node_ids: List[str],
    requested_profile: str,
    requested_persist_mode: str,
    effective_profile: str,
    effective_persist_mode: str,
    durability_path: str,
) -> str:
    """Queue index upsert for worker execution (relaxed persist mode)."""
    from store.pg.models_faim import JobModel

    job_id = uuid4()
    job = JobModel(
        job_id=job_id,
        tenant_id=tenant_id,
        graph_id=graph_id,
        kind="ingest_secondary_index",
        payload_json={
            "raw_id": raw_id,
            "packet_hash": packet_hash,
            "node_ids": node_ids,
            "requested_profile": requested_profile,
            "requested_persist_mode": requested_persist_mode,
            "effective_profile": effective_profile,
            "effective_persist_mode": effective_persist_mode,
            "durability_path": durability_path,
            "source": "ingest_secondary_index",
        },
        status="pending",
    )
    session.add(job)
    session.flush()
    return str(job_id)


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
    perf_start = time.perf_counter()
    events_emitted: List[str] = []
    phase_latency_ms: Dict[str, int] = {}
    raw_id = str(raw_id or "").strip()

    def _finish_phase(phase: str, started_at: float) -> None:
        phase_latency_ms[phase] = int((time.perf_counter() - started_at) * 1000)

    # Normalize requested values
    if isinstance(profile, str):
        profile = FAIMProfile(profile.lower())
    if isinstance(persist_mode, str):
        persist_mode = PersistMode(persist_mode.lower())
    requested_profile = profile
    requested_persist_mode = persist_mode
    policy = resolve_profile_persist_policy(
        operation=PolicyOperation.INGEST,
        requested_profile=requested_profile.value,
        requested_persist_mode=requested_persist_mode.value,
    )
    effective_profile = FAIMProfile(policy.effective_profile)
    effective_persist_mode = PersistMode(policy.effective_persist_mode)

    logger.info(
        "[Ingest] Starting: %s → graph=%s, requested=%s/%s effective=%s/%s compat=%s",
        filename,
        graph_id,
        requested_profile.value,
        requested_persist_mode.value,
        effective_profile.value,
        effective_persist_mode.value,
        policy.compatibility_mode,
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
                "profile": requested_profile.value,
                "persist_mode": requested_persist_mode.value,
                "requested_profile": requested_profile.value,
                "requested_persist_mode": requested_persist_mode.value,
                "effective_profile": effective_profile.value,
                "effective_persist_mode": effective_persist_mode.value,
                "durability_path": policy.durability_path,
                "profile_persist_compat_mode": policy.compatibility_mode,
                "profile_persist_coercion_reason": policy.coercion_reason,
            },
            event_repo,
            session=session,
        )
        events_emitted.append("INGEST_START")

        # =====================================================================
        # STEP 1: Extract EvidenceBlocks (NO CHUNKING!)
        # =====================================================================
        from perception.router import route_extraction

        phase_started = time.perf_counter()
        blocks = route_extraction(file_bytes, filename, raw_id)
        _finish_phase("extract", phase_started)

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
                phase_latency_ms=phase_latency_ms,
            )

        logger.info(f"[Ingest] Extracted {len(blocks)} EvidenceBlocks")

        # =====================================================================
        # STEP 2: Create MemoryPacket with hash (idempotency key)
        # =====================================================================
        from perception.packetize import create_packet

        phase_started = time.perf_counter()
        packet = create_packet(raw_id, blocks)
        _finish_phase("packetize", phase_started)
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
        phase_started = time.perf_counter()
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

                    total_latency_ms = int((time.perf_counter() - perf_start) * 1000)
                    _emit_event(
                        "INGEST_PHASE_LATENCY",
                        graph_id,
                        {
                            "raw_id": raw_id,
                            "packet_hash": packet_hash,
                            "status": "dedup_hit",
                            "phase_latency_ms": phase_latency_ms,
                            "latency_ms": total_latency_ms,
                        },
                        event_repo,
                        session=session,
                    )
                    events_emitted.append("INGEST_PHASE_LATENCY")

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
                        phase_latency_ms=phase_latency_ms,
                        requested_profile=requested_profile.value,
                        requested_persist_mode=requested_persist_mode.value,
                        effective_profile=effective_profile.value,
                        effective_persist_mode=effective_persist_mode.value,
                        durability_path=policy.durability_path,
                        index_write_mode="dedup_hit",
                        secondary_task_status="dedup_hit",
                    )
            except Exception as e:
                logger.warning(f"[Ingest] Dedup check failed (continuing): {e}")
        _finish_phase("dedup_check", phase_started)

        # =====================================================================
        # STEP 3: Validate packet + blocks
        # =====================================================================
        from perception.validate import assert_valid

        phase_started = time.perf_counter()
        assert_valid(packet, blocks)
        _finish_phase("validate", phase_started)
        logger.info("[Ingest] Packet validation passed")

        # =====================================================================
        # STEP 4: Encode blocks to vectors (256 dim, NO ML)
        # =====================================================================
        from encoding import vectorize_blocks
        from encoding.vector_schema import VECTOR_DIMENSION

        phase_started = time.perf_counter()
        vectors = vectorize_blocks(blocks)
        from encoding.representation_v2 import build_representation_v2_for_block

        reprs_v2 = []
        for block in blocks:
            if all(hasattr(block, attr) for attr in ("content", "anchor", "block_type")):
                reprs_v2.append(build_representation_v2_for_block(block))
            else:
                # Compatibility path for unit tests that stub non-EvidenceBlock
                # placeholders through the ingest pipeline.
                reprs_v2.append(None)
        _finish_phase("encode", phase_started)

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

        phase_started = time.perf_counter()
        write_result = engine.write_atoms(
            graph_id=graph_id,
            vectors=vectors,
            raw_id=raw_id,
            packet_hash=packet_hash,
            reprs_v2=reprs_v2,
        )
        _finish_phase("write", phase_started)

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
        # STEP 5b: Secondary durability path (index acceleration)
        # =====================================================================
        # Index is acceleration only, never affects canonical graph truth.
        # Phase R3:
        # - compat_mode=True keeps legacy behavior
        # - compat_mode=False applies strict/relaxed durability path
        index_enabled = bool(policy.index_enabled)
        index_write_mode = "skipped"
        secondary_task_status = "not_required"
        secondary_task_job_id: Optional[str] = None

        if index_enabled and vectors:
            if policy.compatibility_mode:
                # Legacy behavior for compatibility rollout safety.
                try:
                    phase_started = time.perf_counter()
                    indexed_count = _upsert_index_sync(
                        graph_id=graph_id,
                        vectors=vectors,
                        write_result=write_result,
                        node_repo=node_repo,
                    )
                    _emit_event(
                        "INDEX_UPSERTED",
                        graph_id,
                        {
                            "vector_count": indexed_count,
                            "profile": requested_profile.value,
                            "effective_profile": effective_profile.value,
                            "effective_persist_mode": effective_persist_mode.value,
                            "durability_path": policy.durability_path,
                            "index_write_mode": "sync_inline_compat",
                            "profile_persist_compat_mode": True,
                        },
                        event_repo,
                        session=session,
                    )
                    events_emitted.append("INDEX_UPSERTED")
                    _finish_phase("index_sync", phase_started)
                    index_write_mode = "sync_inline_compat"
                    secondary_task_status = "completed_sync"
                    logger.info("[Ingest] Indexed %d vectors (compat mode)", indexed_count)
                except Exception as e:
                    # Index failures are non-fatal in compatibility mode.
                    logger.warning(f"[Ingest] Index upsert failed (compat, non-fatal): {e}")
                    index_write_mode = "sync_inline_compat_failed_nonfatal"
                    secondary_task_status = "sync_failed_nonfatal"
            elif effective_persist_mode == PersistMode.STRICT:
                # Strict durability path: synchronous secondary completion.
                phase_started = time.perf_counter()
                indexed_count = _upsert_index_sync(
                    graph_id=graph_id,
                    vectors=vectors,
                    write_result=write_result,
                    node_repo=node_repo,
                )
                _finish_phase("index_sync", phase_started)
                _emit_event(
                    "INDEX_UPSERTED",
                    graph_id,
                    {
                        "vector_count": indexed_count,
                        "profile": requested_profile.value,
                        "effective_profile": effective_profile.value,
                        "effective_persist_mode": effective_persist_mode.value,
                        "durability_path": policy.durability_path,
                        "index_write_mode": "sync_inline",
                        "profile_persist_compat_mode": False,
                    },
                    event_repo,
                    session=session,
                )
                events_emitted.append("INDEX_UPSERTED")
                index_write_mode = "sync_inline"
                secondary_task_status = "completed_sync"
                logger.info("[Ingest] Indexed %d vectors (strict durability)", indexed_count)
            else:
                # Relaxed durability path: queue secondary index work when jobs are enabled.
                if _jobs_enabled() and session is not None:
                    phase_started = time.perf_counter()
                    node_ids = [str(nid) for nid in (write_result.node_ids or [])]
                    secondary_task_job_id = _enqueue_async_index_upsert_job(
                        session=session,
                        tenant_id=tenant_id,
                        graph_id=graph_id,
                        raw_id=raw_id,
                        packet_hash=packet_hash,
                        node_ids=node_ids,
                        requested_profile=requested_profile.value,
                        requested_persist_mode=requested_persist_mode.value,
                        effective_profile=effective_profile.value,
                        effective_persist_mode=effective_persist_mode.value,
                        durability_path=policy.durability_path,
                    )
                    _finish_phase("index_queue", phase_started)
                    _emit_event(
                        "INDEX_UPSERT_QUEUED",
                        graph_id,
                        {
                            "vector_count": len(vectors),
                            "node_count": len(node_ids),
                            "profile": requested_profile.value,
                            "effective_profile": effective_profile.value,
                            "effective_persist_mode": effective_persist_mode.value,
                            "durability_path": policy.durability_path,
                            "index_write_mode": "async_queued",
                            "secondary_task_job_id": secondary_task_job_id,
                            "profile_persist_compat_mode": False,
                        },
                        event_repo,
                        session=session,
                    )
                    events_emitted.append("INDEX_UPSERT_QUEUED")
                    index_write_mode = "async_queued"
                    secondary_task_status = "queued"
                    logger.info(
                        "[Ingest] Queued async index upsert job=%s vectors=%d",
                        secondary_task_job_id,
                        len(vectors),
                    )
                else:
                    # Jobs unavailable: safe fallback to synchronous completion.
                    phase_started = time.perf_counter()
                    indexed_count = _upsert_index_sync(
                        graph_id=graph_id,
                        vectors=vectors,
                        write_result=write_result,
                        node_repo=node_repo,
                    )
                    _finish_phase("index_sync_fallback", phase_started)
                    _emit_event(
                        "INDEX_UPSERTED",
                        graph_id,
                        {
                            "vector_count": indexed_count,
                            "profile": requested_profile.value,
                            "effective_profile": effective_profile.value,
                            "effective_persist_mode": effective_persist_mode.value,
                            "durability_path": policy.durability_path,
                            "index_write_mode": "sync_fallback_no_jobs",
                            "fallback_reason": "jobs_disabled_or_session_missing",
                            "profile_persist_compat_mode": False,
                        },
                        event_repo,
                        session=session,
                    )
                    events_emitted.append("INDEX_UPSERTED")
                    index_write_mode = "sync_fallback_no_jobs"
                    secondary_task_status = "completed_sync_fallback"
                    logger.info(
                        "[Ingest] Jobs unavailable; indexed %d vectors synchronously",
                        indexed_count,
                    )
        elif effective_profile == FAIMProfile.STRICT:
            logger.info("[Ingest] STRICT mode: skipping index writes")
            index_write_mode = "skipped_profile_strict"
            secondary_task_status = "skipped_profile_strict"
            _emit_event(
                "INDEX_UPSERT_SKIPPED",
                graph_id,
                {
                    "reason": "profile_strict",
                    "profile": requested_profile.value,
                    "effective_profile": effective_profile.value,
                    "effective_persist_mode": effective_persist_mode.value,
                    "durability_path": policy.durability_path,
                    "index_write_mode": index_write_mode,
                },
                event_repo,
                session=session,
            )
            events_emitted.append("INDEX_UPSERT_SKIPPED")
        else:
            index_write_mode = "skipped_no_vectors"
            secondary_task_status = "skipped_no_vectors"

        # =====================================================================
        # STEP 6: Build result
        # =====================================================================
        latency_ms = int((time.time() - start_time) * 1000)
        total_latency_ms = int((time.perf_counter() - perf_start) * 1000)

        # Record successful ingest for future dedup (Stage-9)
        if session is not None:
            try:
                from store.pg.models_faim import IngestDedupModel

                phase_started = time.perf_counter()
                IngestDedupModel.record_ingest(
                    session=session,
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    packet_hash=packet_hash,
                    raw_id=_parse_uuid_or_none(raw_id),
                    node_count=write_result.nodes_written,
                )
                _finish_phase("dedup_record", phase_started)
                logger.info("[Ingest] Recorded in dedup table for future retry safety")
            except Exception as e:
                logger.warning(f"[Ingest] Failed to record dedup (non-fatal): {e}")

        _emit_event(
            "INGEST_PHASE_LATENCY",
            graph_id,
            {
                "raw_id": raw_id,
                "packet_hash": packet_hash,
                "status": "completed",
                "phase_latency_ms": phase_latency_ms,
                "latency_ms": total_latency_ms,
            },
            event_repo,
            session=session,
        )
        events_emitted.append("INGEST_PHASE_LATENCY")

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
            phase_latency_ms=phase_latency_ms,
            requested_profile=requested_profile.value,
            requested_persist_mode=requested_persist_mode.value,
            effective_profile=effective_profile.value,
            effective_persist_mode=effective_persist_mode.value,
            durability_path=policy.durability_path,
            index_write_mode=index_write_mode,
            secondary_task_status=secondary_task_status,
            secondary_task_job_id=secondary_task_job_id,
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

        total_latency_ms = int((time.perf_counter() - perf_start) * 1000)
        _emit_event(
            "INGEST_PHASE_LATENCY",
            graph_id,
            {
                "raw_id": raw_id,
                "status": "error",
                "phase_latency_ms": phase_latency_ms,
                "latency_ms": total_latency_ms,
                "error": str(e),
            },
            event_repo,
            session=session,
        )
        events_emitted.append("INGEST_PHASE_LATENCY")

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
            phase_latency_ms=phase_latency_ms,
            requested_profile=requested_profile.value,
            requested_persist_mode=requested_persist_mode.value,
            effective_profile=effective_profile.value,
            effective_persist_mode=effective_persist_mode.value,
            durability_path=policy.durability_path,
            index_write_mode="error",
            secondary_task_status="error",
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
