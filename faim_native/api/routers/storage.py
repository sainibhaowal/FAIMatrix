"""FAIM-Native API: Storage Router (P1).

Provides storage upload/catalog APIs used by Storage UI.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import and_, text

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context  # noqa: E402
from api.validators import (  # noqa: E402
    sanitize_filename,
    validate_content_type,
    validate_file_extension,
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
    files: List[UploadFileResult]


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
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    files: List[StorageFileItem]


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


class StorageIngestActionResponse(BaseModel):
    """Response for ingest/retry actions."""

    status: str
    file: StorageFileItem
    ingest: Dict[str, Any]


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

    from store.raw.raw_store import RawStore

    fallback = Path(__file__).resolve().parents[2] / "store" / "raw" / "blobs"
    return RawStore(fallback)


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
        tenant_id=ctx.tenant_id,
        session=ctx.session,
        node_repo=ctx.node_repo,
        edge_repo=ctx.edge_repo,
        event_repo=ctx.event_repo,
        gv_repo=ctx.gv_repo,
    )
    return result


# =============================================================================
# Upload + Jobs
# =============================================================================


@router.post("/uploads", response_model=StorageUploadBatchResponse)
async def create_upload_batch(
    graph_id: str = Form(...),
    profile: str = Form("strict"),
    persist_mode: str = Form("relaxed"),
    files: List[UploadFile] = File(...),  # noqa: B008
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageUploadBatchResponse:
    """Upload and ingest one or many files in a single batch."""
    _require_storage_repos(ctx)

    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    from orchestration.jobs.job_store import JobStore

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
        },
    )

    file_results: List[UploadFileResult] = []
    processed = 0
    success = 0
    failed = 0
    dedup_hits = 0

    try:
        JobStore.append_event(
            ctx.session,
            job_id,
            "step_start",
            {
                "message": "Storage upload batch started",
                "requested_files": requested_files,
            },
        )

        for index, upload in enumerate(files):
            filename = sanitize_filename(upload.filename or f"upload-{index + 1}")
            result_entry = UploadFileResult(filename=filename, status="pending")
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

                saved_ref = _store_raw_upload(
                    ctx=ctx,
                    graph_id=graph_id,
                    file_bytes=file_bytes,
                    mime_type=mime_type,
                )
                raw_uuid = _parse_uuid(str(saved_ref.id), "raw_id")

                row = ctx.storage_file_repo.upsert_upload(
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
                ctx.session.commit()

                JobStore.append_event(
                    ctx.session,
                    job_id,
                    "step_progress",
                    {
                        "index": index,
                        "filename": filename,
                        "raw_id": str(raw_uuid),
                        "message": "Ingest started",
                    },
                )

                ingest_result = _run_ingest_existing_raw(
                    ctx=ctx,
                    graph_id=graph_id,
                    raw_id=raw_uuid,
                    filename=filename,
                    file_bytes=file_bytes,
                    profile=profile,
                    persist_mode=persist_mode,
                )

                row = ctx.storage_file_repo.mark_ingest_result(
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
                ctx.session.commit()

                processed += 1
                result_entry.raw_id = str(raw_uuid)
                result_entry.packet_hash = ingest_result.packet_hash or None
                result_entry.node_count = ingest_result.nodes_written
                result_entry.vector_count = ingest_result.vector_count

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
                        "message": "Ingest finished",
                    },
                )
            except HTTPException as e:
                processed += 1
                failed += 1
                result_entry.status = "failed"
                result_entry.error = str(e.detail)
                ctx.session.rollback()
                JobStore.append_event(
                    ctx.session,
                    job_id,
                    "step_progress",
                    {
                        "index": index,
                        "filename": filename,
                        "status": "failed",
                        "error": result_entry.error,
                    },
                )
            except Exception as e:
                processed += 1
                failed += 1
                result_entry.status = "failed"
                result_entry.error = str(e)
                ctx.session.rollback()
                JobStore.append_event(
                    ctx.session,
                    job_id,
                    "step_progress",
                    {
                        "index": index,
                        "filename": filename,
                        "status": "failed",
                        "error": str(e),
                    },
                )

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
                }
            )
            job.payload_json = payload
            job.updated_at = datetime.now(timezone.utc)
            if final_status == "failed":
                job.status = "failed"
                job.error_message = "All files failed ingestion"
                job.completed_at = datetime.now(timezone.utc)
            else:
                job.status = "done"
                job.completed_at = datetime.now(timezone.utc)
            ctx.session.commit()

        return StorageUploadBatchResponse(
            job_id=str(job_id),
            graph_id=graph_id,
            status=final_status,
            requested_files=requested_files,
            processed_files=processed,
            success_files=success,
            failed_files=failed,
            dedup_hits=dedup_hits,
            files=file_results,
        )
    except HTTPException:
        ctx.session.rollback()
        raise
    except Exception as e:
        logger.error(f"Storage upload batch failed: {e}")
        ctx.session.rollback()
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

    requested_files = int((job.payload_json or {}).get("requested_files", processed_files))

    return StorageUploadStatusResponse(
        job_id=str(job.job_id),
        graph_id=job.graph_id,
        status=job.status,
        requested_files=requested_files,
        processed_files=processed_files,
        success_files=success_files,
        failed_files=failed_files,
        dedup_hits=dedup_hits,
        created_at=job.created_at.isoformat() if job.created_at else None,
        updated_at=job.updated_at.isoformat() if job.updated_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        files=file_items,
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

    if ctx.event_repo:
        try:
            ctx.event_repo.emit(
                ctx.session,
                graph_id,
                "STORAGE_DELETE_REQUESTED",
                {
                    "raw_id": str(raw_uuid),
                    "reason": reason,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to emit delete-request event: {e}")

    ctx.session.commit()
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
    ctx.session.commit()

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
            "error": ingest_result.error,
        },
    )


@router.post("/files/{raw_id}/retry", response_model=StorageIngestActionResponse)
async def retry_storage_file(
    raw_id: str,
    graph_id: Optional[str] = Query(None),
    profile: str = Query("strict"),
    persist_mode: str = Query("relaxed"),
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

    return await reingest_storage_file(
        raw_id=raw_id,
        graph_id=graph_id,
        profile=profile,
        persist_mode=persist_mode,
        ctx=ctx,
    )


# =============================================================================
# Summary + Health
# =============================================================================


@router.get("/summary", response_model=StorageSummaryResponse)
async def get_storage_summary(
    graph_id: Optional[str] = Query(None),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageSummaryResponse:
    """Get storage summary metrics."""
    _require_storage_repos(ctx)

    summary = ctx.storage_file_repo.summary(ctx.session, graph_id=graph_id)
    return StorageSummaryResponse(graph_id=graph_id, **summary)


@router.get("/backends/health", response_model=StorageBackendsHealth)
async def get_storage_backends_health(
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> StorageBackendsHealth:
    """Check operational storage backend health."""
    _require_storage_repos(ctx)

    postgres_ok = False
    raw_store_ok = False

    try:
        ctx.session.execute(text("SELECT 1"))
        postgres_ok = True
    except Exception:
        postgres_ok = False

    try:
        store = _resolve_raw_store(ctx)
        _ = store.get_stats()
        raw_store_ok = True
    except Exception:
        raw_store_ok = False

    try:
        from cache.query_cache import is_redis_available

        redis_ok = bool(is_redis_available())
    except Exception:
        redis_ok = False

    try:
        from index.qdrant_index import is_qdrant_available

        qdrant_ok = bool(is_qdrant_available())
    except Exception:
        qdrant_ok = False

    return StorageBackendsHealth(
        postgres=postgres_ok,
        redis=redis_ok,
        qdrant=qdrant_ok,
        raw_store=raw_store_ok,
    )


__all__ = ["router"]
