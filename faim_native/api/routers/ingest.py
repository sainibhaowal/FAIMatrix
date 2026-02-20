"""FAIM-Native API: Ingest Router.

POST /v1/ingest - Ingest file into FAIM graph.
"""

from __future__ import annotations

import base64
import binascii
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

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

router = APIRouter(prefix="", tags=["ingest"])


# =============================================================================
# Request/Response Models
# =============================================================================


class IngestRequest(BaseModel):
    """Ingest request body."""

    graph_id: str
    raw_id: Optional[str] = None  # Existing raw_id, or generate new
    filename: str
    bytes_base64: Optional[str] = None  # Alternative to multipart
    content_type: Optional[str] = None
    profile: str = "strict"  # strict, fast, relaxed
    persist_mode: str = "relaxed"  # strict, relaxed


class IngestResponse(BaseModel):
    """Ingest response."""

    status: str
    packet_hash: str
    graph_version: int
    nodes_written: int
    merges: int
    block_count: int
    vector_count: int
    events_emitted: list[str]
    latency_ms: int
    phase_latency_ms: dict[str, int] = Field(default_factory=dict)
    error: Optional[str] = None
    requested_profile: Optional[str] = None
    requested_persist_mode: Optional[str] = None
    effective_profile: Optional[str] = None
    effective_persist_mode: Optional[str] = None
    durability_path: Optional[str] = None
    index_write_mode: Optional[str] = None
    secondary_task_status: Optional[str] = None
    secondary_task_job_id: Optional[str] = None


# =============================================================================
# Helpers
# =============================================================================


def _decode_base64_payload(payload: str) -> bytes:
    """Decode strict base64 payload with clear API errors."""
    try:
        return base64.b64decode(payload, validate=True)
    except (ValueError, binascii.Error) as e:
        raise HTTPException(status_code=400, detail="Invalid bytes_base64 payload") from e


def _parse_uuid(raw_id: str) -> UUID:
    """Parse UUID or raise HTTP 400."""
    try:
        return UUID(str(raw_id).strip())
    except (ValueError, TypeError, AttributeError) as e:
        raise HTTPException(status_code=400, detail="raw_id must be a valid UUID") from e


