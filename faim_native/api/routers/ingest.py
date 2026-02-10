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
from pydantic import BaseModel

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
    error: Optional[str] = None


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
            },
        )
    ctx.session.commit()


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
            error=result.error,
        )

    except HTTPException:
        if ctx.session:
            ctx.session.rollback()
        raise
    except Exception as e:
        if ctx.session:
            ctx.session.rollback()
        logger.error(f"Ingest failed: {e}")
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
        await validate_upload_file(file)
        file_bytes = await file.read()
        validate_upload_size(len(file_bytes))

        filename = sanitize_filename(file.filename or "upload")
        validate_file_extension(filename)

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
            error=result.error,
        )

    except HTTPException:
        if ctx.session:
            ctx.session.rollback()
        raise
    except Exception as e:
        if ctx.session:
            ctx.session.rollback()
        logger.error(f"Ingest upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


__all__ = ["router"]
