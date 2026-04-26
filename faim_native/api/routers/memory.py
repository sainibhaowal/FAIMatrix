"""FAIM-Native API: Agent-facing memory router (K5)."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import and_, text
from sqlalchemy.exc import OperationalError

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context, require_scopes  # noqa: E402
from api.services.memory_service import (  # noqa: E402
    build_write_request_hash,
    decode_base64_payload,
    normalize_datetime_utc,
    parse_idempotency_key,
    redact_error_text,
)
from api.validators import (  # noqa: E402
    sanitize_filename,
    validate_content_type,
    validate_file_extension,
    validate_mime_extension_match,
    validate_upload_size,
)
from orchestration.ingest_flow import FAIMProfile, PersistMode, run_ingest  # noqa: E402
from store.pg.models_faim import IngestDedupModel, NodeModel  # noqa: E402
from store.pg.repos.memory_write_idempotency_repo import (  # noqa: E402
    MemoryWriteIdempotencyRepo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


# =============================================================================
# Contracts
# =============================================================================


class MemorySearchRequest(BaseModel):
    graph_id: str
    query_text: str
    k: int = Field(10, ge=1, le=100)
    profile: str = Field("strict")
    return_explain: bool = Field(False)


class MemorySearchResult(BaseModel):
    node_id: str
    vector_hash: str
    score: float
    score_components: Dict[str, float]
    level: int
    touch_count: int
    evidence: Optional[Dict[str, Any]] = None
    explain: Optional[Dict[str, Any]] = None


class MemorySearchResponse(BaseModel):
    tenant_id: str
    graph_id: str
    graph_version: int
    graph_hash: str
    query_hash: str
    k: int
    profile: str
    results: List[MemorySearchResult]
    answer: Optional[Dict[str, Any]] = None
    metrics: Dict[str, float]
    duration_ms: float


class MemoryItemResponse(BaseModel):
    node_id: str
    graph_id: str
    kind: str
    level: int
    vector_hash: str
    residual: float
    touch_count: int
    raw_id: Optional[str] = None
    block_id: Optional[str] = None
    anchor: Optional[Dict[str, Any]] = None
    opp_signature: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MemoryProvenanceRawRef(BaseModel):
    raw_id: str
    sha256: str
    uri: str
    mime_type: str
    size_bytes: int
    created_at: Optional[str] = None


class MemoryProvenanceParent(BaseModel):
    parent_id: str
    fraction: float
    kind: str


class MemoryProvenanceDedup(BaseModel):
    packet_hash: Optional[str] = None
    dedup_record_found: bool = False
    dedup_raw_id: Optional[str] = None
    dedup_node_count: int = 0
    dedup_created_at: Optional[str] = None


class MemoryProvenanceEvent(BaseModel):
    seq: int
    kind: str
    ts: Optional[str] = None
    payload_keys: List[str]


class MemoryProvenanceResponse(BaseModel):
    node: MemoryItemResponse
    raw_ref: Optional[MemoryProvenanceRawRef] = None
    dedup: MemoryProvenanceDedup
    parents: List[MemoryProvenanceParent]
    events: List[MemoryProvenanceEvent]


class MemoryWriteRequest(BaseModel):
    graph_id: str
    text: Optional[str] = None
    bytes_base64: Optional[str] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None
    profile: str = "strict"
    persist_mode: str = "relaxed"
    idempotency_key: Optional[str] = None


class MemoryWriteResponse(BaseModel):
    status: str
    raw_id: str
    packet_hash: str
    graph_version: int
    nodes_written: int
    merges: int
    block_count: int
    vector_count: int
    events_emitted: List[str]
    latency_ms: int
    phase_latency_ms: Dict[str, int]
    error: Optional[str] = None
    requested_profile: Optional[str] = None
    requested_persist_mode: Optional[str] = None
    effective_profile: Optional[str] = None
    effective_persist_mode: Optional[str] = None
    durability_path: Optional[str] = None
    index_write_mode: Optional[str] = None
    secondary_task_status: Optional[str] = None
    secondary_task_job_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    replayed: bool = False


class MemoryPatchRequest(BaseModel):
    graph_id: str
    expected_updated_at: Optional[datetime] = None
    kind: Optional[str] = None
    level: Optional[int] = Field(default=None, ge=0, le=128)
    residual: Optional[float] = None
    anchor: Optional[Dict[str, Any]] = None
    opp_signature: Optional[Dict[str, Any]] = None


# =============================================================================
# Helpers
# =============================================================================


def _parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(str(value).strip())
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a valid UUID",
        ) from exc


def _parse_optional_uuid(value: Optional[str]) -> Optional[UUID]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return UUID(text)
    except (ValueError, TypeError, AttributeError):
        return None


def _profile_enum(value: str) -> FAIMProfile:
    try:
        return FAIMProfile(str(value or "").strip().lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid profile: {value}"
        ) from exc


def _persist_mode_enum(value: str) -> PersistMode:
    try:
        return PersistMode(str(value or "").strip().lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid persist_mode: {value}"
        ) from exc


def _node_to_item(node: NodeModel) -> MemoryItemResponse:
    return MemoryItemResponse(
        node_id=str(node.node_id),
        graph_id=node.graph_id,
        kind=node.kind,
        level=int(node.level or 0),
        vector_hash=node.vector_hash,
        residual=(node.residual or 0) / 1e9 if node.residual is not None else 0.0,
        touch_count=int(node.touch_count or 0),
        raw_id=node.raw_id,
        block_id=node.block_id,
        anchor=node.anchor_json,
        opp_signature=node.opp_signature,
        created_at=node.created_at.isoformat() if node.created_at else None,
        updated_at=node.updated_at.isoformat() if node.updated_at else None,
    )


def _resolve_write_payload(body: MemoryWriteRequest) -> tuple[str, str, bytes]:
    has_text = body.text is not None
    has_bytes = body.bytes_base64 is not None

    if has_text and has_bytes:
        raise HTTPException(
            status_code=400,
            detail="Provide either text or bytes_base64, not both",
        )
    if not has_text and not has_bytes:
        raise HTTPException(
            status_code=400,
            detail="Provide either text or bytes_base64",
        )

    if has_text:
        payload_bytes = body.text.encode("utf-8")
        filename = sanitize_filename(body.filename or "memory.txt")
        content_type = body.content_type or "text/plain"
    else:
        try:
            payload_bytes = decode_base64_payload(body.bytes_base64 or "")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        filename = sanitize_filename(body.filename or "memory.bin")
        content_type = body.content_type or "application/octet-stream"

    base_type = content_type.split(";")[0].strip().lower()
    validate_file_extension(filename)
    validate_content_type(base_type)
    validate_mime_extension_match(filename, base_type)
    validate_upload_size(len(payload_bytes))

    return filename, base_type, payload_bytes


def _configure_mutation_lock_timeout(ctx: FAIMContext) -> None:
    """Bound lock waits so concurrent writes fail fast instead of hanging."""
    if ctx.session is None:
        return
    bind = ctx.session.get_bind()
    dialect = getattr(getattr(bind, "dialect", None), "name", "")
    if dialect == "postgresql":
        # Transaction-local lock timeout for this request only.
        ctx.session.execute(text("SET LOCAL lock_timeout = '3s'"))
    elif dialect == "sqlite":
        # Keep SQLite lock wait bounded for local acceptance runs.
        ctx.session.execute(text("PRAGMA busy_timeout = 3000"))


def _is_lock_conflict(exc: OperationalError) -> bool:
    message = str(exc).lower()
    markers = (
        "database is locked",
        "lock timeout",
        "could not obtain lock",
        "deadlock detected",
    )
    return any(marker in message for marker in markers)


def _run_memory_write(
    *,
    ctx: FAIMContext,
    graph_id: str,
    filename: str,
    content_type: str,
    payload_bytes: bytes,
    profile: FAIMProfile,
    persist_mode: PersistMode,
) -> tuple[str, Any]:
    # Reuse existing ingest router helpers to preserve storage/validator/audit behavior.
    from api.routers.ingest import (
        _persist_raw_upload,
        _track_storage_ingest_result,
        _track_storage_ingest_start,
    )

    raw_id = _persist_raw_upload(
        ctx=ctx,
        graph_id=graph_id,
        file_bytes=payload_bytes,
        mime_type=content_type,
        supplied_raw_id=None,
    )
    _track_storage_ingest_start(
        ctx=ctx,
        graph_id=graph_id,
        raw_id=raw_id,
        filename=filename,
        mime_type=content_type,
        size_bytes=len(payload_bytes),
    )

    ingest_result = run_ingest(
        graph_id=graph_id,
        raw_id=raw_id,
        filename=filename,
        file_bytes=payload_bytes,
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
        graph_id=graph_id,
        raw_id=raw_id,
        result=ingest_result,
    )
    return raw_id, ingest_result


def _maybe_enqueue_self_evolve(
    *,
    ctx: FAIMContext,
    graph_id: str,
    profile: str,
    persist_mode: str,
) -> None:
    """Best-effort shared self-evolve enqueue for memory write success path."""
    try:
        from orchestration.self_evolve_scheduler import enqueue_self_evolve_if_due

        result = enqueue_self_evolve_if_due(
            session=ctx.session,
            tenant_id=ctx.tenant_id,
            graph_id=graph_id,
            source="memory_write",
            request_id=ctx.request_id,
            profile=profile,
            persist_mode=persist_mode,
            self_invent_requested=None,
        )
        if result.job_id is None:
            return
        logger.info(
            "self-evolve scheduler decision source=memory_write status=%s reason=%s graph=%s job=%s",
            result.status,
            result.reason,
            graph_id,
            result.job_id,
        )
    except Exception as exc:  # nosec B110
        logger.warning("Shared self-evolve enqueue skipped due to error: %s", exc)


# =============================================================================
# Routes
# =============================================================================


@router.post(
    "/search",
    response_model=MemorySearchResponse,
    dependencies=[Depends(require_scopes(["memory.read"]))],
)
async def memory_search(
    body: MemorySearchRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> MemorySearchResponse:
    from orchestration.query_flow import run_query

    profile = _profile_enum(body.profile)

    try:
        result = run_query(
            session=ctx.session,
            tenant_id=ctx.tenant_id,
            graph_id=body.graph_id,
            query_text=body.query_text,
            k=body.k,
            profile=profile,
            return_explain=body.return_explain,
            index=ctx.index if profile != FAIMProfile.STRICT else None,
            cache=ctx.cache,
        )
        # Query flow mutates usage metrics/events (touch_count), so persist it.
        ctx.session.commit()
        return MemorySearchResponse(
            tenant_id=ctx.tenant_id,
            graph_id=result.graph_id,
            graph_version=result.graph_version,
            graph_hash=result.graph_hash,
            query_hash=result.query_hash,
            k=result.k,
            profile=profile.value,
            results=[
                MemorySearchResult(
                    node_id=item["node_id"],
                    vector_hash=item["vector_hash"],
                    score=item["score"],
                    score_components=item["score_components"],
                    level=item["level"],
                    touch_count=item["touch_count"],
                    evidence=item.get("evidence"),
                    explain=item.get("explain"),
                )
                for item in result.results
            ],
            answer=result.answer,
            metrics=result.metrics,
            duration_ms=result.duration_ms,
        )
    except HTTPException:
        if ctx.session is not None:
            ctx.session.rollback()
        raise
    except Exception as exc:
        if ctx.session is not None:
            ctx.session.rollback()
        logger.error("memory search failed: %s", exc)
        raise HTTPException(status_code=500, detail="Memory search failed") from exc


@router.get(
    "/{node_id}",
    response_model=MemoryItemResponse,
    dependencies=[Depends(require_scopes(["memory.read"]))],
)
async def get_memory_item(
    node_id: str,
    graph_id: str,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> MemoryItemResponse:
    node = ctx.node_repo.get_by_id(graph_id, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return _node_to_item(node)


@router.get(
    "/{node_id}/provenance",
    response_model=MemoryProvenanceResponse,
    dependencies=[Depends(require_scopes(["memory.read"]))],
)
async def get_memory_provenance(
    node_id: str,
    graph_id: str,
    limit_events: int = Query(default=50, ge=1, le=500),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> MemoryProvenanceResponse:
    node = ctx.node_repo.get_by_id(graph_id, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Memory item not found")

    node_uuid = _parse_uuid(node_id, "node_id")
    raw_uuid = _parse_optional_uuid(node.raw_id)

    raw_ref_model: Optional[MemoryProvenanceRawRef] = None
    dedup = MemoryProvenanceDedup()

    if raw_uuid is not None and ctx.raw_repo:
        raw_ref = ctx.raw_repo.get_by_id(ctx.session, raw_uuid)
        if raw_ref is not None:
            raw_ref_model = MemoryProvenanceRawRef(
                raw_id=str(raw_ref.id),
                sha256=str(raw_ref.sha256),
                uri=str(raw_ref.uri),
                mime_type=str(raw_ref.mime_type),
                size_bytes=int(raw_ref.size_bytes),
                created_at=(
                    raw_ref.created_at.isoformat() if raw_ref.created_at else None
                ),
            )

    if raw_uuid is not None and ctx.storage_file_repo:
        storage_row = ctx.storage_file_repo.get_by_raw_id(
            ctx.session, raw_uuid, graph_id
        )
        if storage_row and storage_row.packet_hash:
            dedup_record = IngestDedupModel.check_exists(
                ctx.session,
                ctx.tenant_id,
                graph_id,
                storage_row.packet_hash,
            )
            dedup = MemoryProvenanceDedup(
                packet_hash=storage_row.packet_hash,
                dedup_record_found=dedup_record is not None,
                dedup_raw_id=(
                    str(dedup_record.raw_id)
                    if dedup_record is not None and dedup_record.raw_id
                    else None
                ),
                dedup_node_count=int(getattr(dedup_record, "node_count", 0) or 0),
                dedup_created_at=(
                    dedup_record.created_at.isoformat()
                    if dedup_record is not None and dedup_record.created_at
                    else None
                ),
            )

    parents = []
    try:
        parent_edges = ctx.edge_repo.get_parents(graph_id, node_uuid)
        for edge in parent_edges:
            parent_node = ctx.node_repo.get_by_id(graph_id, edge.src_node_id)
            parents.append(
                MemoryProvenanceParent(
                    parent_id=str(edge.src_node_id),
                    fraction=(edge.weight or 0) / 1e9,
                    kind=parent_node.kind if parent_node else "unknown",
                )
            )
    except Exception as exc:  # nosec B110
        logger.warning("Failed to load memory parents for node=%s: %s", node_id, exc)

    events: List[MemoryProvenanceEvent] = []
    if ctx.event_repo:
        try:
            all_events = ctx.event_repo.get_by_seq(
                ctx.session,
                graph_id=graph_id,
                after_seq=0,
                limit=max(limit_events * 4, 100),
            )
            raw_id_text = str(raw_uuid) if raw_uuid else ""
            for event in reversed(all_events):
                payload = event.payload or {}
                payload_raw_id = str(payload.get("raw_id", "")).strip()
                payload_node_id = str(payload.get("node_id", "")).strip()
                if payload_node_id == str(node_uuid) or (
                    raw_id_text and payload_raw_id == raw_id_text
                ):
                    events.append(
                        MemoryProvenanceEvent(
                            seq=int(event.seq),
                            kind=event.kind,
                            ts=event.ts.isoformat() if event.ts else None,
                            payload_keys=sorted([str(k) for k in payload.keys()]),
                        )
                    )
                if len(events) >= limit_events:
                    break
        except Exception as exc:  # nosec B110
            logger.warning("Failed to load memory provenance events: %s", exc)

    return MemoryProvenanceResponse(
        node=_node_to_item(node),
        raw_ref=raw_ref_model,
        dedup=dedup,
        parents=parents,
        events=events,
    )


@router.post(
    "/write",
    response_model=MemoryWriteResponse,
    dependencies=[Depends(require_scopes(["memory.write"]))],
)
async def write_memory(
    body: MemoryWriteRequest,
    request: Request,
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> MemoryWriteResponse:
    filename, content_type, payload_bytes = _resolve_write_payload(body)
    profile = _profile_enum(body.profile)
    persist_mode = _persist_mode_enum(body.persist_mode)

    try:
        idempotency_key = parse_idempotency_key(
            header_value=idempotency_key_header,
            body_value=body.idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    idem_repo = MemoryWriteIdempotencyRepo(ctx.session, tenant_id=ctx.tenant_id)
    idem_record = None
    request_hash = None

    if idempotency_key:
        request_hash = build_write_request_hash(
            graph_id=body.graph_id,
            filename=filename,
            content_type=content_type,
            payload_bytes=payload_bytes,
            profile=profile.value,
            persist_mode=persist_mode.value,
        )
        begin_result = idem_repo.begin(
            ctx.session,
            graph_id=body.graph_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        begin_state = begin_result.state
        idem_record = begin_result.record

        if begin_state == "new":
            # Persist lock record before executing the heavy write path.
            ctx.session.commit()
            idem_record = idem_repo.get(
                ctx.session,
                graph_id=body.graph_id,
                idempotency_key=idempotency_key,
            )
            if idem_record is None:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to persist idempotency record",
                )

        if begin_state == "conflict_payload":
            raise HTTPException(
                status_code=409,
                detail=(
                    "idempotency_key already used with different payload; "
                    "use a new idempotency key"
                ),
            )
        if begin_state == "in_progress":
            raise HTTPException(
                status_code=409,
                detail="A write request with this idempotency key is already in progress",
            )
        if begin_state == "failed":
            raise HTTPException(
                status_code=409,
                detail=(
                    "This idempotency key maps to a failed request. "
                    "Use a new idempotency key to retry."
                ),
            )
        if begin_state == "replay":
            stored = begin_result.record.response_json
            if not isinstance(stored, dict):
                raise HTTPException(
                    status_code=409,
                    detail="Stored idempotent response is unavailable for replay",
                )
            replay_payload = dict(stored)
            replay_payload["idempotency_key"] = idempotency_key
            replay_payload["replayed"] = True
            return MemoryWriteResponse(**replay_payload)

    try:
        raw_id, ingest_result = _run_memory_write(
            ctx=ctx,
            graph_id=body.graph_id,
            filename=filename,
            content_type=content_type,
            payload_bytes=payload_bytes,
            profile=profile,
            persist_mode=persist_mode,
        )
        if ingest_result.status in {"completed", "dedup_hit"}:
            _maybe_enqueue_self_evolve(
                ctx=ctx,
                graph_id=body.graph_id,
                profile=profile.value,
                persist_mode=persist_mode.value,
            )

        response_payload = {
            "status": ingest_result.status,
            "raw_id": raw_id,
            "packet_hash": ingest_result.packet_hash,
            "graph_version": ingest_result.graph_version,
            "nodes_written": ingest_result.nodes_written,
            "merges": ingest_result.merges,
            "block_count": ingest_result.block_count,
            "vector_count": ingest_result.vector_count,
            "events_emitted": ingest_result.events_emitted,
            "latency_ms": ingest_result.latency_ms,
            "phase_latency_ms": ingest_result.phase_latency_ms,
            "error": ingest_result.error,
            "requested_profile": ingest_result.requested_profile,
            "requested_persist_mode": ingest_result.requested_persist_mode,
            "effective_profile": ingest_result.effective_profile,
            "effective_persist_mode": ingest_result.effective_persist_mode,
            "durability_path": ingest_result.durability_path,
            "index_write_mode": ingest_result.index_write_mode,
            "secondary_task_status": ingest_result.secondary_task_status,
            "secondary_task_job_id": ingest_result.secondary_task_job_id,
            "idempotency_key": idempotency_key,
            "replayed": False,
        }

        if ctx.event_repo and ctx.session:
            ctx.event_repo.emit(
                ctx.session,
                body.graph_id,
                "MEMORY_WRITE_COMPLETED",
                {
                    "raw_id": raw_id,
                    "packet_hash": ingest_result.packet_hash,
                    "status": ingest_result.status,
                    "idempotency_key": idempotency_key,
                    "request_id": getattr(request.state, "request_id", None),
                    "requested_profile": ingest_result.requested_profile,
                    "requested_persist_mode": ingest_result.requested_persist_mode,
                    "effective_profile": ingest_result.effective_profile,
                    "effective_persist_mode": ingest_result.effective_persist_mode,
                    "durability_path": ingest_result.durability_path,
                    "index_write_mode": ingest_result.index_write_mode,
                    "secondary_task_status": ingest_result.secondary_task_status,
                    "secondary_task_job_id": ingest_result.secondary_task_job_id,
                },
            )

        if idempotency_key and idem_record is not None:
            idem_repo.mark_completed(
                ctx.session,
                record=idem_record,
                response_json=response_payload,
                packet_hash=ingest_result.packet_hash,
                raw_id=_parse_optional_uuid(raw_id),
                node_count=ingest_result.nodes_written,
                vector_count=ingest_result.vector_count,
            )
            ctx.session.commit()

        return MemoryWriteResponse(**response_payload)
    except HTTPException as exc:
        if idempotency_key and idem_record is not None:
            try:
                ctx.session.rollback()
                idem_repo.mark_failed(
                    ctx.session,
                    record=idem_record,
                    error_message=redact_error_text(str(exc.detail)),
                )
                ctx.session.commit()
            except Exception:  # nosec B110
                ctx.session.rollback()
        raise
    except Exception as exc:
        logger.error("memory write failed: %s", exc)
        if idempotency_key and idem_record is not None:
            try:
                ctx.session.rollback()
                idem_repo.mark_failed(
                    ctx.session,
                    record=idem_record,
                    error_message=redact_error_text(str(exc)),
                )
                ctx.session.commit()
            except Exception:  # nosec B110
                ctx.session.rollback()
        raise HTTPException(status_code=500, detail="Memory write failed") from exc


@router.patch(
    "/{node_id}",
    response_model=MemoryItemResponse,
    dependencies=[Depends(require_scopes(["memory.write"]))],
)
async def patch_memory_item(
    node_id: str,
    body: MemoryPatchRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> MemoryItemResponse:
    _configure_mutation_lock_timeout(ctx)

    node = ctx.node_repo.get_by_id(body.graph_id, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Memory item not found")

    # Optimistic update guard.
    expected = normalize_datetime_utc(body.expected_updated_at)
    current = normalize_datetime_utc(node.updated_at)
    if expected is not None and current is not None and expected != current:
        raise HTTPException(
            status_code=409,
            detail=(
                "Memory item was updated by another request. "
                f"current_updated_at={current.isoformat()}"
            ),
        )

    changed = False
    if body.kind is not None:
        kind = str(body.kind).strip().lower()
        if kind not in {"atom", "macro"}:
            raise HTTPException(
                status_code=422, detail="kind must be 'atom' or 'macro'"
            )
        node.kind = kind
        changed = True

    if body.level is not None:
        node.level = int(body.level)
        changed = True

    if body.residual is not None:
        node.residual = int(float(body.residual) * 1e9)
        changed = True

    if body.anchor is not None:
        node.anchor_json = body.anchor
        changed = True

    if body.opp_signature is not None:
        node.opp_signature = body.opp_signature
        changed = True

    if not changed:
        raise HTTPException(
            status_code=400, detail="No mutable fields provided for update"
        )

    try:
        node.updated_at = datetime.now(timezone.utc)
        ctx.session.flush()
        if ctx.event_repo:
            ctx.event_repo.emit(
                ctx.session,
                body.graph_id,
                "MEMORY_ITEM_UPDATED",
                {
                    "node_id": str(node.node_id),
                    "raw_id": node.raw_id,
                    "updated_fields": sorted(
                        [
                            field
                            for field in (
                                "kind",
                                "level",
                                "residual",
                                "anchor",
                                "opp_signature",
                            )
                            if getattr(body, field) is not None
                        ]
                    ),
                },
            )
        ctx.session.commit()
    except OperationalError as exc:
        ctx.session.rollback()
        if _is_lock_conflict(exc):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Memory item update is temporarily locked by another operation. "
                    "Retry the request."
                ),
            ) from exc
        raise

    reloaded = (
        ctx.session.query(NodeModel)
        .filter(
            and_(
                NodeModel.tenant_id == ctx.tenant_id,
                NodeModel.graph_id == body.graph_id,
                NodeModel.node_id == _parse_uuid(node_id, "node_id"),
            )
        )
        .first()
    )
    if reloaded is None:
        raise HTTPException(
            status_code=404, detail="Memory item not found after update"
        )
    return _node_to_item(reloaded)


__all__ = ["router"]