def _encryption_enabled() -> bool:
    mode = os.getenv("FAIM_PAYLOAD_CIPHER", "").strip().lower()
    if mode in {"fernet", "envelope"}:
        return True
    raw = os.getenv("FAIM_ENCRYPTION_AT_REST", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _emit_storage_audit_event(
    *,
    ctx: FAIMContext,
    graph_id: str,
    kind: str,
    payload: dict[str, Any],
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


def _normalize_failure_reason(error: Optional[str]) -> str:
    text_value = str(error or "").strip().lower()
    if not text_value:
        return "unknown"
    if "mime" in text_value and "extension" in text_value:
        return "mime_extension_mismatch"
    if "upload file too large" in text_value or "file size exceeds" in text_value:
        return "upload_oversize"
    if "unsupported file extension" in text_value:
        return "unsupported_extension"
    if "path separators" in text_value:
        return "path_traversal_filename"
    if "encrypt" in text_value or "decrypt" in text_value:
        return "encryption_error"
    if "raw_id" in text_value or "uuid" in text_value:
        return "raw_id_contract_error"
    if "extract" in text_value:
        return "extract_error"
    return "ingest_error"


def _ingest_lifecycle_log(
    *,
    ctx: FAIMContext,
    op: str,
    status: str,
    graph_id: Optional[str],
    raw_id: Optional[str] = None,
    latency_ms: Optional[int] = None,
    failure_reason: Optional[str] = None,
    detail: Optional[str] = None,
    level: str = "info",
) -> None:
    try:
        from runtime.feature_flags import get_feature_flags

        if not get_feature_flags().storage_structured_lifecycle_logs:
            return
    except Exception:
        pass

    extra: dict[str, Any] = {
        "request_id": ctx.request_id,
        "tenant_id": ctx.tenant_id,
        "graph_id": graph_id,
        "raw_id": raw_id,
        "op": op,
        "status": status,
        "failure_reason": failure_reason,
    }
    if latency_ms is not None:
        extra["latency_ms"] = int(latency_ms)
    payload = {k: v for k, v in extra.items() if v is not None}
    log_fn = getattr(logger, level, logger.info)
    log_fn(detail or f"ingest.lifecycle op={op} status={status}", extra=payload)


def _persist_raw_upload(
    *,
    ctx: FAIMContext,
    graph_id: str,
    file_bytes: bytes,
    mime_type: str,
    supplied_raw_id: Optional[str] = None,
) -> str:
    """Persist raw bytes to immutable blob store + raw_refs table."""
    if supplied_raw_id is not None:
        _parse_uuid(supplied_raw_id)

    if not ctx.raw_repo or not ctx.session:
        raise HTTPException(status_code=500, detail="Raw storage repository is not available")

    store = ctx.raw_store
    if store is None:
        env = os.getenv("FAIM_ENV", "").strip().lower()
        if env in {"prod", "production"}:
            raise HTTPException(
                status_code=500,
                detail="Raw store is unavailable in production mode",
            )
        from store.raw.raw_store import RawStore

        fallback = Path(__file__).resolve().parents[2] / "store" / "raw" / "blobs"
        store = RawStore(fallback)

    try:
        raw_ref = store.store(file_bytes, mime_type=mime_type, graph_id=graph_id)
    except Exception as exc:
        if _encryption_enabled():
            _emit_storage_audit_event(
                ctx=ctx,
                graph_id=graph_id,
                kind="STORAGE_ENCRYPT_FAILED",
                payload={
                    "filename": "ingest_upload",
                    "mime_type": mime_type,
                    "size_bytes": len(file_bytes),
                    "error": str(exc),
                },
                commit=True,
            )
        raise

    saved_ref = ctx.raw_repo.create(ctx.session, raw_ref)
    _emit_storage_audit_event(
        ctx=ctx,
        graph_id=graph_id,
        kind="STORAGE_RAW_STORED",
        payload={
            "raw_id": str(saved_ref.id),
            "sha256": str(saved_ref.sha256),
            "mime_type": mime_type,
            "size_bytes": len(file_bytes),
        },
    )
    ctx.session.commit()

    persisted_raw_id = str(saved_ref.id)
    if supplied_raw_id and supplied_raw_id.strip() and supplied_raw_id.strip() != persisted_raw_id:
        logger.warning(
            "Supplied raw_id does not match persisted raw reference; using persisted raw_id"
        )

    return persisted_raw_id


def _track_storage_ingest_start(
    *,
    ctx: FAIMContext,
    graph_id: str,
    raw_id: str,
    filename: str,
    mime_type: str,
    size_bytes: int,
) -> None:
    """Record upload metadata in storage catalog when repo is available."""
    if not ctx.storage_file_repo or not ctx.raw_repo or not ctx.session:
        return

    raw_uuid = _parse_uuid(raw_id)
    raw_ref = ctx.raw_repo.get_by_id(ctx.session, raw_uuid)
    if raw_ref is None:
        return

    ctx.storage_file_repo.upsert_upload(
        ctx.session,
        graph_id=graph_id,
        raw_id=raw_uuid,
        filename=filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        sha256=str(raw_ref.sha256),
        job_id=None,
    )
    ctx.storage_file_repo.mark_ingesting(
        ctx.session,
        raw_id=raw_uuid,
        graph_id=graph_id,
        job_id=None,
    )
    ctx.session.commit()


def _track_storage_ingest_result(
    *,
    ctx: FAIMContext,
    graph_id: str,
    raw_id: str,
    result: Any,
) -> None:
    """Update storage catalog ingest status when repo is available."""
    if not ctx.storage_file_repo or not ctx.session:
        return

    raw_uuid = _parse_uuid(raw_id)
    ctx.storage_file_repo.mark_ingest_result(
        ctx.session,
        raw_id=raw_uuid,
        graph_id=graph_id,
        status=result.status,
        packet_hash=result.packet_hash or None,
        node_count=result.nodes_written,
        vector_count=result.vector_count,
        error_message=result.error,
        job_id=None,
    )
    if result.status == "dedup_hit":
        _emit_storage_audit_event(
            ctx=ctx,
            graph_id=graph_id,
            kind="STORAGE_DEDUP_HIT",
            payload={
                "raw_id": raw_id,
                "packet_hash": result.packet_hash,
                "requested_profile": getattr(result, "requested_profile", None),
                "requested_persist_mode": getattr(result, "requested_persist_mode", None),
                "effective_profile": getattr(result, "effective_profile", None),
                "effective_persist_mode": getattr(result, "effective_persist_mode", None),
                "durability_path": getattr(result, "durability_path", None),
            },
        )
    elif result.status == "error":
        _emit_storage_audit_event(
            ctx=ctx,
            graph_id=graph_id,
            kind="STORAGE_EXTRACT_FAILED",
            payload={
                "raw_id": raw_id,
                "error": result.error,
                "requested_profile": getattr(result, "requested_profile", None),
                "requested_persist_mode": getattr(result, "requested_persist_mode", None),
                "effective_profile": getattr(result, "effective_profile", None),
                "effective_persist_mode": getattr(result, "effective_persist_mode", None),
                "durability_path": getattr(result, "durability_path", None),
            },
        )
    ctx.session.commit()


def _maybe_enqueue_self_evolve(
    *,
    ctx: FAIMContext,
    graph_id: str,
    source: str,
    profile: str,
    persist_mode: str,
) -> None:
    """Best-effort shared self-evolve enqueue after successful ingest writes."""
    try:
        from orchestration.self_evolve_scheduler import enqueue_self_evolve_if_due

        result = enqueue_self_evolve_if_due(
            session=ctx.session,
            tenant_id=ctx.tenant_id,
            graph_id=graph_id,
            source=source,
            request_id=ctx.request_id,
            profile=profile,
            persist_mode=persist_mode,
            self_invent_requested=None,
        )
        if result.job_id is None:
            return
        logger.info(
            "self-evolve scheduler decision source=%s status=%s reason=%s graph=%s job=%s",
            source,
            result.status,
            result.reason,
            graph_id,
            result.job_id,
        )
    except Exception as exc:  # nosec B110
        logger.warning("Shared self-evolve enqueue skipped due to error: %s", exc)


# =============================================================================
# Ingest Endpoint
# =============================================================================


@router.post("/ingest", response_model=IngestResponse)
async def ingest_file(
    request: IngestRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> IngestResponse:
    """Ingest a file into the FAIM graph.

    Uses Stage-1 raw ingest, then orchestration.run_ingest().

    Returns packet_hash (idempotency key), graph_version, and events.
    """
    try:
        _ingest_lifecycle_log(
            ctx=ctx,
            op="ingest_json",
            status="started",
            graph_id=request.graph_id,
            detail="json ingest request started",
        )
        # Decode file bytes
        if not request.bytes_base64:
            raise HTTPException(
                status_code=400,
                detail="Must provide bytes_base64 or use multipart upload",
            )
        file_bytes = _decode_base64_payload(request.bytes_base64)

        # Security validation
        filename = sanitize_filename(request.filename)
        validate_file_extension(filename)
        validate_content_type(request.content_type)
        validate_mime_extension_match(filename, request.content_type)
        validate_upload_size(len(file_bytes))

        mime_type = (request.content_type or "application/octet-stream").split(";")[
            0
        ].strip()

        # Persist raw bytes before orchestration
        raw_id = _persist_raw_upload(
            ctx=ctx,
            graph_id=request.graph_id,
            file_bytes=file_bytes,
            mime_type=mime_type,
            supplied_raw_id=request.raw_id,
        )
        _track_storage_ingest_start(
            ctx=ctx,
            graph_id=request.graph_id,
            raw_id=raw_id,
            filename=filename,
            mime_type=mime_type,
            size_bytes=len(file_bytes),
        )

        # Import orchestration
        from orchestration.ingest_flow import FAIMProfile, PersistMode, run_ingest

        # Map profile/persist_mode
        try:
            profile = FAIMProfile(request.profile.lower())
            persist_mode = PersistMode(request.persist_mode.lower())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        # Run ingest
        result = run_ingest(
            graph_id=request.graph_id,
            raw_id=raw_id,
            filename=filename,
            file_bytes=file_bytes,
            profile=profile,
            persist_mode=persist_mode,
            tenant_id=ctx.tenant_id,
            session=ctx.session,
            node_repo=ctx.node_repo,
            edge_repo=ctx.edge_repo,
            event_repo=ctx.event_repo,
            gv_repo=ctx.gv_repo,
        )
        _track_storage_ingest_result(
            ctx=ctx,
            graph_id=request.graph_id,
            raw_id=raw_id,
            result=result,
        )
        if result.status in {"completed", "dedup_hit"}:
            _maybe_enqueue_self_evolve(
                ctx=ctx,
                graph_id=request.graph_id,
                source="ingest_json",
                profile=profile.value,
                persist_mode=persist_mode.value,
            )
        _ingest_lifecycle_log(
            ctx=ctx,
            op="ingest_json",
            status=result.status,
            graph_id=request.graph_id,
            raw_id=raw_id,
            latency_ms=result.latency_ms,
            failure_reason=(
                _normalize_failure_reason(result.error) if result.error else None
            ),
            detail="json ingest completed",
        )

        return IngestResponse(
            status=result.status,
            packet_hash=result.packet_hash,
            graph_version=result.graph_version,
            nodes_written=result.nodes_written,
            merges=result.merges,
            block_count=result.block_count,
            vector_count=result.vector_count,
            events_emitted=result.events_emitted,
            latency_ms=result.latency_ms,
            phase_latency_ms=result.phase_latency_ms,
            error=result.error,
            requested_profile=result.requested_profile,
            requested_persist_mode=result.requested_persist_mode,
            effective_profile=result.effective_profile,
            effective_persist_mode=result.effective_persist_mode,
            durability_path=result.durability_path,
            index_write_mode=result.index_write_mode,
            secondary_task_status=result.secondary_task_status,
            secondary_task_job_id=result.secondary_task_job_id,
        )

    except HTTPException:
        if ctx.session:
            ctx.session.rollback()
        _ingest_lifecycle_log(
            ctx=ctx,
            op="ingest_json",
            status="failed",
            graph_id=request.graph_id,
            failure_reason="http_error",
            detail="json ingest failed with http exception",
            level="warning",
        )
        raise
    except Exception as e:
        if ctx.session:
            ctx.session.rollback()
        logger.error(f"Ingest failed: {e}")
        _ingest_lifecycle_log(
            ctx=ctx,
            op="ingest_json",
            status="failed",
            graph_id=request.graph_id,
            failure_reason=_normalize_failure_reason(str(e)),
            detail="json ingest failed",
            level="error",
        )
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


# =============================================================================
# Multipart Upload
# =============================================================================


@router.post("/ingest/upload", response_model=IngestResponse)
async def ingest_upload(
    graph_id: str = Form(...),
    profile: str = Form("strict"),
    persist_mode: str = Form("relaxed"),
    file: UploadFile = File(...),  # noqa: B008
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> IngestResponse:
    """Ingest a file via multipart upload.

    Alternative to JSON body with bytes_base64.
    """
    try:
        _ingest_lifecycle_log(
            ctx=ctx,
            op="ingest_upload",
            status="started",
            graph_id=graph_id,
            detail="multipart ingest request started",
        )
        await validate_upload_file(file)
        file_bytes = await file.read()
        validate_upload_size(len(file_bytes))

        filename = sanitize_filename(file.filename or "upload")
        validate_file_extension(filename)
        validate_mime_extension_match(filename, file.content_type)

        mime_type = (file.content_type or "application/octet-stream").split(";")[
            0
        ].strip()

        # Persist raw bytes before orchestration
        raw_id = _persist_raw_upload(
            ctx=ctx,
            graph_id=graph_id,
            file_bytes=file_bytes,
            mime_type=mime_type,
            supplied_raw_id=None,
        )
        _track_storage_ingest_start(
            ctx=ctx,
            graph_id=graph_id,
            raw_id=raw_id,
            filename=filename,
            mime_type=mime_type,
            size_bytes=len(file_bytes),
        )

        from orchestration.ingest_flow import FAIMProfile, PersistMode, run_ingest

        try:
            profile_enum = FAIMProfile(profile.lower())
            persist_mode_enum = PersistMode(persist_mode.lower())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        result = run_ingest(
            graph_id=graph_id,
            raw_id=raw_id,
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
        _track_storage_ingest_result(
            ctx=ctx,
            graph_id=graph_id,
            raw_id=raw_id,
            result=result,
        )
        if result.status in {"completed", "dedup_hit"}:
            _maybe_enqueue_self_evolve(
                ctx=ctx,
                graph_id=graph_id,
                source="ingest_upload",
                profile=profile_enum.value,
                persist_mode=persist_mode_enum.value,
            )
        _ingest_lifecycle_log(
            ctx=ctx,
            op="ingest_upload",
            status=result.status,
            graph_id=graph_id,
            raw_id=raw_id,
            latency_ms=result.latency_ms,
            failure_reason=(
                _normalize_failure_reason(result.error) if result.error else None
            ),
            detail="multipart ingest completed",
        )

        return IngestResponse(
            status=result.status,
            packet_hash=result.packet_hash,
            graph_version=result.graph_version,
            nodes_written=result.nodes_written,
            merges=result.merges,
            block_count=result.block_count,
            vector_count=result.vector_count,
            events_emitted=result.events_emitted,
            latency_ms=result.latency_ms,
            phase_latency_ms=result.phase_latency_ms,
            error=result.error,
            requested_profile=result.requested_profile,
            requested_persist_mode=result.requested_persist_mode,
            effective_profile=result.effective_profile,
            effective_persist_mode=result.effective_persist_mode,
            durability_path=result.durability_path,
            index_write_mode=result.index_write_mode,
            secondary_task_status=result.secondary_task_status,
            secondary_task_job_id=result.secondary_task_job_id,
        )

    except HTTPException:
        if ctx.session:
            ctx.session.rollback()
        _ingest_lifecycle_log(
            ctx=ctx,
            op="ingest_upload",
            status="failed",
            graph_id=graph_id,
            failure_reason="http_error",
            detail="multipart ingest failed with http exception",
            level="warning",
        )
        raise
    except Exception as e:
        if ctx.session:
            ctx.session.rollback()
        logger.error(f"Ingest upload failed: {e}")
        _ingest_lifecycle_log(
            ctx=ctx,
            op="ingest_upload",
            status="failed",
            graph_id=graph_id,
            failure_reason=_normalize_failure_reason(str(e)),
            detail="multipart ingest failed",
            level="error",
        )
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


__all__ = ["router"]
