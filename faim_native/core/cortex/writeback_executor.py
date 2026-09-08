"""Deterministic Cortex writeback execution helpers.

Approved Cortex writeback candidates are turned into durable memory writes
through the existing memory ingest pipeline. The execution is idempotent and
records a receipt so the runtime can distinguish proposal, approval, replay,
execution, and failure states.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, Mapping

from fastapi.encoders import jsonable_encoder

from api.services.memory_service import build_write_request_hash, redact_error_text
from orchestration.ingest_flow import FAIMProfile, PersistMode
from runtime.context import _get_raw_store
from store.pg.repos.memory_write_idempotency_repo import MemoryWriteIdempotencyRepo


@dataclass(frozen=True)
class CortexWritebackExecutionResult:
    """Best-effort receipt for one Cortex writeback candidate."""

    execution_key: str
    execution_request_hash: str
    execution_status: str
    status: str
    response_json: Dict[str, Any]
    raw_id: str | None = None
    packet_hash: str | None = None
    node_count: int = 0
    vector_count: int = 0
    error: str | None = None
    replayed: bool = False


def _stable_writeback_key(
    *,
    tenant_id: str,
    graph_id: str,
    turn_id: str,
    kind: str,
    reason: str,
    text: str,
) -> str:
    raw = "||".join(
        [
            str(tenant_id or "").strip(),
            str(graph_id or "").strip(),
            str(turn_id or "").strip(),
            str(kind or "").strip(),
            str(reason or "").strip(),
            str(text or "").strip(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _candidate_filename(kind: str, turn_id: str) -> str:
    slug = str(kind or "summary").strip().lower().replace(" ", "_")
    return f"cortex_writeback_{slug}_{str(turn_id or 'turn').strip()[:24]}.md"


def _candidate_text(candidate: Mapping[str, Any], turn_id: str) -> str:
    body = str(
        candidate.get("text")
        or candidate.get("reason")
        or candidate.get("summary")
        or "Cortex writeback"
    ).strip()
    kind = str(candidate.get("kind") or "summary").strip().lower()
    if kind == "contradiction_resolution":
        prefix = "Cortex contradiction resolution"
    else:
        prefix = "Cortex memory writeback"
    return f"{prefix} (turn {turn_id})\n\n{body}".strip()


def _make_context(
    *,
    session,
    tenant_id: str,
    request_id: str,
):
    from runtime.context import get_repos

    repos = get_repos(tenant_id, session=session)
    return SimpleNamespace(
        session=session,
        tenant_id=tenant_id,
        request_id=request_id,
        node_repo=repos["node_repo"],
        edge_repo=repos["edge_repo"],
        event_repo=repos["event_repo"],
        gv_repo=repos["gv_repo"],
        raw_repo=repos["raw_repo"],
        storage_file_repo=repos["storage_file_repo"],
        raw_store=_get_raw_store(tenant_id),
    )


def execute_cortex_writeback_candidate(
    *,
    session,
    tenant_id: str,
    graph_id: str,
    turn_id: str,
    candidate_row,
    candidate_payload: Mapping[str, Any],
    request_id: str | None = None,
) -> CortexWritebackExecutionResult:
    """Execute one auto-approved Cortex writeback candidate.

    The execution uses the existing memory ingest pipeline so the writeback
    produces a real durable graph mutation, not just an audit label.
    """

    from api.routers.memory import _run_memory_write

    candidate_kind = str(candidate_payload.get("kind") or "summary").strip()
    candidate_reason = str(candidate_payload.get("reason") or "").strip()
    candidate_text = _candidate_text(candidate_payload, turn_id)
    filename = _candidate_filename(candidate_kind, turn_id)
    payload_bytes = candidate_text.encode("utf-8")
    execution_key = _stable_writeback_key(
        tenant_id=tenant_id,
        graph_id=graph_id,
        turn_id=turn_id,
        kind=candidate_kind,
        reason=candidate_reason,
        text=candidate_text,
    )
    execution_request_hash = build_write_request_hash(
        graph_id=graph_id,
        filename=filename,
        content_type="text/markdown",
        payload_bytes=payload_bytes,
        profile=FAIMProfile.STRICT.value,
        persist_mode=PersistMode.STRICT.value,
    )

    candidate_row.execution_key = execution_key
    candidate_row.execution_request_hash = execution_request_hash
    candidate_row.execution_status = "running"
    candidate_row.executed_at = datetime.now(timezone.utc)
    session.flush()

    idem_repo = MemoryWriteIdempotencyRepo(session, tenant_id=tenant_id)
    begin_result = idem_repo.begin(
        session,
        graph_id=graph_id,
        idempotency_key=execution_key,
        request_hash=execution_request_hash,
    )

    if begin_result.state == "replay":
        stored = begin_result.record.response_json or {}
        if not isinstance(stored, dict):
            stored = {}
        candidate_row.execution_status = "replayed"
        candidate_row.execution_receipt_json = jsonable_encoder(stored)
        candidate_row.execution_error = None
        candidate_row.executed_at = datetime.now(timezone.utc)
        session.flush()
        return CortexWritebackExecutionResult(
            execution_key=execution_key,
            execution_request_hash=execution_request_hash,
            execution_status="replayed",
            status=str(candidate_row.status or "auto_approved"),
            response_json=dict(stored),
            raw_id=str(stored.get("raw_id")) if stored.get("raw_id") else None,
            packet_hash=str(stored.get("packet_hash")) if stored.get("packet_hash") else None,
            node_count=int(stored.get("nodes_written") or 0),
            vector_count=int(stored.get("vector_count") or 0),
            replayed=True,
        )

    if begin_result.state in {"failed", "conflict_payload"}:
        reason = (
            "writeback idempotency conflict"
            if begin_result.state == "conflict_payload"
            else "previous writeback execution failed"
        )
        candidate_row.execution_status = "failed"
        candidate_row.execution_error = reason
        candidate_row.executed_at = datetime.now(timezone.utc)
        session.flush()
        return CortexWritebackExecutionResult(
            execution_key=execution_key,
            execution_request_hash=execution_request_hash,
            execution_status="failed",
            status=str(candidate_row.status or "auto_approved"),
            response_json={},
            error=reason,
        )

    ctx = _make_context(
        session=session,
        tenant_id=tenant_id,
        request_id=request_id or turn_id,
    )

    try:
        raw_id, ingest_result = _run_memory_write(
            ctx=ctx,
            graph_id=graph_id,
            filename=filename,
            content_type="text/markdown",
            payload_bytes=payload_bytes,
            profile=FAIMProfile.STRICT,
            persist_mode=PersistMode.STRICT,
        )
        response_json = {
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
        }
        idem_repo.mark_completed(
            session,
            record=begin_result.record,
            response_json=response_json,
            packet_hash=ingest_result.packet_hash,
            raw_id=None,
            node_count=ingest_result.nodes_written,
            vector_count=ingest_result.vector_count,
        )
        candidate_row.execution_status = "executed"
        candidate_row.execution_receipt_json = jsonable_encoder(response_json)
        candidate_row.execution_error = None
        candidate_row.executed_at = datetime.now(timezone.utc)
        session.flush()
        return CortexWritebackExecutionResult(
            execution_key=execution_key,
            execution_request_hash=execution_request_hash,
            execution_status="executed",
            status=str(candidate_row.status or "auto_approved"),
            response_json=response_json,
            raw_id=raw_id,
            packet_hash=ingest_result.packet_hash,
            node_count=ingest_result.nodes_written,
            vector_count=ingest_result.vector_count,
        )
    except Exception as exc:  # nosec B110
        error_text = redact_error_text(str(exc))
        candidate_row.execution_status = "failed"
        candidate_row.execution_error = error_text
        candidate_row.executed_at = datetime.now(timezone.utc)
        try:
            session.flush()
        except Exception:  # nosec B110
            pass
        try:
            idem_repo.mark_failed(session, record=begin_result.record, error_message=error_text)
        except Exception:  # nosec B110
            pass
        return CortexWritebackExecutionResult(
            execution_key=execution_key,
            execution_request_hash=execution_request_hash,
            execution_status="failed",
            status=str(candidate_row.status or "auto_approved"),
            response_json={},
            error=error_text,
        )


__all__ = ["CortexWritebackExecutionResult", "execute_cortex_writeback_candidate"]
