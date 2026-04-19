"""FAIM-Native API: Storage Router (P1).

Provides storage upload/catalog APIs used by Storage UI.
"""

from __future__ import annotations

import logging
import io
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, text

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context  # noqa: E402
from api.validators import (  # noqa: E402
    sanitize_filename,
    validate_content_type,
    validate_file_extension,
    validate_mime_extension_match,
    validate_upload_file,
    validate_upload_size,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storage", tags=["storage"])


# =============================================================================
# Response Models
# =============================================================================


class StorageFileItem(BaseModel):
    """Storage file item for catalog and detail views."""

    raw_id: str
    graph_id: str
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    ingest_status: str
    packet_hash: Optional[str] = None
    node_count: int = 0
    vector_count: int = 0
    error: Optional[str] = None
    uploaded_at: Optional[str] = None
    ingested_at: Optional[str] = None
    updated_at: Optional[str] = None
    delete_requested: bool = False


class UploadFileResult(BaseModel):
    """Per-file upload result in upload batch response."""

    filename: str
    status: str
    raw_id: Optional[str] = None
    packet_hash: Optional[str] = None
    node_count: int = 0
    vector_count: int = 0
    error: Optional[str] = None
    requested_profile: Optional[str] = None
    requested_persist_mode: Optional[str] = None
    requested_extractor_mode: Optional[str] = None
    effective_profile: Optional[str] = None
    effective_persist_mode: Optional[str] = None
    effective_extractor_mode: Optional[str] = None
    durability_path: Optional[str] = None


class StorageUploadBatchResponse(BaseModel):
    """Batch upload response."""

    job_id: str
    graph_id: str
    status: str
    requested_files: int
    processed_files: int
    success_files: int
    failed_files: int
    dedup_hits: int
    cancelled_files: int = 0
    files: List[UploadFileResult]
    requested_profile: Optional[str] = None
    requested_persist_mode: Optional[str] = None
    requested_extractor_mode: Optional[str] = None
    effective_profile: Optional[str] = None
    effective_persist_mode: Optional[str] = None
    effective_extractor_mode: Optional[str] = None
    durability_path: Optional[str] = None


class StorageUploadStatusResponse(BaseModel):
    """Upload status and progress response."""

    job_id: str
    graph_id: str
    status: str
    requested_files: int
    processed_files: int
    success_files: int
    failed_files: int
    dedup_hits: int
    cancelled_files: int = 0
    cancel_requested: bool = False
    cancel_reason: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    files: List[StorageFileItem]
    requested_profile: Optional[str] = None
    requested_persist_mode: Optional[str] = None
    requested_extractor_mode: Optional[str] = None
    effective_profile: Optional[str] = None
    effective_persist_mode: Optional[str] = None
    effective_extractor_mode: Optional[str] = None
    durability_path: Optional[str] = None


class StorageJobEvent(BaseModel):
    """Event entry for a storage upload job."""

    seq: int
    kind: str
    ts: Optional[str] = None
    payload: Dict[str, Any]


class StorageJobEventsResponse(BaseModel):
    """Job events response."""

    job_id: str
    events: List[StorageJobEvent]


class StorageFileListResponse(BaseModel):
    """File catalog response."""

    items: List[StorageFileItem]
    total: int
    limit: int
    offset: int


class StorageSummaryResponse(BaseModel):
    """Storage summary response."""

    graph_id: Optional[str] = None
    total_files: int
    total_bytes: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]


class StorageBackendsHealth(BaseModel):
    """Storage backend health response."""

    postgres: bool
    redis: bool
    qdrant: bool
    raw_store: bool


class StorageSupportedTypesResponse(BaseModel):
    """Supported upload and extraction file coverage for Storage UI."""

    max_upload_size_bytes: int
    max_upload_size_mb: float
    total_extensions: int
    total_content_types: int
    extensions: List[str]
    content_types: List[str]
    categories: Dict[str, List[str]]
    extractor_doc_types: Dict[str, int]
    ocr_enabled: bool
    ocr_engine: str
    ocr_fail_closed: bool
    ocr_capable_extensions: List[str]


class StorageMaintenanceHistoryItem(BaseModel):
    """Summary of a maintenance action run for a graph."""

    seq: int
    kind: str
    ts: Optional[str] = None
    status: str
    summary: str
    graph_version: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class StorageMaintenanceHistoryResponse(BaseModel):
    """Recent storage maintenance action history."""

    graph_id: str
    total: int
    items: List[StorageMaintenanceHistoryItem]


class StorageBackendState(BaseModel):
    """Operational backend health state with latency and status."""

    ok: bool
    status: str  # up | degraded | down
    latency_ms: int
    error: Optional[str] = None


class StoragePhaseLatencyStats(BaseModel):
    """Aggregate latency metrics for a pipeline phase."""

    count: int
    avg_ms: float
    p95_ms: float
    max_ms: int


class StorageOpsMetricsResponse(BaseModel):
    """Storage observability and operations metrics."""

    graph_id: Optional[str] = None
    window_seconds: int
    generated_at: str
    upload_count: int
    upload_bytes: int
    processed_files: int
    dedup_hits: int
    dedup_ratio: float
    failures_total: int
    failure_reasons: Dict[str, int]
    phase_latency_ms: Dict[str, StoragePhaseLatencyStats]
    backend_states: Dict[str, StorageBackendState]


class StorageIngestActionResponse(BaseModel):
    """Response for ingest/retry actions."""

    status: str
    file: StorageFileItem
    ingest: Dict[str, Any]


class StorageRepresentationBackfillResponse(BaseModel):
    """Graph-scoped Representation V2 backfill response."""

    status: str
    graph_id: str
    files_scanned: int
    files_loaded: int
    files_failed: int
    blocks_extracted: int
    matched_nodes: int
    inserted: int
    updated: int
    unchanged: int
    skipped_nodes: int
    graph_version: int
    errors: List[str] = Field(default_factory=list)


class StoragePruneResponse(BaseModel):
    """Cold-node pruning summary."""

    status: str
    graph_id: str
    dry_run: bool
    cold_age_days: int
    scanned: int
    pruned: int
    skipped_level: int
    skipped_touched: int
    graph_version: int


class StorageLongTermResponse(BaseModel):
    """Response for long-term flag toggle on a node."""

    status: str
    node_id: str
    graph_id: str
    long_term: bool


class StorageClusterResponse(BaseModel):
    """Response for k-means clustering run."""

    status: str
    graph_id: str
    k: int
    nodes_clustered: int
    iterations: int
    converged: bool
    cluster_sizes: Dict[str, int]
    graph_version: int


class StorageCanonicalSemanticsRebuildResponse(BaseModel):
    """Graph-scoped canonical semantics rebuild response."""

    status: str
    graph_id: str
    files_scanned: int
    files_loaded: int
    files_failed: int
    blocks_extracted: int
    matched_nodes: int
    term_stats_written: int
    lexicon_written: int
    edges_written: int
    graph_version: int
    errors: List[str] = Field(default_factory=list)


class StorageMultilingualSemanticsRebuildResponse(BaseModel):
    """Graph-scoped multilingual semantics rebuild response."""

    status: str
    graph_id: str
    files_scanned: int
    files_loaded: int
    files_failed: int
    blocks_extracted: int
    matched_nodes: int
    lexicon_written: int
    concept_nodes_written: int
    concept_edges_written: int
    graph_version: int
    errors: List[str] = Field(default_factory=list)


class StorageMultimodalBackfillResponse(BaseModel):
    """Graph-scoped multimodal sidecar rebuild response."""

    status: str
    graph_id: str
    files_scanned: int
    files_loaded: int
    files_failed: int
    blocks_extracted: int
    matched_nodes: int
    inserted: int
    updated: int
    unchanged: int
    graph_version: int
    errors: List[str] = Field(default_factory=list)


class StorageDomainProfileRebuildResponse(BaseModel):
    """Graph-scoped domain profile rebuild response."""

    status: str
    graph_id: str
    files_scanned: int
    files_loaded: int
    files_failed: int
    blocks_extracted: int
    matched_nodes: int
    lexicon_written: int
    graph_version: int
    errors: List[str] = Field(default_factory=list)


class StorageDomainKnowledgeImportRequest(BaseModel):
    """Offline graph-scoped domain knowledge import payload."""

    domain_pack: Optional[str] = None
    kb_rows: List[Dict[str, Any]] = Field(default_factory=list)


class StorageDomainKnowledgeImportResponse(BaseModel):
    """Graph-scoped domain knowledge import response."""

    status: str
    graph_id: str
    sources_written: int
    lexicon_written: int
    entity_nodes_written: int
    relation_nodes_written: int
    fact_nodes_written: int
    value_nodes_written: int
    time_nodes_written: int
    edges_written: int
    graph_version: int
    errors: List[str] = Field(default_factory=list)


class StorageUploadCancelResponse(BaseModel):
    """Response for upload cancellation request."""

    job_id: str
    status: str
    cancel_requested: bool
    cancel_reason: Optional[str] = None


class StorageProvenanceRawRef(BaseModel):
    """Raw reference details used in provenance inspect flow."""

    raw_id: str
    sha256: str
    uri: str
    mime_type: str
    size_bytes: int
    created_at: Optional[str] = None


class StorageProvenanceDedup(BaseModel):
    """Dedup linkage details for provenance."""

    packet_hash: Optional[str] = None
    dedup_record_found: bool = False
    dedup_raw_id: Optional[str] = None
    dedup_node_count: int = 0
    dedup_created_at: Optional[str] = None


class StorageProvenanceNode(BaseModel):
    """Minimal node summary for raw provenance."""

    node_id: str
    kind: str
    vector_hash: str
    block_id: Optional[str] = None
    created_at: Optional[str] = None


class StorageProvenanceEvent(BaseModel):
    """Minimal event summary for raw provenance."""

    seq: int
    kind: str
    ts: Optional[str] = None
    payload_keys: List[str]
    payload: Dict[str, Any] = Field(default_factory=dict)


class StorageProvenanceResponse(BaseModel):
    """Provenance inspect response for one raw file."""

    file: StorageFileItem
    raw_ref: Optional[StorageProvenanceRawRef] = None
    dedup: StorageProvenanceDedup
    node_count: int
    event_count: int
    nodes: List[StorageProvenanceNode]
    events: List[StorageProvenanceEvent]


class StorageRetentionRequest(BaseModel):
    """Retention execution request payload."""

    graph_id: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
    dry_run: bool = True
    irreversible: bool = False
    reason: Optional[str] = None


class StorageRetentionItem(BaseModel):
    """Per-item retention action result."""

    raw_id: str
    graph_id: str
    filename: str
    status: str
    detail: Optional[str] = None
    blob_deleted: bool = False
    raw_ref_deleted: bool = False


class StorageRetentionResponse(BaseModel):
    """Retention execution summary."""

    status: str
    dry_run: bool
    irreversible: bool
    scanned: int
    deleted: int
    skipped: int
    failed: int
    results: List[StorageRetentionItem]


class StorageRetentionJobResponse(BaseModel):
    """Retention job enqueue response."""

    job_id: str
    graph_id: str
    kind: str
    status: str


# =============================================================================
# Helpers
# =============================================================================


def _require_storage_repos(ctx: FAIMContext) -> None:
    if not ctx.session:
        raise HTTPException(status_code=500, detail="Database session unavailable")
    if not ctx.raw_repo:
        raise HTTPException(status_code=500, detail="Raw repository unavailable")
    if not ctx.storage_file_repo:
        raise HTTPException(status_code=500, detail="Storage repository unavailable")


def _parse_uuid(value: str, field_name: str = "id") -> UUID:
    try:
        return UUID(str(value).strip())
    except (ValueError, TypeError, AttributeError) as e:
        raise HTTPException(
            status_code=400, detail=f"{field_name} must be a valid UUID"
        ) from e


def _resolve_raw_store(ctx: FAIMContext):
    store = ctx.raw_store
    if store is not None:
        return store

    env = os.getenv("FAIM_ENV", "").strip().lower()
    if env in {"prod", "production"}:
        raise HTTPException(
            status_code=500,
            detail="Raw store is unavailable in production mode",
        )

    from store.raw.raw_store import RawStore

    fallback = Path(__file__).resolve().parents[2] / "store" / "raw" / "blobs"
    return RawStore(fallback)


def _storage_encryption_enabled() -> bool:
    mode = os.getenv("FAIM_PAYLOAD_CIPHER", "").strip().lower()
    if mode in {"fernet", "envelope"}:
        return True
    raw = os.getenv("FAIM_ENCRYPTION_AT_REST", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _normalize_extractor_mode(value: Optional[str]) -> str:
    return "faim_native"


def _maintenance_summary(kind: str, payload: Dict[str, Any]) -> str:
    kind = str(kind or "").strip().upper()
    if kind == "CANONICAL_SEMANTICS_REBUILD":
        return (
            "canonical rebuild "
            f"(files={payload.get('files_scanned', 0)}, "
            f"nodes={payload.get('matched_nodes', 0)}, "
            f"terms={payload.get('term_stats_written', 0)}, "
            f"edges={payload.get('edges_written', 0)})"
        )
    if kind == "MULTILINGUAL_SEMANTICS_REBUILD":
        return (
            "multilingual rebuild "
            f"(files={payload.get('files_scanned', 0)}, "
            f"nodes={payload.get('matched_nodes', 0)}, "
            f"concepts={payload.get('concept_nodes_written', 0)}, "
            f"edges={payload.get('concept_edges_written', 0)})"
        )
    if kind == "MULTIMODAL_BACKFILL":
        return (
            "multimodal backfill "
            f"(files={payload.get('files_scanned', 0)}, "
            f"matched={payload.get('matched_nodes', 0)}, "
            f"inserted={payload.get('inserted', 0)}, "
            f"updated={payload.get('updated', 0)})"
        )
    if kind == "DOMAIN_PROFILE_REBUILD":
        return (
            "domain profile rebuild "
            f"(files={payload.get('files_scanned', 0)}, "
            f"nodes={payload.get('matched_nodes', 0)}, "
            f"terms={payload.get('lexicon_written', 0)})"
        )
    if kind == "DOMAIN_KNOWLEDGE_IMPORT":
        return (
            "domain knowledge import "
            f"(sources={payload.get('sources_written', 0)}, "
            f"entities={payload.get('entity_nodes_written', 0)}, "
            f"facts={payload.get('fact_nodes_written', 0)}, "
            f"edges={payload.get('edges_written', 0)})"
        )
    return kind.lower().replace("_", " ")


def _emit_storage_audit_event(
    *,
    ctx: FAIMContext,
    graph_id: str,
    kind: str,
    payload: Dict[str, Any],
    commit: bool = False,
) -> None:
    if not ctx.event_repo or not ctx.session:
        return
    try:
        ctx.event_repo.emit(ctx.session, graph_id, kind, payload)
        if commit:
            ctx.session.commit()
        else:
            ctx.session.flush()
    except Exception as exc:  # nosec B110
        logger.warning("Failed to emit storage audit event %s: %s", kind, exc)


def _storage_lifecycle_log(
    *,
    ctx: FAIMContext,
    op: str,
    status: str,
    graph_id: Optional[str] = None,
    job_id: Optional[str] = None,
    raw_id: Optional[str] = None,
    failure_reason: Optional[str] = None,
    latency_ms: Optional[int] = None,
    detail: Optional[str] = None,
    level: str = "info",
) -> None:
    """Emit correlated structured lifecycle log for storage operations."""
    try:
        from runtime.feature_flags import get_feature_flags

        if not get_feature_flags().storage_structured_lifecycle_logs:
            return
    except Exception:
        # Logging should never fail business path.
        pass

    extra: Dict[str, Any] = {
        "request_id": ctx.request_id,
        "tenant_id": ctx.tenant_id,
        "graph_id": graph_id,
        "job_id": job_id,
        "raw_id": raw_id,
        "op": op,
        "status": status,
        "failure_reason": failure_reason,
    }
    if latency_ms is not None:
        extra["latency_ms"] = int(latency_ms)

    payload = {k: v for k, v in extra.items() if v is not None}
    message = detail or f"storage.lifecycle op={op} status={status}"

    log_fn = getattr(logger, level, logger.info)
    log_fn(message, extra=payload)


def _normalize_failure_reason(error: Optional[str]) -> str:
    """Map raw storage/ingest errors into a stable failure taxonomy."""
    text_value = str(error or "").strip().lower()
    if not text_value:
        return "unknown"
    if "cancel" in text_value:
        return "cancelled"
    if "mime" in text_value and "extension" in text_value:
        return "mime_extension_mismatch"
    if "upload file too large" in text_value or "file size exceeds" in text_value:
        return "upload_oversize"
    if "unsupported file extension" in text_value:
        return "unsupported_extension"
    if "filename cannot contain path separators" in text_value:
        return "path_traversal_filename"
    if "decrypt" in text_value or "encrypt" in text_value:
        return "encryption_error"
    if "raw blob not available" in text_value or "raw reference not found" in text_value:
        return "raw_unavailable"
    if "extract" in text_value:
        return "extract_error"
    if "vector" in text_value or "encode" in text_value:
        return "encode_error"
    if "qdrant" in text_value or "index" in text_value:
        return "index_error"
    if "uuid" in text_value or "raw_id" in text_value:
        return "raw_id_contract_error"
    return "ingest_error"


def _percentile(values: List[int], p: float) -> float:
    """Compute percentile using nearest-rank interpolation for observability."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * (p / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * weight)


def _probe_backend_state(name: str, probe_fn) -> StorageBackendState:
    """Measure backend availability + latency and derive health state."""
    started = time.perf_counter()
    error: Optional[str] = None
    ok = False
    try:
        ok = bool(probe_fn())
    except Exception as exc:  # nosec B110
        ok = False
        error = str(exc)[:240]
    latency_ms = int((time.perf_counter() - started) * 1000)
    if not ok:
        status = "down"
    elif latency_ms > 750:
        status = "degraded"
    else:
        status = "up"
    return StorageBackendState(ok=ok, status=status, latency_ms=latency_ms, error=error)


def _job_cancel_requested(ctx: FAIMContext, job_id: UUID) -> bool:
    from orchestration.jobs.job_store import JobStore

    return bool(JobStore.is_cancel_requested(ctx.session, job_id))


def _self_invent_after_upload_enabled() -> bool:
    try:
        from runtime.feature_flags import get_feature_flags

        flags = get_feature_flags()
        return bool(flags.self_invent_enabled and flags.self_invent_after_upload)
    except Exception:
        return False


def _enqueue_post_upload_evolve_job(
    *,
    ctx: FAIMContext,
    graph_id: str,
    upload_job_id: UUID,
) -> Optional[UUID]:
    """Optionally enqueue evolve job after successful upload ingestion."""
    if not _self_invent_after_upload_enabled():
        return None

    try:
        from orchestration.self_evolve_scheduler import enqueue_self_evolve_if_due

        result = enqueue_self_evolve_if_due(
            session=ctx.session,
            tenant_id=ctx.tenant_id,
            graph_id=graph_id,
            source="storage_upload",
            source_job_id=upload_job_id,
            request_id=ctx.request_id,
            profile="strict",
            persist_mode="relaxed",
            self_invent_requested=True,
        )
        return result.job_id
    except Exception as exc:  # nosec B110
        logger.warning("Failed shared self-evolve enqueue after upload: %s", exc)
        return None


def _row_to_file_item(row: Any) -> StorageFileItem:
    return StorageFileItem(
        raw_id=str(row.raw_id),
        graph_id=row.graph_id,
        filename=row.filename,
        mime_type=row.mime_type,
        size_bytes=int(row.size_bytes or 0),
        sha256=row.sha256,
        ingest_status=row.ingest_status,
        packet_hash=row.packet_hash,
        node_count=int(row.node_count or 0),
        vector_count=int(row.vector_count or 0),
        error=row.error_message,
        uploaded_at=row.uploaded_at.isoformat() if row.uploaded_at else None,
        ingested_at=row.ingested_at.isoformat() if row.ingested_at else None,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
        delete_requested=bool(row.delete_requested),
    )


def _store_raw_upload(
    *,
    ctx: FAIMContext,
    graph_id: str,
    file_bytes: bytes,
    mime_type: str,
) -> Any:
    """Persist raw bytes into immutable blob store + raw_refs."""
    store = _resolve_raw_store(ctx)
    raw_ref = store.store(file_bytes, mime_type=mime_type, graph_id=graph_id)
    return ctx.raw_repo.create(ctx.session, raw_ref)


def _run_ingest_existing_raw(
    *,
    ctx: FAIMContext,
    graph_id: str,
    raw_id: UUID,
    filename: str,
    file_bytes: bytes,
    profile: str,
    persist_mode: str,
    extractor_mode: str,
):
    """Execute ingest pipeline for existing persisted raw bytes."""
    from orchestration.ingest_flow import FAIMProfile, PersistMode, run_ingest

    try:
        profile_enum = FAIMProfile(profile.lower())
        persist_mode_enum = PersistMode(persist_mode.lower())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    result = run_ingest(
        graph_id=graph_id,
        raw_id=str(raw_id),
        filename=filename,
        file_bytes=file_bytes,
        profile=profile_enum,
        persist_mode=persist_mode_enum,
        extraction_settings={"extractor_mode": _normalize_extractor_mode(extractor_mode)},
        tenant_id=ctx.tenant_id,
        session=ctx.session,
        node_repo=ctx.node_repo,
        edge_repo=ctx.edge_repo,
        event_repo=ctx.event_repo,
        gv_repo=ctx.gv_repo,
    )
    return result


def _collect_backend_states(ctx: FAIMContext) -> Dict[str, StorageBackendState]:
    """Collect backend health states with per-check latency."""
    def _redis_probe() -> bool:
        from cache.query_cache import is_redis_available

        return bool(is_redis_available())

    def _qdrant_probe() -> bool:
        from index.qdrant_index import is_qdrant_available

        return bool(is_qdrant_available())

    states: Dict[str, StorageBackendState] = {}
    states["postgres"] = _probe_backend_state(
        "postgres",
        lambda: bool(ctx.session.execute(text("SELECT 1")).scalar() == 1),
    )
    states["raw_store"] = _probe_backend_state(
        "raw_store",
        lambda: bool(_resolve_raw_store(ctx).get_stats() is not None),
    )
    states["redis"] = _probe_backend_state(
        "redis",
        _redis_probe,
    )
    states["qdrant"] = _probe_backend_state(
        "qdrant",
        _qdrant_probe,
    )
    return states


# =============================================================================
# Upload + Jobs
# =============================================================================


@router.post("/uploads", response_model=StorageUploadBatchResponse)
async def create_upload_batch(
    graph_id: str = Form(...),
    profile: str = Form("strict"),
    persist_mode: str = Form("relaxed"),
    extractor_mode: str = Form("auto"),
    files: List[UploadFile] = File(...),  # noqa: B008
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageUploadBatchResponse:
    """Upload and ingest one or many files in a single batch."""
    _require_storage_repos(ctx)
    batch_started = time.perf_counter()

    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    from orchestration.jobs.job_store import JobStore
    from orchestration.profile_persist_policy import (
        PolicyOperation,
        resolve_profile_persist_policy,
    )

    requested_profile = str(profile or "").strip().lower()
    requested_persist_mode = str(persist_mode or "").strip().lower()
    requested_extractor_mode = _normalize_extractor_mode(extractor_mode)
    policy = resolve_profile_persist_policy(
        operation=PolicyOperation.INGEST,
        requested_profile=requested_profile,
        requested_persist_mode=requested_persist_mode,
    )

    requested_files = len(files)
    job_id = JobStore.enqueue(
        session=ctx.session,
        tenant_id=ctx.tenant_id,
        graph_id=graph_id,
        kind="storage_upload",
        payload={
            "requested_files": requested_files,
            "profile": profile,
            "persist_mode": persist_mode,
            "extractor_mode": requested_extractor_mode,
            "requested_profile": requested_profile,
            "requested_persist_mode": requested_persist_mode,
            "requested_extractor_mode": requested_extractor_mode,
            "effective_profile": policy.effective_profile,
            "effective_persist_mode": policy.effective_persist_mode,
            "effective_extractor_mode": requested_extractor_mode,
            "durability_path": policy.durability_path,
        },
    )

    file_results: List[UploadFileResult] = []
    processed = 0
    success = 0
    failed = 0
    dedup_hits = 0
    cancelled = 0
    cancel_triggered = False
    followup_evolve_job_id: Optional[str] = None
    _storage_lifecycle_log(
        ctx=ctx,
        op="upload_batch",
        status="started",
        graph_id=graph_id,
        job_id=str(job_id),
        detail=f"storage upload batch started ({requested_files} files)",
    )

    try:
        JobStore.append_event(
            ctx.session,
            job_id,
            "step_start",
            {
                "message": "Storage upload batch started",
                "requested_files": requested_files,
                "requested_extractor_mode": requested_extractor_mode,
            },
        )

        for index, upload in enumerate(files):
            if _job_cancel_requested(ctx, job_id):
                cancel_triggered = True
                _storage_lifecycle_log(
                    ctx=ctx,
                    op="upload_batch",
                    status="cancelled",
                    graph_id=graph_id,
                    job_id=str(job_id),
                    detail="cancellation acknowledged before processing next file",
                )
                JobStore.append_event(
                    ctx.session,
                    job_id,
                    "step_progress",
                    {
                        "index": index,
                        "status": "cancelled",
                        "message": "Cancellation acknowledged before next file",
                    },
                )
                break

            filename = sanitize_filename(upload.filename or f"upload-{index + 1}")
            result_entry = UploadFileResult(
                filename=filename,
                status="pending",
                requested_profile=requested_profile,
                requested_persist_mode=requested_persist_mode,
                requested_extractor_mode=requested_extractor_mode,
                effective_profile=policy.effective_profile,
                effective_persist_mode=policy.effective_persist_mode,
                effective_extractor_mode=requested_extractor_mode,
                durability_path=policy.durability_path,
            )
            file_results.append(result_entry)

            try:
                await validate_upload_file(upload)
                validate_file_extension(filename)

                file_bytes = await upload.read()
                validate_upload_size(len(file_bytes))

                mime_type = (upload.content_type or "application/octet-stream").split(";")[
                    0
                ].strip()
                validate_content_type(mime_type)
                validate_mime_extension_match(filename, mime_type)

                try:
                    saved_ref = _store_raw_upload(
                        ctx=ctx,
                        graph_id=graph_id,
                        file_bytes=file_bytes,
                        mime_type=mime_type,
                    )
                except Exception as exc:
                    if _storage_encryption_enabled():
                        _emit_storage_audit_event(
                            ctx=ctx,
                            graph_id=graph_id,
                            kind="STORAGE_ENCRYPT_FAILED",
                            payload={
                                "filename": filename,
                                "mime_type": mime_type,
                                "size_bytes": len(file_bytes),
                                "error": str(exc),
                            },
                            commit=True,
                        )
                    raise

                raw_uuid = _parse_uuid(str(saved_ref.id), "raw_id")

                ctx.storage_file_repo.upsert_upload(
                    ctx.session,
                    graph_id=graph_id,
                    raw_id=raw_uuid,
                    filename=filename,
                    mime_type=mime_type,
                    size_bytes=len(file_bytes),
                    sha256=str(saved_ref.sha256),
                    job_id=job_id,
                )
                ctx.storage_file_repo.mark_ingesting(
                    ctx.session,
                    raw_id=raw_uuid,
                    graph_id=graph_id,
                    job_id=job_id,
                )
                _emit_storage_audit_event(
                    ctx=ctx,
                    graph_id=graph_id,
                    kind="STORAGE_RAW_STORED",
                    payload={
                        "job_id": str(job_id),
                        "raw_id": str(raw_uuid),
                        "filename": filename,
                        "mime_type": mime_type,
                        "size_bytes": len(file_bytes),
                        "sha256": str(saved_ref.sha256),
                    },
                )
                ctx.session.commit()
                _storage_lifecycle_log(
                    ctx=ctx,
                    op="raw_store",
                    status="stored",
                    graph_id=graph_id,
                    job_id=str(job_id),
                    raw_id=str(raw_uuid),
                    detail=f"raw persisted for {filename}",
                )

                JobStore.append_event(
                    ctx.session,
                    job_id,
                    "step_progress",
                    {
                        "index": index,
                        "filename": filename,
                        "raw_id": str(raw_uuid),
                        "message": "Ingest started",
                        "requested_extractor_mode": requested_extractor_mode,
                    },
                )

                if _job_cancel_requested(ctx, job_id):
                    cancel_triggered = True
                    cancelled += 1
                    processed += 1
                    result_entry.raw_id = str(raw_uuid)
                    result_entry.status = "cancelled"
                    result_entry.error = "Upload cancelled before ingest execution"
                    ctx.storage_file_repo.mark_cancelled(
                        ctx.session,
                        raw_id=raw_uuid,
                        graph_id=graph_id,
                        error_message=result_entry.error,
                        job_id=job_id,
                    )
                    JobStore.append_event(
                        ctx.session,
                        job_id,
                        "step_progress",
                        {
                            "index": index,
                            "filename": filename,
                            "raw_id": str(raw_uuid),
                            "status": "cancelled",
                            "message": "Cancellation acknowledged before ingest",
                            "requested_extractor_mode": requested_extractor_mode,
                        },
                    )
                    ctx.session.commit()
                    _storage_lifecycle_log(
                        ctx=ctx,
                        op="ingest",
                        status="cancelled",
                        graph_id=graph_id,
                        job_id=str(job_id),
                        raw_id=str(raw_uuid),
                        failure_reason="cancelled",
                        detail="cancellation acknowledged before ingest execution",
                    )
                    break

                ingest_result = _run_ingest_existing_raw(
                    ctx=ctx,
                    graph_id=graph_id,
                    raw_id=raw_uuid,
                    filename=filename,
                    file_bytes=file_bytes,
                    profile=profile,
                    persist_mode=persist_mode,
                    extractor_mode=requested_extractor_mode,
                )

                ctx.storage_file_repo.mark_ingest_result(
                    ctx.session,
                    raw_id=raw_uuid,
                    graph_id=graph_id,
                    status=ingest_result.status,
                    packet_hash=ingest_result.packet_hash or None,
                    node_count=ingest_result.nodes_written,
                    vector_count=ingest_result.vector_count,
                    error_message=ingest_result.error,
                    job_id=job_id,
                )
                if ingest_result.status == "dedup_hit":
                    _emit_storage_audit_event(
                        ctx=ctx,
                        graph_id=graph_id,
                        kind="STORAGE_DEDUP_HIT",
                        payload={
                            "job_id": str(job_id),
                            "raw_id": str(raw_uuid),
                            "filename": filename,
                            "packet_hash": ingest_result.packet_hash,
                            "requested_profile": ingest_result.requested_profile,
                            "requested_persist_mode": ingest_result.requested_persist_mode,
                            "requested_extractor_mode": ingest_result.requested_extractor_mode,
                            "effective_profile": ingest_result.effective_profile,
                            "effective_persist_mode": ingest_result.effective_persist_mode,
                            "effective_extractor_mode": ingest_result.effective_extractor_mode,
                            "durability_path": ingest_result.durability_path,
                        },
                    )
                elif ingest_result.status == "error":
                    _emit_storage_audit_event(
                        ctx=ctx,
                        graph_id=graph_id,
                        kind="STORAGE_EXTRACT_FAILED",
                        payload={
                            "job_id": str(job_id),
                            "raw_id": str(raw_uuid),
                            "filename": filename,
                            "error": ingest_result.error,
                            "requested_profile": ingest_result.requested_profile,
                            "requested_persist_mode": ingest_result.requested_persist_mode,
                            "requested_extractor_mode": ingest_result.requested_extractor_mode,
                            "effective_profile": ingest_result.effective_profile,
                            "effective_persist_mode": ingest_result.effective_persist_mode,
                            "effective_extractor_mode": ingest_result.effective_extractor_mode,
                            "durability_path": ingest_result.durability_path,
                        },
                    )
                ctx.session.commit()

                processed += 1
                result_entry.raw_id = str(raw_uuid)
                result_entry.packet_hash = ingest_result.packet_hash or None
                result_entry.node_count = ingest_result.nodes_written
                result_entry.vector_count = ingest_result.vector_count
                result_entry.requested_profile = ingest_result.requested_profile
                result_entry.requested_persist_mode = ingest_result.requested_persist_mode
                result_entry.requested_extractor_mode = ingest_result.requested_extractor_mode
                result_entry.effective_profile = ingest_result.effective_profile
                result_entry.effective_persist_mode = ingest_result.effective_persist_mode
                result_entry.effective_extractor_mode = ingest_result.effective_extractor_mode
                result_entry.durability_path = ingest_result.durability_path

                if ingest_result.status == "error":
                    failed += 1
                    result_entry.status = "failed"
                    result_entry.error = ingest_result.error
                elif ingest_result.status == "dedup_hit":
                    dedup_hits += 1
                    success += 1
                    result_entry.status = "dedup_hit"
                else:
                    success += 1
                    result_entry.status = "ingested"

                _storage_lifecycle_log(
                    ctx=ctx,
                    op="ingest",
                    status=result_entry.status,
                    graph_id=graph_id,
                    job_id=str(job_id),
                    raw_id=str(raw_uuid),
                    failure_reason=(
                        _normalize_failure_reason(result_entry.error)
                        if result_entry.error
                        else None
                    ),
                    latency_ms=ingest_result.latency_ms,
                    detail=f"ingest finished for {filename}",
                )

                JobStore.append_event(
                    ctx.session,
                    job_id,
                    "step_progress",
                    {
                        "index": index,
                        "filename": filename,
                        "raw_id": str(raw_uuid),
                        "status": result_entry.status,
                        "packet_hash": ingest_result.packet_hash,
                        "requested_profile": ingest_result.requested_profile,
                        "requested_persist_mode": ingest_result.requested_persist_mode,
                        "requested_extractor_mode": ingest_result.requested_extractor_mode,
                        "effective_profile": ingest_result.effective_profile,
                        "effective_persist_mode": ingest_result.effective_persist_mode,
                        "effective_extractor_mode": ingest_result.effective_extractor_mode,
                        "durability_path": ingest_result.durability_path,
                        "message": "Ingest finished",
                    },
                )
            except HTTPException as e:
                processed += 1
                failed += 1
                result_entry.status = "failed"
                result_entry.error = str(e.detail)
                ctx.session.rollback()
                _storage_lifecycle_log(
                    ctx=ctx,
                    op="ingest",
                    status="failed",
                    graph_id=graph_id,
                    job_id=str(job_id),
                    raw_id=result_entry.raw_id,
                    failure_reason=_normalize_failure_reason(result_entry.error),
                    detail=f"ingest failed for {filename}",
                    level="warning",
                )
                JobStore.append_event(
                    ctx.session,
                    job_id,
                    "step_progress",
                    {
                        "index": index,
                        "filename": filename,
                        "status": "failed",
                        "error": result_entry.error,
                        "requested_profile": result_entry.requested_profile,
                        "requested_persist_mode": result_entry.requested_persist_mode,
                        "requested_extractor_mode": result_entry.requested_extractor_mode,
                        "effective_profile": result_entry.effective_profile,
                        "effective_persist_mode": result_entry.effective_persist_mode,
                        "effective_extractor_mode": result_entry.effective_extractor_mode,
                        "durability_path": result_entry.durability_path,
                    },
                )
            except Exception as e:
                processed += 1
                failed += 1
                result_entry.status = "failed"
                result_entry.error = str(e)
                ctx.session.rollback()
                _storage_lifecycle_log(
                    ctx=ctx,
                    op="ingest",
                    status="failed",
                    graph_id=graph_id,
                    job_id=str(job_id),
                    raw_id=result_entry.raw_id,
                    failure_reason=_normalize_failure_reason(result_entry.error),
                    detail=f"ingest failed for {filename}",
                    level="warning",
                )
                JobStore.append_event(
                    ctx.session,
                    job_id,
                    "step_progress",
                    {
                        "index": index,
                        "filename": filename,
                        "status": "failed",
                        "error": str(e),
                        "requested_profile": result_entry.requested_profile,
                        "requested_persist_mode": result_entry.requested_persist_mode,
                        "requested_extractor_mode": result_entry.requested_extractor_mode,
                        "effective_profile": result_entry.effective_profile,
                        "effective_persist_mode": result_entry.effective_persist_mode,
                        "effective_extractor_mode": result_entry.effective_extractor_mode,
                        "durability_path": result_entry.durability_path,
                    },
                )

        if cancel_triggered:
            if len(file_results) < requested_files:
                for upload in files[len(file_results) :]:
                    file_results.append(
                        UploadFileResult(
                            filename=sanitize_filename(upload.filename or "upload"),
                            status="cancelled",
                            error="Upload cancelled before processing",
                        )
                    )
                    cancelled += 1
            for pending in file_results:
                if pending.status == "pending":
                    pending.status = "cancelled"
                    pending.error = "Upload cancelled before processing"
                    cancelled += 1
            final_status = "cancelled"
        else:
            final_status = "completed"
            if failed and success:
                final_status = "partial_failed"
            elif failed and not success:
                final_status = "failed"

        JobStore.append_event(
            ctx.session,
            job_id,
            "step_progress",
            {
                "message": "Batch finished",
                "status": final_status,
                "processed": processed,
                "success": success,
                "failed": failed,
                "dedup_hits": dedup_hits,
                "cancelled_files": cancelled,
                "requested_extractor_mode": requested_extractor_mode,
            },
        )

        job = JobStore.get_job(ctx.session, job_id)
        if job and job.tenant_id == ctx.tenant_id:
            payload = dict(job.payload_json or {})
            payload.update(
                {
                    "processed_files": processed,
                    "success_files": success,
                    "failed_files": failed,
                    "dedup_hits": dedup_hits,
                    "cancelled_files": cancelled,
                }
            )
            job.payload_json = payload
            job.updated_at = datetime.now(timezone.utc)
            if final_status == "cancelled":
                JobStore.mark_cancelled(
                    ctx.session,
                    job_id,
                    reason=JobStore.get_cancel_reason(ctx.session, job_id)
                    or "Cancelled by user request",
                )
            elif final_status == "failed":
                job.status = "failed"
                job.error_message = "All files failed ingestion"
                job.completed_at = datetime.now(timezone.utc)
                ctx.session.commit()
            else:
                job.status = "done"
                job.completed_at = datetime.now(timezone.utc)
                ctx.session.commit()

        if final_status in {"completed", "partial_failed"} and success > 0:
            try:
                evolve_job_id = _enqueue_post_upload_evolve_job(
                    ctx=ctx,
                    graph_id=graph_id,
                    upload_job_id=job_id,
                )
                if evolve_job_id is not None:
                    followup_evolve_job_id = str(evolve_job_id)
                    job = JobStore.get_job(ctx.session, job_id)
                    if job and job.tenant_id == ctx.tenant_id:
                        payload = dict(job.payload_json or {})
                        payload["followup_evolve_job_id"] = followup_evolve_job_id
                        job.payload_json = payload
                        job.updated_at = datetime.now(timezone.utc)
                        ctx.session.commit()
                    _storage_lifecycle_log(
                        ctx=ctx,
                        op="upload_batch",
                        status="evolve_enqueued",
                        graph_id=graph_id,
                        job_id=str(job_id),
                        detail=(
                            "post-upload evolve job enqueued "
                            f"(evolve_job_id={followup_evolve_job_id})"
                        ),
                    )
                    JobStore.append_event(
                        ctx.session,
                        job_id,
                        "step_progress",
                        {
                            "status": "followup_evolve_enqueued",
                            "evolve_job_id": followup_evolve_job_id,
                            "message": "Post-upload evolve job enqueued",
                        },
                    )
            except Exception as exc:  # nosec B110
                logger.warning("Failed to enqueue post-upload evolve job: %s", exc)

        _storage_lifecycle_log(
            ctx=ctx,
            op="upload_batch",
            status=final_status,
            graph_id=graph_id,
            job_id=str(job_id),
            latency_ms=int((time.perf_counter() - batch_started) * 1000),
            detail=(
                "batch completed "
                f"(processed={processed}, success={success}, failed={failed}, dedup={dedup_hits}, cancelled={cancelled})"
            ),
        )

        return StorageUploadBatchResponse(
            job_id=str(job_id),
            graph_id=graph_id,
            status=final_status,
            requested_files=requested_files,
            processed_files=processed,
            success_files=success,
            failed_files=failed,
            dedup_hits=dedup_hits,
            cancelled_files=cancelled,
            files=file_results,
            requested_profile=requested_profile,
            requested_persist_mode=requested_persist_mode,
            requested_extractor_mode=requested_extractor_mode,
            effective_profile=policy.effective_profile,
            effective_persist_mode=policy.effective_persist_mode,
            effective_extractor_mode=requested_extractor_mode,
            durability_path=policy.durability_path,
        )
    except HTTPException:
        ctx.session.rollback()
        raise
    except Exception as e:
        logger.error(f"Storage upload batch failed: {e}")
        ctx.session.rollback()
        _storage_lifecycle_log(
            ctx=ctx,
            op="upload_batch",
            status="failed",
            graph_id=graph_id,
            job_id=str(job_id),
            failure_reason=_normalize_failure_reason(str(e)),
            latency_ms=int((time.perf_counter() - batch_started) * 1000),
            detail="storage upload batch failed",
            level="error",
        )
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


@router.get("/uploads/{job_id}", response_model=StorageUploadStatusResponse)
async def get_upload_status(
    job_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageUploadStatusResponse:
    """Get status and per-file progress for an upload batch."""
    _require_storage_repos(ctx)

    from orchestration.jobs.job_store import JobStore
    from store.pg.models_faim import StorageFileModel

    job_uuid = _parse_uuid(job_id, "job_id")
    job = JobStore.get_job(ctx.session, job_uuid)
    if job is None or job.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Upload job not found")

    rows = (
        ctx.session.query(StorageFileModel)
        .filter(
            and_(
                StorageFileModel.tenant_id == ctx.tenant_id,
                StorageFileModel.last_job_id == job_uuid,
            )
        )
        .order_by(StorageFileModel.updated_at.desc(), StorageFileModel.id.asc())
        .all()
    )

    file_items = [_row_to_file_item(r) for r in rows]
    processed_files = len(file_items)
    success_files = len(
        [f for f in file_items if f.ingest_status in {"ingested", "dedup_hit"}]
    )
    failed_files = len([f for f in file_items if f.ingest_status == "failed"])
    dedup_hits = len([f for f in file_items if f.ingest_status == "dedup_hit"])
    payload = job.payload_json or {}
    cancelled_files = max(
        len([f for f in file_items if f.ingest_status == "cancelled"]),
        int(payload.get("cancelled_files", 0)),
    )
    requested_files = int(payload.get("requested_files", processed_files))
    cancel_requested = bool(payload.get("cancel_requested", False))
    cancel_reason = payload.get("cancel_reason")
    requested_profile = payload.get("requested_profile")
    requested_persist_mode = payload.get("requested_persist_mode")
    requested_extractor_mode = payload.get("requested_extractor_mode")
    effective_profile = payload.get("effective_profile")
    effective_persist_mode = payload.get("effective_persist_mode")
    effective_extractor_mode = payload.get("effective_extractor_mode")
    durability_path = payload.get("durability_path")

    return StorageUploadStatusResponse(
        job_id=str(job.job_id),
        graph_id=job.graph_id,
        status=job.status,
        requested_files=requested_files,
        processed_files=processed_files,
        success_files=success_files,
        failed_files=failed_files,
        dedup_hits=dedup_hits,
        cancelled_files=cancelled_files,
        cancel_requested=cancel_requested,
        cancel_reason=str(cancel_reason) if cancel_reason is not None else None,
        created_at=job.created_at.isoformat() if job.created_at else None,
        updated_at=job.updated_at.isoformat() if job.updated_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        files=file_items,
        requested_profile=(
            str(requested_profile) if requested_profile is not None else None
        ),
        requested_persist_mode=(
            str(requested_persist_mode) if requested_persist_mode is not None else None
        ),
        requested_extractor_mode=(
            str(requested_extractor_mode) if requested_extractor_mode is not None else None
        ),
        effective_profile=(
            str(effective_profile) if effective_profile is not None else None
        ),
        effective_persist_mode=(
            str(effective_persist_mode) if effective_persist_mode is not None else None
        ),
        effective_extractor_mode=(
            str(effective_extractor_mode) if effective_extractor_mode is not None else None
        ),
        durability_path=str(durability_path) if durability_path is not None else None,
    )


@router.get("/uploads/{job_id}/events", response_model=StorageJobEventsResponse)
async def get_upload_job_events(
    job_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageJobEventsResponse:
    """Get timeline events for a storage upload job."""
    _require_storage_repos(ctx)

    from orchestration.jobs.job_store import JobStore

    job_uuid = _parse_uuid(job_id, "job_id")
    job = JobStore.get_job(ctx.session, job_uuid)
    if job is None or job.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Upload job not found")

    events = JobStore.get_job_events(ctx.session, job_uuid)
    return StorageJobEventsResponse(
        job_id=str(job_uuid),
        events=[
            StorageJobEvent(
                seq=int(e.seq),
                kind=e.kind,
                ts=e.ts.isoformat() if e.ts else None,
                payload=e.payload or {},
            )
            for e in events
        ],
    )


@router.post("/uploads/{job_id}/cancel", response_model=StorageUploadCancelResponse)
async def cancel_upload_job(
    job_id: str,
    reason: Optional[str] = Query(None),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageUploadCancelResponse:
    """Request cancellation for an upload job."""
    _require_storage_repos(ctx)

    from orchestration.jobs.job_store import JobStore

    job_uuid = _parse_uuid(job_id, "job_id")
    job = JobStore.get_job(ctx.session, job_uuid)
    if job is None or job.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=404, detail="Upload job not found")

    if job.status in {"done", "failed", "cancelled"}:
        _storage_lifecycle_log(
            ctx=ctx,
            op="upload_cancel",
            status=job.status,
            graph_id=job.graph_id,
            job_id=str(job_uuid),
            detail="cancellation request ignored because job is terminal",
        )
        return StorageUploadCancelResponse(
            job_id=str(job_uuid),
            status=job.status,
            cancel_requested=bool((job.payload_json or {}).get("cancel_requested")),
            cancel_reason=(job.payload_json or {}).get("cancel_reason"),
        )

    updated = JobStore.request_cancel(ctx.session, job_uuid, reason=reason)
    if updated is None:
        raise HTTPException(status_code=404, detail="Upload job not found")

    JobStore.append_event(
        ctx.session,
        job_uuid,
        "step_progress",
        {
            "status": "cancel_requested",
            "message": "Cancellation requested",
            "reason": reason,
        },
    )
    payload = updated.payload_json or {}
    _storage_lifecycle_log(
        ctx=ctx,
        op="upload_cancel",
        status="cancel_requested",
        graph_id=updated.graph_id,
        job_id=str(job_uuid),
        failure_reason="cancel_requested",
        detail="cancellation requested for upload job",
    )
    return StorageUploadCancelResponse(
        job_id=str(job_uuid),
        status=updated.status,
        cancel_requested=bool(payload.get("cancel_requested")),
        cancel_reason=payload.get("cancel_reason"),
    )


# =============================================================================
# File Catalog
# =============================================================================


@router.get("/files", response_model=StorageFileListResponse)
async def list_storage_files(
    graph_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    include_delete_requested: bool = Query(False),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageFileListResponse:
    """List files in storage catalog."""
    _require_storage_repos(ctx)

    rows, total = ctx.storage_file_repo.list_files(
        ctx.session,
        graph_id=graph_id,
        status=status,
        query=q,
        limit=limit,
        offset=offset,
        include_delete_requested=include_delete_requested,
    )

    return StorageFileListResponse(
        items=[_row_to_file_item(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/files/{raw_id}", response_model=StorageFileItem)
async def get_storage_file(
    raw_id: str,
    graph_id: Optional[str] = Query(None),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageFileItem:
    """Get one file metadata entry by raw_id."""
    _require_storage_repos(ctx)

    raw_uuid = _parse_uuid(raw_id, "raw_id")
    row = ctx.storage_file_repo.get_by_raw_id(ctx.session, raw_uuid, graph_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Storage file not found")

    return _row_to_file_item(row)


@router.get("/files/{raw_id}/download")
async def download_storage_file(
    raw_id: str,
    graph_id: Optional[str] = Query(None),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
):
    """Download the original raw blob for a stored file."""
    _require_storage_repos(ctx)

    raw_uuid = _parse_uuid(raw_id, "raw_id")
    row = ctx.storage_file_repo.get_by_raw_id(ctx.session, raw_uuid, graph_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Storage file not found")

    raw_ref = ctx.raw_repo.get_by_id(ctx.session, raw_uuid)
    if raw_ref is None:
        raise HTTPException(status_code=404, detail="Raw reference not found")

    store = _resolve_raw_store(ctx)
    try:
        file_bytes = store.load(raw_ref, verify=True)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Raw blob not available: {e}") from e

    filename = sanitize_filename(row.filename or f"{raw_uuid}")
    headers = {
        "Content-Disposition": (
            f"attachment; filename=\"{filename}\"; "
            f"filename*=UTF-8''{quote(filename)}"
        ),
        "X-Content-Type-Options": "nosniff",
    }
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=row.mime_type or "application/octet-stream",
        headers=headers,
    )


@router.get("/files/{raw_id}/provenance", response_model=StorageProvenanceResponse)
async def get_storage_file_provenance(
    raw_id: str,
    graph_id: Optional[str] = Query(None),
    limit_nodes: int = Query(25, ge=1, le=200),
    limit_events: int = Query(50, ge=1, le=500),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageProvenanceResponse:
    """Inspect provenance linkage from raw source to nodes/events."""
    _require_storage_repos(ctx)

    from store.pg.models_faim import IngestDedupModel, NodeModel

    raw_uuid = _parse_uuid(raw_id, "raw_id")
    row = ctx.storage_file_repo.get_by_raw_id(ctx.session, raw_uuid, graph_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Storage file not found")

    raw_ref = ctx.raw_repo.get_by_id(ctx.session, raw_uuid)
    raw_ref_model = None
    if raw_ref is not None:
        raw_ref_model = StorageProvenanceRawRef(
            raw_id=str(raw_ref.id),
            sha256=str(raw_ref.sha256),
            uri=str(raw_ref.uri),
            mime_type=str(raw_ref.mime_type),
            size_bytes=int(raw_ref.size_bytes),
            created_at=raw_ref.created_at.isoformat() if raw_ref.created_at else None,
        )

    dedup_record = None
    dedup_raw_id = str(raw_uuid)
    if row.packet_hash:
        dedup_record = IngestDedupModel.check_exists(
            ctx.session,
            ctx.tenant_id,
            row.graph_id,
            row.packet_hash,
        )
        if dedup_record is not None and dedup_record.raw_id:
            dedup_raw_id = str(dedup_record.raw_id)

    provenance_raw_ids = {str(raw_uuid)}
    if dedup_raw_id:
        provenance_raw_ids.add(dedup_raw_id)

    nodes_q = (
        ctx.session.query(NodeModel)
        .filter(
            and_(
                NodeModel.tenant_id == ctx.tenant_id,
                NodeModel.graph_id == row.graph_id,
                NodeModel.raw_id.in_(list(provenance_raw_ids)),
            )
        )
        .order_by(NodeModel.created_at.desc(), NodeModel.node_id.asc())
    )
    node_rows = nodes_q.limit(limit_nodes).all()
    node_count = int(nodes_q.count())

    event_items: List[StorageProvenanceEvent] = []
    if ctx.event_repo:
        try:
            all_events = ctx.event_repo.get_by_seq(
                ctx.session,
                graph_id=row.graph_id,
                after_seq=0,
                limit=max(limit_events * 4, 100),
            )
            for event in reversed(all_events):
                payload = event.payload or {}
                payload_raw_id = str(payload.get("raw_id", "")).strip()
                if payload_raw_id and payload_raw_id in provenance_raw_ids:
                    event_items.append(
                        StorageProvenanceEvent(
                            seq=int(event.seq),
                            kind=event.kind,
                            ts=event.ts.isoformat() if event.ts else None,
                            payload_keys=sorted([str(k) for k in payload.keys()]),
                            payload={str(k): v for k, v in payload.items()},
                        )
                    )
                if len(event_items) >= limit_events:
                    break
        except Exception as exc:  # nosec B110
            logger.warning("Failed to load provenance events: %s", exc)

    return StorageProvenanceResponse(
        file=_row_to_file_item(row),
        raw_ref=raw_ref_model,
        dedup=StorageProvenanceDedup(
            packet_hash=row.packet_hash,
            dedup_record_found=dedup_record is not None,
            dedup_raw_id=dedup_raw_id,
            dedup_node_count=int(getattr(dedup_record, "node_count", 0) or 0),
            dedup_created_at=(
                dedup_record.created_at.isoformat()
                if dedup_record is not None and dedup_record.created_at
                else None
            ),
        ),
        node_count=node_count,
        event_count=len(event_items),
        nodes=[
            StorageProvenanceNode(
                node_id=str(node.node_id),
                kind=node.kind,
                vector_hash=node.vector_hash,
                block_id=node.block_id,
                created_at=node.created_at.isoformat() if node.created_at else None,
            )
            for node in node_rows
        ],
        events=event_items,
    )


@router.delete("/files/{raw_id}", response_model=StorageFileItem)
async def request_delete_storage_file(
    raw_id: str,
    graph_id: str = Query(...),
    reason: Optional[str] = Query(None),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageFileItem:
    """Mark a file as delete-requested (logical request only)."""
    _require_storage_repos(ctx)

    raw_uuid = _parse_uuid(raw_id, "raw_id")
    row = ctx.storage_file_repo.mark_delete_requested(
        ctx.session,
        raw_id=raw_uuid,
        graph_id=graph_id,
        reason=reason,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Storage file not found")

    _emit_storage_audit_event(
        ctx=ctx,
        graph_id=graph_id,
        kind="STORAGE_DELETE_REQUESTED",
        payload={
            "raw_id": str(raw_uuid),
            "reason": reason,
        },
    )

    ctx.session.commit()
    _storage_lifecycle_log(
        ctx=ctx,
        op="delete_request",
        status="delete_requested",
        graph_id=graph_id,
        raw_id=str(raw_uuid),
        detail="logical delete request recorded",
    )
    return _row_to_file_item(row)


# =============================================================================
# Ingestion / Retry
# =============================================================================


@router.post("/files/{raw_id}/ingest", response_model=StorageIngestActionResponse)
async def reingest_storage_file(
    raw_id: str,
    graph_id: Optional[str] = Query(None),
    profile: str = Query("strict"),
    persist_mode: str = Query("relaxed"),
    extractor_mode: str = Query("auto"),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageIngestActionResponse:
    """Re-ingest an existing raw file."""
    _require_storage_repos(ctx)

    raw_uuid = _parse_uuid(raw_id, "raw_id")
    row = ctx.storage_file_repo.get_by_raw_id(ctx.session, raw_uuid, graph_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Storage file not found")

    raw_ref = ctx.raw_repo.get_by_id(ctx.session, raw_uuid)
    if raw_ref is None:
        raise HTTPException(status_code=404, detail="Raw reference not found")

    store = _resolve_raw_store(ctx)
    try:
        file_bytes = store.load(raw_ref, verify=True)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Raw blob not available: {e}") from e

    ctx.storage_file_repo.mark_ingesting(
        ctx.session,
        raw_id=raw_uuid,
        graph_id=row.graph_id,
        job_id=None,
    )
    ctx.session.commit()

    ingest_result = _run_ingest_existing_raw(
        ctx=ctx,
        graph_id=row.graph_id,
        raw_id=raw_uuid,
        filename=row.filename,
        file_bytes=file_bytes,
        profile=profile,
        persist_mode=persist_mode,
        extractor_mode=extractor_mode,
    )

    row = ctx.storage_file_repo.mark_ingest_result(
        ctx.session,
        raw_id=raw_uuid,
        graph_id=row.graph_id,
        status=ingest_result.status,
        packet_hash=ingest_result.packet_hash or None,
        node_count=ingest_result.nodes_written,
        vector_count=ingest_result.vector_count,
        error_message=ingest_result.error,
        job_id=None,
    )
    if ingest_result.status == "dedup_hit":
        _emit_storage_audit_event(
            ctx=ctx,
            graph_id=row.graph_id,
            kind="STORAGE_DEDUP_HIT",
            payload={
                "raw_id": str(raw_uuid),
                "filename": row.filename,
                "packet_hash": ingest_result.packet_hash,
                "requested_profile": ingest_result.requested_profile,
                "requested_persist_mode": ingest_result.requested_persist_mode,
                "requested_extractor_mode": ingest_result.requested_extractor_mode,
                "effective_profile": ingest_result.effective_profile,
                "effective_persist_mode": ingest_result.effective_persist_mode,
                "effective_extractor_mode": ingest_result.effective_extractor_mode,
                "durability_path": ingest_result.durability_path,
            },
        )
    elif ingest_result.status == "error":
        _emit_storage_audit_event(
            ctx=ctx,
            graph_id=row.graph_id,
            kind="STORAGE_EXTRACT_FAILED",
            payload={
                "raw_id": str(raw_uuid),
                "filename": row.filename,
                "error": ingest_result.error,
                "requested_profile": ingest_result.requested_profile,
                "requested_persist_mode": ingest_result.requested_persist_mode,
                "requested_extractor_mode": ingest_result.requested_extractor_mode,
                "effective_profile": ingest_result.effective_profile,
                "effective_persist_mode": ingest_result.effective_persist_mode,
                "effective_extractor_mode": ingest_result.effective_extractor_mode,
                "durability_path": ingest_result.durability_path,
            },
        )
    ctx.session.commit()
    _storage_lifecycle_log(
        ctx=ctx,
        op="reingest",
        status=ingest_result.status,
        graph_id=row.graph_id,
        raw_id=str(raw_uuid),
        failure_reason=(
            _normalize_failure_reason(ingest_result.error)
            if ingest_result.error
            else None
        ),
        latency_ms=ingest_result.latency_ms,
        detail="re-ingest completed",
    )

    return StorageIngestActionResponse(
        status="ok",
        file=_row_to_file_item(row),
        ingest={
            "status": ingest_result.status,
            "packet_hash": ingest_result.packet_hash,
            "graph_version": ingest_result.graph_version,
            "nodes_written": ingest_result.nodes_written,
            "vector_count": ingest_result.vector_count,
            "events_emitted": ingest_result.events_emitted,
            "latency_ms": ingest_result.latency_ms,
            "phase_latency_ms": ingest_result.phase_latency_ms,
            "error": ingest_result.error,
            "requested_profile": ingest_result.requested_profile,
            "requested_persist_mode": ingest_result.requested_persist_mode,
            "requested_extractor_mode": ingest_result.requested_extractor_mode,
            "effective_profile": ingest_result.effective_profile,
            "effective_persist_mode": ingest_result.effective_persist_mode,
            "effective_extractor_mode": ingest_result.effective_extractor_mode,
            "durability_path": ingest_result.durability_path,
            "index_write_mode": ingest_result.index_write_mode,
            "secondary_task_status": ingest_result.secondary_task_status,
            "secondary_task_job_id": ingest_result.secondary_task_job_id,
        },
    )


@router.post("/files/{raw_id}/retry", response_model=StorageIngestActionResponse)
async def retry_storage_file(
    raw_id: str,
    graph_id: Optional[str] = Query(None),
    profile: str = Query("strict"),
    persist_mode: str = Query("relaxed"),
    extractor_mode: str = Query("auto"),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageIngestActionResponse:
    """Retry a failed file ingest."""
    _require_storage_repos(ctx)

    raw_uuid = _parse_uuid(raw_id, "raw_id")
    row = ctx.storage_file_repo.get_by_raw_id(ctx.session, raw_uuid, graph_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Storage file not found")

    if row.ingest_status != "failed":
        raise HTTPException(
            status_code=409,
            detail=f"Retry is only allowed for failed files (current status: {row.ingest_status})",
        )

    response = await reingest_storage_file(
        raw_id=raw_id,
        graph_id=graph_id,
        profile=profile,
        persist_mode=persist_mode,
        extractor_mode=extractor_mode,
        ctx=ctx,
    )
    _storage_lifecycle_log(
        ctx=ctx,
        op="retry",
        status=response.ingest.get("status", "ok"),
        graph_id=response.file.graph_id,
        raw_id=response.file.raw_id,
        failure_reason=(
            _normalize_failure_reason(response.ingest.get("error"))
            if response.ingest.get("error")
            else None
        ),
        detail="retry completed",
    )
    return response


@router.post(
    "/graphs/{graph_id}/representation-v2/rebuild",
    response_model=StorageRepresentationBackfillResponse,
)
async def rebuild_representation_v2_for_graph(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageRepresentationBackfillResponse:
    """Rebuild Representation V2 sidecars for all stored files in a graph."""
    _require_storage_repos(ctx)

    from orchestration.representation_v2_backfill import run_representation_v2_backfill

    result = run_representation_v2_backfill(
        session=ctx.session,
        tenant_id=ctx.tenant_id,
        graph_id=graph_id,
        raw_repo=ctx.raw_repo,
        storage_file_repo=ctx.storage_file_repo,
        raw_store=_resolve_raw_store(ctx),
        node_repo=ctx.node_repo,
        gv_repo=ctx.gv_repo,
        event_repo=ctx.event_repo,
    )
    ctx.session.commit()

    _storage_lifecycle_log(
        ctx=ctx,
        op="repr_v2_backfill",
        status="completed",
        graph_id=graph_id,
        detail="representation-v2 backfill completed",
    )

    return StorageRepresentationBackfillResponse(
        status="ok",
        graph_id=graph_id,
        files_scanned=result.files_scanned,
        files_loaded=result.files_loaded,
        files_failed=result.files_failed,
        blocks_extracted=result.blocks_extracted,
        matched_nodes=result.matched_nodes,
        inserted=result.inserted,
        updated=result.updated,
        unchanged=result.unchanged,
        skipped_nodes=result.skipped_nodes,
        graph_version=result.graph_version,
        errors=result.errors,
    )


@router.post(
    "/graphs/{graph_id}/canonical-semantics/rebuild",
    response_model=StorageCanonicalSemanticsRebuildResponse,
)
async def rebuild_canonical_semantics_for_graph(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageCanonicalSemanticsRebuildResponse:
    """Rebuild graph-scoped canonical semantics artifacts for stored files."""
    _require_storage_repos(ctx)

    from orchestration.canonical_semantics_rebuild import run_canonical_semantics_rebuild

    result = run_canonical_semantics_rebuild(
        session=ctx.session,
        tenant_id=ctx.tenant_id,
        graph_id=graph_id,
        raw_repo=ctx.raw_repo,
        storage_file_repo=ctx.storage_file_repo,
        raw_store=_resolve_raw_store(ctx),
        node_repo=ctx.node_repo,
        edge_repo=ctx.edge_repo,
        gv_repo=ctx.gv_repo,
        event_repo=ctx.event_repo,
    )
    ctx.session.commit()

    _storage_lifecycle_log(
        ctx=ctx,
        op="canonical_semantics_rebuild",
        status="completed",
        graph_id=graph_id,
        detail="canonical semantics rebuild completed",
    )

    return StorageCanonicalSemanticsRebuildResponse(
        status="ok",
        graph_id=graph_id,
        files_scanned=result.files_scanned,
        files_loaded=result.files_loaded,
        files_failed=result.files_failed,
        blocks_extracted=result.blocks_extracted,
        matched_nodes=result.matched_nodes,
        term_stats_written=result.term_stats_written,
        lexicon_written=result.lexicon_written,
        edges_written=result.edges_written,
        graph_version=result.graph_version,
        errors=result.errors,
    )


@router.post(
    "/graphs/{graph_id}/multilingual-semantics/rebuild",
    response_model=StorageMultilingualSemanticsRebuildResponse,
)
async def rebuild_multilingual_semantics_for_graph(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageMultilingualSemanticsRebuildResponse:
    """Rebuild graph-scoped EN/DE multilingual semantics artifacts for stored files."""
    _require_storage_repos(ctx)

    from orchestration.multilingual_semantics_rebuild import run_multilingual_semantics_rebuild

    result = run_multilingual_semantics_rebuild(
        session=ctx.session,
        tenant_id=ctx.tenant_id,
        graph_id=graph_id,
        raw_repo=ctx.raw_repo,
        storage_file_repo=ctx.storage_file_repo,
        raw_store=_resolve_raw_store(ctx),
        node_repo=ctx.node_repo,
        edge_repo=ctx.edge_repo,
        gv_repo=ctx.gv_repo,
        event_repo=ctx.event_repo,
    )
    ctx.session.commit()

    _storage_lifecycle_log(
        ctx=ctx,
        op="multilingual_semantics_rebuild",
        status="completed",
        graph_id=graph_id,
        detail="multilingual semantics rebuild completed",
    )

    return StorageMultilingualSemanticsRebuildResponse(
        status="ok",
        graph_id=graph_id,
        files_scanned=result.files_scanned,
        files_loaded=result.files_loaded,
        files_failed=result.files_failed,
        blocks_extracted=result.blocks_extracted,
        matched_nodes=result.matched_nodes,
        lexicon_written=result.lexicon_written,
        concept_nodes_written=result.concept_nodes_written,
        concept_edges_written=result.concept_edges_written,
        graph_version=result.graph_version,
        errors=result.errors,
    )


@router.post(
    "/graphs/{graph_id}/domain-profile/rebuild",
    response_model=StorageDomainProfileRebuildResponse,
)
async def rebuild_domain_profile_for_graph(
    graph_id: str,
    domain_pack: Optional[str] = Query(None),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageDomainProfileRebuildResponse:
    """Rebuild graph-scoped domain terminology artifacts for stored files."""
    _require_storage_repos(ctx)

    from orchestration.domain_profile_rebuild import run_domain_profile_rebuild

    result = run_domain_profile_rebuild(
        session=ctx.session,
        tenant_id=ctx.tenant_id,
        graph_id=graph_id,
        raw_repo=ctx.raw_repo,
        storage_file_repo=ctx.storage_file_repo,
        raw_store=_resolve_raw_store(ctx),
        node_repo=ctx.node_repo,
        gv_repo=ctx.gv_repo,
        event_repo=ctx.event_repo,
        domain_pack=domain_pack,
    )
    ctx.session.commit()

    _storage_lifecycle_log(
        ctx=ctx,
        op="domain_profile_rebuild",
        status="completed",
        graph_id=graph_id,
        detail="domain profile rebuild completed",
    )

    return StorageDomainProfileRebuildResponse(
        status="ok",
        graph_id=graph_id,
        files_scanned=result.files_scanned,
        files_loaded=result.files_loaded,
        files_failed=result.files_failed,
        blocks_extracted=result.blocks_extracted,
        matched_nodes=result.matched_nodes,
        lexicon_written=result.lexicon_written,
        graph_version=result.graph_version,
        errors=result.errors,
    )


@router.post(
    "/graphs/{graph_id}/domain-knowledge/import",
    response_model=StorageDomainKnowledgeImportResponse,
)
async def import_domain_knowledge_for_graph(
    graph_id: str,
    body: StorageDomainKnowledgeImportRequest = Body(
        default_factory=StorageDomainKnowledgeImportRequest
    ),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageDomainKnowledgeImportResponse:
    """Import offline graph-scoped domain knowledge."""
    from orchestration.domain_knowledge_import import run_domain_knowledge_import

    result = run_domain_knowledge_import(
        session=ctx.session,
        tenant_id=ctx.tenant_id,
        graph_id=graph_id,
        kb_rows=body.kb_rows,
        domain_pack=body.domain_pack,
        node_repo=ctx.node_repo,
        edge_repo=ctx.edge_repo,
        gv_repo=ctx.gv_repo,
        event_repo=ctx.event_repo,
    )
    ctx.session.commit()

    _storage_lifecycle_log(
        ctx=ctx,
        op="domain_knowledge_import",
        status="completed",
        graph_id=graph_id,
        detail="domain knowledge import completed",
    )

    return StorageDomainKnowledgeImportResponse(
        status="ok",
        graph_id=graph_id,
        sources_written=result.sources_written,
        lexicon_written=result.lexicon_written,
        entity_nodes_written=result.entity_nodes_written,
        relation_nodes_written=result.relation_nodes_written,
        fact_nodes_written=result.fact_nodes_written,
        value_nodes_written=result.value_nodes_written,
        time_nodes_written=result.time_nodes_written,
        edges_written=result.edges_written,
        graph_version=result.graph_version,
        errors=result.errors,
    )


@router.post(
    "/graphs/{graph_id}/multimodal/rebuild",
    response_model=StorageMultimodalBackfillResponse,
)
async def rebuild_multimodal_for_graph(
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageMultimodalBackfillResponse:
    """Rebuild graph-scoped multimodal sidecars for stored files."""
    _require_storage_repos(ctx)

    from orchestration.multimodal_backfill import run_multimodal_backfill

    result = run_multimodal_backfill(
        session=ctx.session,
        tenant_id=ctx.tenant_id,
        graph_id=graph_id,
        raw_repo=ctx.raw_repo,
        storage_file_repo=ctx.storage_file_repo,
        raw_store=_resolve_raw_store(ctx),
        node_repo=ctx.node_repo,
        gv_repo=ctx.gv_repo,
        event_repo=ctx.event_repo,
    )
    ctx.session.commit()

    _storage_lifecycle_log(
        ctx=ctx,
        op="multimodal_backfill",
        status="completed",
        graph_id=graph_id,
        detail="multimodal backfill completed",
    )

    return StorageMultimodalBackfillResponse(
        status="ok",
        graph_id=graph_id,
        files_scanned=result.files_scanned,
        files_loaded=result.files_loaded,
        files_failed=result.files_failed,
        blocks_extracted=result.blocks_extracted,
        matched_nodes=result.matched_nodes,
        inserted=result.inserted,
        updated=result.updated,
        unchanged=result.unchanged,
        graph_version=result.graph_version,
        errors=result.errors,
    )


# =============================================================================
# Summary + Health
# =============================================================================


@router.get("/supported-types", response_model=StorageSupportedTypesResponse)
async def get_storage_supported_types(
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageSupportedTypesResponse:
    """Get supported upload/extraction types and OCR runtime capability."""
    _require_storage_repos(ctx)

    from api.validators.input_limits import (
        ALLOWED_CONTENT_TYPES,
        ALLOWED_EXTENSIONS,
        MAX_UPLOAD_SIZE,
    )
    from perception.router import EXTENSION_DOC_TYPE

    try:
        from perception.extract.ocr_service import get_ocr_settings
    except Exception:
        get_ocr_settings = None  # type: ignore[assignment]

    if get_ocr_settings is not None:
        ocr_settings = get_ocr_settings()
        ocr_enabled = bool(ocr_settings.enabled)
        ocr_engine = str(ocr_settings.engine)
        ocr_fail_closed = bool(ocr_settings.fail_closed)
    else:
        ocr_enabled = False
        ocr_engine = "unavailable"
        ocr_fail_closed = False

    categories: Dict[str, List[str]] = {
        "documents": [],
        "images": [],
        "code": [],
        "text_data": [],
        "other": [],
    }
    for ext in sorted(ALLOWED_EXTENSIONS):
        if ext in {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}:
            categories["documents"].append(ext)
        elif ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tiff"}:
            categories["images"].append(ext)
        elif ext in {
            ".py",
            ".js",
            ".ts",
            ".java",
            ".go",
            ".rs",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".cs",
            ".rb",
            ".php",
            ".swift",
            ".kt",
            ".scala",
            ".sh",
            ".sql",
        }:
            categories["code"].append(ext)
        elif ext in {
            ".txt",
            ".md",
            ".markdown",
            ".rst",
            ".csv",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".xml",
            ".html",
            ".htm",
        }:
            categories["text_data"].append(ext)
        else:
            categories["other"].append(ext)

    extractor_doc_types: Dict[str, int] = {}
    for doc_type in EXTENSION_DOC_TYPE.values():
        extractor_doc_types[doc_type] = extractor_doc_types.get(doc_type, 0) + 1

    ocr_capable_extensions = sorted(
        [ext for ext, doc_type in EXTENSION_DOC_TYPE.items() if doc_type in {"image", "pdf"}]
    )

    return StorageSupportedTypesResponse(
        max_upload_size_bytes=int(MAX_UPLOAD_SIZE),
        max_upload_size_mb=round(float(MAX_UPLOAD_SIZE) / (1024 * 1024), 2),
        total_extensions=len(ALLOWED_EXTENSIONS),
        total_content_types=len(ALLOWED_CONTENT_TYPES),
        extensions=sorted(ALLOWED_EXTENSIONS),
        content_types=sorted(ALLOWED_CONTENT_TYPES),
        categories=categories,
        extractor_doc_types=dict(sorted(extractor_doc_types.items(), key=lambda item: item[0])),
        ocr_enabled=ocr_enabled,
        ocr_engine=ocr_engine,
        ocr_fail_closed=ocr_fail_closed,
        ocr_capable_extensions=ocr_capable_extensions,
    )


@router.get("/maintenance/history", response_model=StorageMaintenanceHistoryResponse)
async def get_storage_maintenance_history(
    graph_id: str = Query(...),
    limit: int = Query(10, ge=1, le=50),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageMaintenanceHistoryResponse:
    """Get recent storage maintenance actions for a graph."""
    _require_storage_repos(ctx)

    from store.pg.models_faim import EventModel

    kinds = [
        "CANONICAL_SEMANTICS_REBUILD",
        "MULTILINGUAL_SEMANTICS_REBUILD",
        "MULTIMODAL_BACKFILL",
        "DOMAIN_PROFILE_REBUILD",
        "DOMAIN_KNOWLEDGE_IMPORT",
    ]
    rows = (
        ctx.session.query(EventModel)
        .filter(
            and_(
                EventModel.tenant_id == ctx.tenant_id,
                EventModel.graph_id == graph_id,
                EventModel.kind.in_(kinds),
            )
        )
        .order_by(desc(EventModel.seq))
        .limit(limit)
        .all()
    )

    items: List[StorageMaintenanceHistoryItem] = []
    for row in reversed(rows):
        payload = dict(row.payload or {})
        items.append(
            StorageMaintenanceHistoryItem(
                seq=row.seq,
                kind=row.kind,
                ts=row.ts.isoformat() if row.ts else None,
                status=str(payload.get("status") or "completed"),
                summary=_maintenance_summary(row.kind, payload),
                graph_version=(
                    int(payload["graph_version"])
                    if isinstance(payload.get("graph_version"), (int, float, str))
                    and str(payload.get("graph_version")).strip().isdigit()
                    else None
                ),
                payload=payload,
            )
        )

    return StorageMaintenanceHistoryResponse(
        graph_id=graph_id,
        total=len(items),
        items=items,
    )


@router.get("/summary", response_model=StorageSummaryResponse)
async def get_storage_summary(
    graph_id: Optional[str] = Query(None),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageSummaryResponse:
    """Get storage summary metrics."""
    _require_storage_repos(ctx)

    summary = ctx.storage_file_repo.summary(ctx.session, graph_id=graph_id)
    return StorageSummaryResponse(graph_id=graph_id, **summary)


@router.get("/ops/metrics", response_model=StorageOpsMetricsResponse)
async def get_storage_ops_metrics(
    graph_id: Optional[str] = Query(None),
    window_seconds: int = Query(3600, ge=60, le=604800),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageOpsMetricsResponse:
    """Get storage observability metrics for operations and SLO tracking."""
    _require_storage_repos(ctx)
    try:
        from runtime.feature_flags import get_feature_flags

        if not get_feature_flags().storage_observability_enabled:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Storage observability metrics are disabled. "
                    "Set FAIM_STORAGE_OBSERVABILITY_ENABLED=true"
                ),
            )
    except HTTPException:
        raise
    except Exception:
        # Keep endpoint available if flags cannot be loaded.
        pass

    from store.pg.models_faim import EventModel, StorageFileModel

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=int(window_seconds))

    files_q = ctx.session.query(StorageFileModel).filter(
        and_(
            StorageFileModel.tenant_id == ctx.tenant_id,
            StorageFileModel.uploaded_at >= cutoff,
        )
    )
    if graph_id:
        files_q = files_q.filter(StorageFileModel.graph_id == graph_id)
    rows = files_q.all()

    upload_count = len(rows)
    upload_bytes = int(sum(int(r.size_bytes or 0) for r in rows))

    processed_statuses = {"ingested", "dedup_hit", "failed", "cancelled"}
    processed_files = int(sum(1 for r in rows if r.ingest_status in processed_statuses))
    dedup_hits = int(sum(1 for r in rows if r.ingest_status == "dedup_hit"))
    dedup_ratio = float(dedup_hits / processed_files) if processed_files > 0 else 0.0

    failure_rows = [r for r in rows if r.ingest_status == "failed"]
    failure_reasons: Dict[str, int] = {}
    for row in failure_rows:
        reason = _normalize_failure_reason(row.error_message)
        failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
    failures_total = int(len(failure_rows))

    phase_values: Dict[str, List[int]] = defaultdict(list)
    events_q = ctx.session.query(EventModel).filter(
        and_(
            EventModel.tenant_id == ctx.tenant_id,
            EventModel.kind == "INGEST_PHASE_LATENCY",
            EventModel.ts >= cutoff,
        )
    )
    if graph_id:
        events_q = events_q.filter(EventModel.graph_id == graph_id)

    for event in events_q.order_by(EventModel.seq.asc()).all():
        payload = event.payload or {}
        phase_payload = payload.get("phase_latency_ms")
        if not isinstance(phase_payload, dict):
            continue
        for phase, raw_value in phase_payload.items():
            try:
                value_int = int(raw_value)
            except (TypeError, ValueError):
                continue
            if value_int < 0:
                continue
            phase_values[str(phase)].append(value_int)

    phase_latency_ms: Dict[str, StoragePhaseLatencyStats] = {}
    for phase, values in phase_values.items():
        if not values:
            continue
        phase_latency_ms[phase] = StoragePhaseLatencyStats(
            count=len(values),
            avg_ms=round(sum(values) / max(1, len(values)), 2),
            p95_ms=round(_percentile(values, 95.0), 2),
            max_ms=max(values),
        )

    backend_states = _collect_backend_states(ctx)

    _storage_lifecycle_log(
        ctx=ctx,
        op="ops_metrics",
        status="ok",
        graph_id=graph_id,
        detail=(
            "storage ops metrics generated "
            f"(window_seconds={window_seconds}, uploads={upload_count}, failures={failures_total})"
        ),
    )

    return StorageOpsMetricsResponse(
        graph_id=graph_id,
        window_seconds=int(window_seconds),
        generated_at=now.isoformat(),
        upload_count=upload_count,
        upload_bytes=upload_bytes,
        processed_files=processed_files,
        dedup_hits=dedup_hits,
        dedup_ratio=round(dedup_ratio, 6),
        failures_total=failures_total,
        failure_reasons=dict(sorted(failure_reasons.items(), key=lambda item: item[0])),
        phase_latency_ms=phase_latency_ms,
        backend_states=backend_states,
    )


@router.get("/backends/health", response_model=StorageBackendsHealth)
async def get_storage_backends_health(
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageBackendsHealth:
    """Check operational storage backend health."""
    _require_storage_repos(ctx)
    states = _collect_backend_states(ctx)
    postgres_ok = states["postgres"].ok
    raw_store_ok = states["raw_store"].ok
    redis_ok = states["redis"].ok
    qdrant_ok = states["qdrant"].ok

    _storage_lifecycle_log(
        ctx=ctx,
        op="backend_health",
        status=(
            "ok"
            if all(s.ok for s in states.values())
            else "degraded"
            if any(s.ok for s in states.values())
            else "down"
        ),
        detail="backend health snapshot generated",
    )

    return StorageBackendsHealth(
        postgres=postgres_ok,
        redis=redis_ok,
        qdrant=qdrant_ok,
        raw_store=raw_store_ok,
    )


@router.post("/retention/execute", response_model=StorageRetentionResponse)
async def execute_storage_retention(
    request: StorageRetentionRequest = Body(default_factory=StorageRetentionRequest),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageRetentionResponse:
    """Run retention cleanup for delete-requested files.

    Default mode is dry-run; physical deletion requires irreversible mode and
    enabled hard-delete feature flag.
    """
    _require_storage_repos(ctx)
    started = time.perf_counter()

    if not request.dry_run and not request.irreversible:
        raise HTTPException(
            status_code=400,
            detail="Physical deletion requires irreversible=true",
        )

    if not request.dry_run:
        from runtime.feature_flags import get_feature_flags

        flags = get_feature_flags()
        if not flags.storage_hard_delete_enabled:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Physical deletion disabled. "
                    "Set FAIM_STORAGE_HARD_DELETE_ENABLED=true for irreversible cleanup."
                ),
            )

    try:
        from orchestration.jobs.storage_retention import run_storage_retention_cleanup

        result = run_storage_retention_cleanup(
            session=ctx.session,
            tenant_id=ctx.tenant_id,
            storage_file_repo=ctx.storage_file_repo,
            raw_repo=ctx.raw_repo,
            raw_store=_resolve_raw_store(ctx),
            event_repo=ctx.event_repo,
            graph_id=request.graph_id,
            limit=request.limit,
            dry_run=request.dry_run,
            irreversible=request.irreversible,
            reason=request.reason,
        )
    except ValueError as exc:
        _storage_lifecycle_log(
            ctx=ctx,
            op="retention_execute",
            status="failed",
            graph_id=request.graph_id,
            failure_reason=_normalize_failure_reason(str(exc)),
            latency_ms=int((time.perf_counter() - started) * 1000),
            detail="retention execution rejected",
            level="warning",
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        ctx.session.rollback()
        logger.error("Storage retention execution failed: %s", exc)
        _storage_lifecycle_log(
            ctx=ctx,
            op="retention_execute",
            status="failed",
            graph_id=request.graph_id,
            failure_reason=_normalize_failure_reason(str(exc)),
            latency_ms=int((time.perf_counter() - started) * 1000),
            detail="retention execution failed",
            level="error",
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    _storage_lifecycle_log(
        ctx=ctx,
        op="retention_execute",
        status="ok" if result.failed == 0 else "partial_failed",
        graph_id=request.graph_id,
        latency_ms=int((time.perf_counter() - started) * 1000),
        detail=(
            "retention execution completed "
            f"(dry_run={result.dry_run}, scanned={result.scanned}, deleted={result.deleted}, failed={result.failed})"
        ),
    )

    return StorageRetentionResponse(
        status="ok" if result.failed == 0 else "partial_failed",
        dry_run=result.dry_run,
        irreversible=result.irreversible,
        scanned=result.scanned,
        deleted=result.deleted,
        skipped=result.skipped,
        failed=result.failed,
        results=[
            StorageRetentionItem(
                raw_id=item.raw_id,
                graph_id=item.graph_id,
                filename=item.filename,
                status=item.status,
                detail=item.detail,
                blob_deleted=item.blob_deleted,
                raw_ref_deleted=item.raw_ref_deleted,
            )
            for item in result.results
        ],
    )


@router.post("/retention/jobs", response_model=StorageRetentionJobResponse)
async def enqueue_storage_retention_job(
    request: StorageRetentionRequest = Body(default_factory=StorageRetentionRequest),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageRetentionJobResponse:
    """Enqueue retention cleanup for background worker execution."""
    _require_storage_repos(ctx)

    from runtime.config import get_config

    cfg = get_config()
    if not cfg.enable_jobs:
        raise HTTPException(
            status_code=409,
            detail="Background jobs are disabled (FAIM_ENABLE_JOBS=false)",
        )

    if not request.dry_run and not request.irreversible:
        raise HTTPException(
            status_code=400,
            detail="Physical deletion requires irreversible=true",
        )

    if not request.dry_run and not cfg.storage_hard_delete_enabled:
        raise HTTPException(
            status_code=409,
            detail=(
                "Physical deletion disabled. "
                "Set FAIM_STORAGE_HARD_DELETE_ENABLED=true for irreversible cleanup."
            ),
        )

    from orchestration.jobs.job_store import JobStore

    payload = {
        "graph_id": request.graph_id,
        "limit": request.limit,
        "dry_run": request.dry_run,
        "irreversible": request.irreversible,
        "reason": request.reason,
    }
    graph_for_job = request.graph_id or "default"
    job_id = JobStore.enqueue(
        session=ctx.session,
        tenant_id=ctx.tenant_id,
        graph_id=graph_for_job,
        kind="storage_retention",
        payload=payload,
    )
    JobStore.append_event(
        ctx.session,
        job_id,
        "step_start",
        {
            "message": "Storage retention job enqueued",
            "graph_id": request.graph_id,
            "dry_run": request.dry_run,
            "irreversible": request.irreversible,
            "limit": request.limit,
        },
    )
    _storage_lifecycle_log(
        ctx=ctx,
        op="retention_enqueue",
        status="pending",
        graph_id=graph_for_job,
        job_id=str(job_id),
        detail=(
            "retention job enqueued "
            f"(dry_run={request.dry_run}, irreversible={request.irreversible}, limit={request.limit})"
        ),
    )

    return StorageRetentionJobResponse(
        job_id=str(job_id),
        graph_id=graph_for_job,
        kind="storage_retention",
        status="pending",
    )


@router.post(
    "/graphs/{graph_id}/prune-cold-nodes",
    response_model=StoragePruneResponse,
)
async def prune_cold_nodes(
    graph_id: str,
    dry_run: bool = Query(True, description="If true, report what would be pruned without deleting"),
    cold_age_days: int = Query(90, ge=30, le=365),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StoragePruneResponse:
    """Prune cold nodes: level-0 atoms with zero touch_count and no access within cold_age_days."""
    from store.pg.models_faim import NodeModel as _NM

    _require_storage_repos(ctx)
    cutoff = datetime.now(timezone.utc) - timedelta(days=cold_age_days)

    candidates = (
        ctx.session.query(_NM)
        .filter(
            _NM.tenant_id == ctx.tenant_id,
            _NM.graph_id == graph_id,
            _NM.level == 0,
            _NM.touch_count == 0,
            _NM.last_access.is_(None),
            _NM.created_at < cutoff,
            _NM.long_term == False,  # noqa: E712 — long_term nodes are never pruned
        )
        .all()
    )

    scanned = len(candidates)
    pruned = 0

    if not dry_run:
        for node in candidates:
            try:
                ctx.session.delete(node)
                pruned += 1
            except Exception:
                pass
        ctx.session.commit()

        gv = 0
        try:
            gv = ctx.gv_repo.bump(
                session=ctx.session,
                graph_id=graph_id,
                reason=f"prune_cold_nodes_{cold_age_days}d",
            )
        except Exception:
            pass
    else:
        pruned = scanned  # dry run: all candidates qualify

    _storage_lifecycle_log(
        ctx=ctx,
        op="prune_cold_nodes",
        status="dry_run" if dry_run else "completed",
        graph_id=graph_id,
        detail=f"cold_age={cold_age_days}d scanned={scanned} pruned={'(dry)' if dry_run else pruned}",
    )

    return StoragePruneResponse(
        status="dry_run" if dry_run else "ok",
        graph_id=graph_id,
        dry_run=dry_run,
        cold_age_days=cold_age_days,
        scanned=scanned,
        pruned=pruned,
        skipped_level=0,
        skipped_touched=0,
        graph_version=0 if dry_run else gv,
    )


# =============================================================================
# Long-term memory flag — exempt individual nodes from cold pruning
# =============================================================================


@router.post(
    "/graphs/{graph_id}/nodes/{node_id}/long-term",
    response_model=StorageLongTermResponse,
)
async def set_node_long_term(
    graph_id: str,
    node_id: str,
    long_term: bool = Query(True, description="Set to true to protect node from cold pruning"),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageLongTermResponse:
    """Toggle the long_term flag on a node. Long-term nodes are never cold-pruned."""
    from store.pg.models_faim import NodeModel as _NM
    import uuid as _uuid

    _require_storage_repos(ctx)

    try:
        nid = _uuid.UUID(node_id)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid node_id format")

    node = (
        ctx.session.query(_NM)
        .filter(
            _NM.tenant_id == ctx.tenant_id,
            _NM.graph_id == graph_id,
            _NM.node_id == nid,
        )
        .first()
    )
    if node is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Node not found")

    node.long_term = long_term
    ctx.session.commit()

    _storage_lifecycle_log(
        ctx=ctx,
        op="set_long_term",
        status="ok",
        graph_id=graph_id,
        detail=f"node={node_id} long_term={long_term}",
    )

    return StorageLongTermResponse(
        status="ok",
        node_id=node_id,
        graph_id=graph_id,
        long_term=long_term,
    )


# =============================================================================
# K-means clustering — assign topic clusters to all nodes in a graph
# =============================================================================


@router.post(
    "/graphs/{graph_id}/cluster",
    response_model=StorageClusterResponse,
)
async def run_graph_clustering(
    graph_id: str,
    k: Optional[int] = Query(None, ge=2, le=20, description="Number of clusters. Auto-selected if omitted."),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageClusterResponse:
    """Run k-means clustering on all node v_native vectors in the graph.

    Assigns cluster_id to every node. Stores cluster centers in graph_clusters table.
    Subsequent queries scope recall to the top-matching clusters for faster retrieval.
    """
    from store.pg.models_faim import NodeModel as _NM, GraphClusterModel as _GCM
    from core.clustering import run_kmeans

    _require_storage_repos(ctx)

    # Load all nodes with their vectors
    nodes = (
        ctx.session.query(_NM)
        .filter(
            _NM.tenant_id == ctx.tenant_id,
            _NM.graph_id == graph_id,
        )
        .all()
    )

    if len(nodes) < 2:
        return StorageClusterResponse(
            status="skipped",
            graph_id=graph_id,
            k=0,
            nodes_clustered=0,
            iterations=0,
            converged=True,
            cluster_sizes={},
            graph_version=0,
        )

    node_ids = [node.node_id for node in nodes]
    vectors = [
        list(node.v_native) if isinstance(node.v_native, list) else list(node.v_native)
        for node in nodes
    ]

    # Run k-means
    result = run_kmeans(node_ids=node_ids, vectors=vectors, graph_id=graph_id, k=k)

    # Write cluster_id back to each node
    id_to_node = {node.node_id: node for node in nodes}
    for nid, cid in result.assignments.items():
        if nid in id_to_node:
            id_to_node[nid].cluster_id = cid

    # Replace cluster centers for this graph (delete old, insert new)
    ctx.session.query(_GCM).filter(
        _GCM.tenant_id == ctx.tenant_id,
        _GCM.graph_id == graph_id,
    ).delete()

    for ci, center in enumerate(result.centers):
        if center:
            ctx.session.add(_GCM(
                tenant_id=ctx.tenant_id,
                graph_id=graph_id,
                cluster_id=ci,
                center=center,
                node_count=result.cluster_sizes.get(ci, 0),
            ))

    ctx.session.flush()
    gv = 0
    try:
        gv = ctx.gv_repo.bump(
            session=ctx.session,
            graph_id=graph_id,
            reason=f"clustering_k{result.k}",
        )
    except Exception:
        pass
    ctx.session.commit()

    _storage_lifecycle_log(
        ctx=ctx,
        op="run_clustering",
        status="ok",
        graph_id=graph_id,
        detail=f"k={result.k} nodes={len(nodes)} iterations={result.iterations} converged={result.converged}",
    )

    return StorageClusterResponse(
        status="ok",
        graph_id=graph_id,
        k=result.k,
        nodes_clustered=len(nodes),
        iterations=result.iterations,
        converged=result.converged,
        cluster_sizes={str(k): v for k, v in result.cluster_sizes.items()},
        graph_version=gv,
    )


__all__ = ["router"]
