"""Real storage tools for the Cortex AGI engine with human-in-the-loop approval.

Cortex agents get a curated set of storage tools. Read-only operations
(status, list files, get file, download, orphan scan) execute directly
against the tenant's repositories. Mutating operations (upload, delete,
reingest, retry) are gated behind a human-in-the-loop approval ledger
(``cortex_tool_approvals``): the agent proposes the action, an operator
approves it, and only then is the action executed with a stored receipt.

Every tool is tenant-scoped: all queries are filtered by ``tenant_id`` and
``graph_id``. No tool ever crosses tenant boundaries.
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

APPROVAL_TOOL_NAMES = {
    "faim_storage_upload",
    "faim_storage_delete",
    "faim_storage_reingest",
    "faim_storage_retry",
}


def _parse_uuid(value: Any, field_name: str = "raw_id") -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {field_name}: {value!r}") from exc


def _resolve_session(tenant_id: str) -> Any:
    """Open a fresh session for the tenant (auto-close via context manager)."""
    from runtime.context import close_session, get_repos

    return get_repos(tenant_id)


# =============================================================================
# Approval ledger
# =============================================================================


def propose_approval(
    session,
    *,
    tenant_id: str,
    graph_id: str,
    tool_name: str,
    args: Dict[str, Any],
    reason: str,
    session_id: Optional[str] = None,
    turn_id: Optional[str] = None,
    proposed_by: str = "agent_cortex",
) -> Dict[str, Any]:
    """Record a pending human-approval request for a mutating tool action."""
    from store.pg.models_faim import CortexToolApprovalModel

    now = datetime.now(timezone.utc)
    row = CortexToolApprovalModel(
        tenant_id=tenant_id,
        graph_id=graph_id,
        session_id=session_id,
        turn_id=turn_id,
        tool_name=tool_name,
        status="pending",
        execution_status="pending",
        args_json=args,
        reason=reason or f"{tool_name} requested",
        proposed_by=proposed_by,
        created_at=now,
    )
    session.add(row)
    session.flush()
    session.commit()
    return {
        "status": "pending_approval",
        "approval_id": row.id,
        "tool_name": tool_name,
        "message": (
            f"Action '{tool_name}' requires human approval. "
            f"Approval request #{row.id} is pending."
        ),
    }


def approve_approval(session, *, approval_id: int, tenant_id: str, decision_by: str) -> Dict[str, Any]:
    """Approve a pending approval request (does not execute; use execute_approval)."""
    from store.pg.models_faim import CortexToolApprovalModel

    row = (
        session.query(CortexToolApprovalModel)
        .filter(
            CortexToolApprovalModel.id == int(approval_id),
            CortexToolApprovalModel.tenant_id == tenant_id,
        )
        .first()
    )
    if row is None:
        raise ValueError(f"Approval request #{approval_id} not found")
    if row.status != "pending":
        raise ValueError(f"Approval request #{approval_id} is already {row.status}")

    row.status = "approved"
    row.decision_by = decision_by or "operator"
    row.decided_at = datetime.now(timezone.utc)
    session.commit()
    return {"approval_id": row.id, "status": row.status, "tool_name": row.tool_name}


def reject_approval(
    session,
    *,
    approval_id: int,
    tenant_id: str,
    decision_by: str,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Reject a pending approval request."""
    from store.pg.models_faim import CortexToolApprovalModel

    row = (
        session.query(CortexToolApprovalModel)
        .filter(
            CortexToolApprovalModel.id == int(approval_id),
            CortexToolApprovalModel.tenant_id == tenant_id,
        )
        .first()
    )
    if row is None:
        raise ValueError(f"Approval request #{approval_id} not found")
    if row.status != "pending":
        raise ValueError(f"Approval request #{approval_id} is already {row.status}")

    row.status = "rejected"
    row.execution_status = "skipped"
    row.decision_by = decision_by or "operator"
    row.decision_note = note
    row.decided_at = datetime.now(timezone.utc)
    session.commit()
    return {
        "approval_id": row.id,
        "status": row.status,
        "execution_status": row.execution_status,
        "tool_name": row.tool_name,
    }


def execute_approval(session, *, approval_id: int, tenant_id: str) -> Dict[str, Any]:
    """Execute an approved storage action and store the receipt."""
    from store.pg.models_faim import CortexToolApprovalModel

    row = (
        session.query(CortexToolApprovalModel)
        .filter(
            CortexToolApprovalModel.id == int(approval_id),
            CortexToolApprovalModel.tenant_id == tenant_id,
        )
        .first()
    )
    if row is None:
        raise ValueError(f"Approval request #{approval_id} not found")
    if row.status != "approved":
        raise ValueError(f"Approval request #{approval_id} is not approved")
    if row.execution_status == "executed":
        return {
            "approval_id": row.id,
            "status": row.status,
            "execution_status": "executed",
            "already_executed": True,
            "receipt": row.execution_receipt_json or {},
        }

    args = dict(row.args_json or {})
    args.pop("ctx", None)
    executor = _EXECUTORS.get(row.tool_name)
    if executor is None:
        row.execution_status = "failed"
        row.execution_error = f"Unknown tool '{row.tool_name}'"
        row.executed_at = datetime.now(timezone.utc)
        session.commit()
        raise ValueError(row.execution_error)

    try:
        receipt = executor(
            session,
            tenant_id=tenant_id,
            graph_id=row.graph_id,
            **args,
        )
        row.execution_status = "executed"
        row.execution_receipt_json = receipt
        row.execution_error = None
    except Exception as exc:  # nosec B110 - surfaced in receipt
        row.execution_status = "failed"
        row.execution_error = str(exc)
        row.execution_receipt_json = {}
        session.commit()
        raise ValueError(str(exc)) from exc

    row.executed_at = datetime.now(timezone.utc)
    session.commit()
    return {
        "approval_id": row.id,
        "status": row.status,
        "execution_status": "executed",
        "receipt": receipt,
    }


def list_approvals(
    session,
    *,
    tenant_id: str,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List approval requests for a tenant, newest first."""
    from store.pg.models_faim import CortexToolApprovalModel

    q = session.query(CortexToolApprovalModel).filter(
        CortexToolApprovalModel.tenant_id == tenant_id
    )
    if status:
        q = q.filter(CortexToolApprovalModel.status == status)
    rows = q.order_by(CortexToolApprovalModel.created_at.desc()).limit(max(1, int(limit))).all()
    return [
        {
            "id": r.id,
            "tenant_id": r.tenant_id,
            "graph_id": r.graph_id,
            "session_id": r.session_id,
            "turn_id": r.turn_id,
            "tool_name": r.tool_name,
            "status": r.status,
            "execution_status": r.execution_status,
            "args": r.args_json or {},
            "reason": r.reason,
            "proposed_by": r.proposed_by,
            "decision_by": r.decision_by,
            "decision_note": r.decision_note,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "decided_at": r.decided_at.isoformat() if r.decided_at else None,
            "executed_at": r.executed_at.isoformat() if r.executed_at else None,
            "receipt": r.execution_receipt_json or {},
        }
        for r in rows
    ]


# =============================================================================
# Read-only tools (no approval required)
# =============================================================================


async def faim_storage_status(
    tenant_id: str, graph_id: Optional[str] = None
) -> Dict[str, Any]:
    """Return a live summary of tenant storage: files, sizes, ingest health."""
    repos = _resolve_session(tenant_id)
    session = repos["session"]
    try:
        file_repo = repos["storage_file_repo"]
        summary = file_repo.summary(session, graph_id=graph_id)

        from store.pg.models_faim import EdgeModel, NodeModel, RawRefModel

        nq = session.query(NodeModel).filter(NodeModel.tenant_id == tenant_id)
        eq = session.query(EdgeModel).filter(EdgeModel.tenant_id == tenant_id)
        rq = session.query(RawRefModel).filter(RawRefModel.tenant_id == tenant_id)
        if graph_id:
            nq = nq.filter(NodeModel.graph_id == graph_id)
            eq = eq.filter(EdgeModel.graph_id == graph_id)
        summary["node_count"] = nq.count()
        summary["edge_count"] = eq.count()
        summary["raw_ref_count"] = rq.count()

        # Orphaned-edge health check (reuses the cleanup sweep logic).
        try:
            from store.pg.graph_cleanup import (
                find_orphan_edges,
                find_orphan_coactivations,
            )

            orphan_edges = find_orphan_edges(session, tenant_id, graph_id)
            orphan_coacts = find_orphan_coactivations(session, tenant_id, graph_id)
            summary["orphaned_edges"] = len(orphan_edges)
            summary["orphaned_coactivations"] = len(orphan_coacts)
            summary["healthy"] = (
                len(orphan_edges) == 0 and len(orphan_coacts) == 0
            )
        except Exception as exc:  # nosec B110 - health check is best-effort
            logger.warning("Orphan health check unavailable: %s", exc)
            summary["orphaned_edges"] = None
            summary["orphaned_coactivations"] = None
            summary["healthy"] = None

        return {"status": "success", "storage": summary}
    finally:
        session.close()


async def faim_storage_files(
    tenant_id: str,
    graph_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 25,
    include_delete_requested: bool = True,
) -> Dict[str, Any]:
    """List catalogued storage files with ingest status and metadata."""
    repos = _resolve_session(tenant_id)
    session = repos["session"]
    try:
        file_repo = repos["storage_file_repo"]
        rows, total = file_repo.list_files(
            session,
            graph_id=graph_id,
            status=status,
            query=None,
            limit=max(1, int(limit)),
            offset=0,
            include_delete_requested=include_delete_requested,
        )
        items = []
        for r in rows:
            items.append(
                {
                    "id": str(r.id),
                    "raw_id": str(r.raw_id),
                    "filename": r.filename,
                    "mime_type": r.mime_type,
                    "size_bytes": r.size_bytes,
                    "ingest_status": r.ingest_status,
                    "node_count": r.node_count,
                    "vector_count": r.vector_count,
                    "error_message": r.error_message,
                    "delete_requested": bool(r.delete_requested),
                    "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else None,
                    "ingested_at": r.ingested_at.isoformat() if r.ingested_at else None,
                }
            )
        return {"status": "success", "total": int(total), "items": items}
    finally:
        session.close()


async def faim_storage_get_file(
    tenant_id: str, graph_id: Optional[str], raw_id: str
) -> Dict[str, Any]:
    """Return a single storage file's metadata by raw_id."""
    repos = _resolve_session(tenant_id)
    session = repos["session"]
    try:
        file_repo = repos["storage_file_repo"]
        row = file_repo.get_by_raw_id(session, _parse_uuid(raw_id), graph_id)
        if row is None:
            return {"status": "error", "error": "File not found"}
        return {
            "status": "success",
            "file": {
                "id": str(row.id),
                "raw_id": str(row.raw_id),
                "filename": row.filename,
                "mime_type": row.mime_type,
                "size_bytes": row.size_bytes,
                "ingest_status": row.ingest_status,
                "node_count": row.node_count,
                "vector_count": row.vector_count,
                "error_message": row.error_message,
                "delete_requested": bool(row.delete_requested),
            },
        }
    finally:
        session.close()


async def faim_storage_download(
    tenant_id: str, graph_id: Optional[str], raw_id: str
) -> Dict[str, Any]:
    """Return file metadata and content (base64) for download."""
    repos = _resolve_session(tenant_id)
    session = repos["session"]
    try:
        raw_uuid = _parse_uuid(raw_id)
        file_repo = repos["storage_file_repo"]
        row = file_repo.get_by_raw_id(session, raw_uuid, graph_id)
        if row is None:
            return {"status": "error", "error": "File not found"}
        raw_ref = repos["raw_repo"].get_by_id(session, raw_uuid)
        if raw_ref is None:
            return {"status": "error", "error": "Raw blob not found"}
        store = repos["raw_store"]
        try:
            content = store.load(raw_ref, verify=True)
        except Exception as exc:  # nosec B110 - surfaced to agent
            return {
                "status": "error",
                "error": f"Raw blob unavailable: {exc}",
                "file": {
                    "filename": row.filename,
                    "mime_type": row.mime_type,
                    "ingest_status": row.ingest_status,
                },
            }
        return {
            "status": "success",
            "file": {
                "raw_id": str(row.raw_id),
                "filename": row.filename,
                "mime_type": row.mime_type,
                "size_bytes": len(content),
                "content_base64": base64.b64encode(content).decode("ascii"),
            },
        }
    finally:
        session.close()


async def faim_storage_orphan_scan(
    tenant_id: str, graph_id: Optional[str] = None
) -> Dict[str, Any]:
    """Scan for orphaned edges and coactivations that should be swept."""
    repos = _resolve_session(tenant_id)
    session = repos["session"]
    try:
        from store.pg.graph_cleanup import (
            find_orphan_coactivations,
            find_orphan_edges,
        )

        orphan_edges = find_orphan_edges(session, tenant_id, graph_id)
        orphan_coacts = find_orphan_coactivations(session, tenant_id, graph_id)
        return {
            "status": "success",
            "orphaned_edges": len(orphan_edges),
            "orphaned_coactivations": len(orphan_coacts),
            "healthy": len(orphan_edges) == 0 and len(orphan_coacts) == 0,
            "suggestion": (
                "Run sweep-orphans to clean up orphaned artifacts."
                if orphan_edges or orphan_coacts
                else "No orphaned artifacts found."
            ),
        }
    finally:
        session.close()


# =============================================================================
# Mutating tools (require human-in-the-loop approval)
# =============================================================================


def _delete_file(session, *, tenant_id: str, graph_id: str, raw_id: str, reason: str = "") -> Dict[str, Any]:
    """Execute a hard delete (mirrors the storage router's hard delete path)."""
    from store.pg.graph_cleanup import purge_graph_artifacts_for_raw_ids
    from store.pg.models_faim import StorageFileModel

    raw_uuid = _parse_uuid(raw_id)
    file_repo = None
    from store.pg.repos.storage_file_repo import StorageFileRepo

    file_repo = StorageFileRepo(session, tenant_id=tenant_id)
    row = file_repo.get_by_raw_id(session, raw_uuid, graph_id)
    if row is None:
        raise ValueError("Storage file not found")

    # 1. Delete physical raw blob + raw ref.
    raw_ref = None
    from store.pg.repos.raw_repo import RawRepo

    raw_repo = RawRepo(tenant_id=tenant_id)
    raw_ref = raw_repo.get_by_id(session, raw_uuid)
    if raw_ref is not None:
        from runtime.context import _get_raw_store

        store = _get_raw_store(tenant_id)
        try:
            if callable(getattr(store, "delete", None)):
                store.delete(raw_ref)
        except Exception as exc:  # nosec B110
            logger.warning("Failed to delete raw blob %s: %s", raw_uuid, exc)
        try:
            raw_repo.delete_by_id(session, raw_uuid)
        except Exception as exc:  # nosec B110
            logger.warning("Failed to delete raw ref %s: %s", raw_uuid, exc)

    # 2. Purge graph artifacts atomically (edges, coactivations, reprs, nodes).
    purge_summary = purge_graph_artifacts_for_raw_ids(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        raw_ids=[raw_uuid],
    )

    # 3. Remove storage catalog rows for this raw_id in the graph.
    session.query(StorageFileModel).filter(
        StorageFileModel.tenant_id == tenant_id,
        StorageFileModel.graph_id == graph_id,
        StorageFileModel.raw_id == raw_uuid,
    ).delete(synchronize_session=False)
    session.commit()
    return {
        "op": "delete",
        "raw_id": str(raw_uuid),
        "purge": purge_summary,
        "message": "File and all graph artifacts deleted.",
    }


def _reingest_file(
    session,
    *,
    tenant_id: str,
    graph_id: str,
    raw_id: str,
    profile: str = "strict",
    persist_mode: str = "relaxed",
    extractor_mode: str = "auto",
) -> Dict[str, Any]:
    """Re-run the ingest pipeline for an existing raw file."""
    from orchestration.ingest_flow import FAIMProfile, PersistMode, run_ingest
    from store.pg.repos.raw_repo import RawRepo
    from store.pg.repos.storage_file_repo import StorageFileRepo

    raw_uuid = _parse_uuid(raw_id)
    file_repo = StorageFileRepo(session, tenant_id=tenant_id)
    row = file_repo.get_by_raw_id(session, raw_uuid, graph_id)
    if row is None:
        raise ValueError("Storage file not found")
    raw_repo = RawRepo(tenant_id=tenant_id)
    raw_ref = raw_repo.get_by_id(session, raw_uuid)
    if raw_ref is None:
        raise ValueError("Raw reference not found")

    from runtime.context import _get_raw_store

    store = _get_raw_store(tenant_id)
    try:
        file_bytes = store.load(raw_ref, verify=True)
    except Exception as exc:
        raise ValueError(f"Raw blob not available: {exc}") from exc

    profile_enum = FAIMProfile(str(profile or "strict").lower())
    persist_mode_enum = PersistMode(str(persist_mode or "relaxed").lower())

    file_repo.mark_ingesting(session, raw_id=raw_uuid, graph_id=row.graph_id, job_id=None)
    session.commit()

    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.graph_version_repo import GraphVersionRepo
    from store.pg.repos.node_repo import NodeRepo

    result = run_ingest(
        graph_id=row.graph_id,
        raw_id=str(raw_uuid),
        filename=row.filename,
        file_bytes=file_bytes,
        profile=profile_enum,
        persist_mode=persist_mode_enum,
        extraction_settings={"extractor_mode": extractor_mode or "auto"},
        tenant_id=tenant_id,
        session=session,
        node_repo=NodeRepo(session, tenant_id=tenant_id),
        edge_repo=EdgeRepo(session, tenant_id=tenant_id),
        event_repo=EventRepo(tenant_id=tenant_id),
        gv_repo=GraphVersionRepo(tenant_id=tenant_id),
    )
    row = file_repo.mark_ingest_result(
        session,
        raw_id=raw_uuid,
        graph_id=row.graph_id,
        status=result.status,
        packet_hash=result.packet_hash or None,
        node_count=result.nodes_written,
        vector_count=result.vector_count,
        error_message=result.error,
        job_id=None,
    )
    session.commit()
    return {
        "op": "reingest",
        "raw_id": str(raw_uuid),
        "filename": row.filename if row else None,
        "status": result.status,
        "nodes_written": result.nodes_written,
        "vector_count": result.vector_count,
        "packet_hash": result.packet_hash,
        "error": result.error,
    }


def _upload_file(
    session,
    *,
    tenant_id: str,
    graph_id: str,
    filename: str,
    content_base64: str,
    mime_type: str = "application/octet-stream",
    profile: str = "strict",
    persist_mode: str = "relaxed",
) -> Dict[str, Any]:
    """Persist a raw upload and run the ingest pipeline."""
    from orchestration.ingest_flow import FAIMProfile, PersistMode, run_ingest
    from store.pg.repos.storage_file_repo import StorageFileRepo

    if not filename or not filename.strip():
        raise ValueError("filename is required")
    try:
        file_bytes = base64.b64decode(content_base64, validate=True)
    except Exception as exc:
        raise ValueError("content_base64 must be valid base64") from exc
    if not file_bytes:
        raise ValueError("content is empty")

    from store.raw.raw_store import RawStore
    from runtime.context import _get_raw_store

    store = _get_raw_store(tenant_id)
    raw_ref = store.store(file_bytes, mime_type=mime_type, graph_id=graph_id)

    from store.pg.repos.raw_repo import RawRepo

    raw_repo = RawRepo(tenant_id=tenant_id)
    saved_ref = raw_repo.create(session, raw_ref)

    raw_uuid = _parse_uuid(str(saved_ref.id), "raw_id")
    file_repo = StorageFileRepo(session, tenant_id=tenant_id)
    file_repo.upsert_upload(
        session,
        graph_id=graph_id,
        raw_id=raw_uuid,
        filename=filename.strip(),
        mime_type=mime_type or "application/octet-stream",
        size_bytes=len(file_bytes),
        sha256=str(raw_ref.sha256),
        job_id=None,
    )
    session.commit()

    profile_enum = FAIMProfile(str(profile or "strict").lower())
    persist_mode_enum = PersistMode(str(persist_mode or "relaxed").lower())

    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.graph_version_repo import GraphVersionRepo
    from store.pg.repos.node_repo import NodeRepo

    result = run_ingest(
        graph_id=graph_id,
        raw_id=str(raw_uuid),
        filename=filename.strip(),
        file_bytes=file_bytes,
        profile=profile_enum,
        persist_mode=persist_mode_enum,
        extraction_settings={"extractor_mode": "auto"},
        tenant_id=tenant_id,
        session=session,
        node_repo=NodeRepo(session, tenant_id=tenant_id),
        edge_repo=EdgeRepo(session, tenant_id=tenant_id),
        event_repo=EventRepo(tenant_id=tenant_id),
        gv_repo=GraphVersionRepo(tenant_id=tenant_id),
    )
    row = file_repo.mark_ingest_result(
        session,
        raw_id=raw_uuid,
        graph_id=graph_id,
        status=result.status,
        packet_hash=result.packet_hash or None,
        node_count=result.nodes_written,
        vector_count=result.vector_count,
        error_message=result.error,
        job_id=None,
    )
    session.commit()
    return {
        "op": "upload",
        "raw_id": str(raw_uuid),
        "filename": filename.strip(),
        "status": result.status,
        "nodes_written": result.nodes_written,
        "vector_count": result.vector_count,
        "packet_hash": result.packet_hash,
        "error": result.error,
    }


def _retry_file(
    session,
    *,
    tenant_id: str,
    graph_id: str,
    raw_id: str,
    profile: str = "strict",
    persist_mode: str = "relaxed",
) -> Dict[str, Any]:
    """Clear delete_requested flag and re-ingest a previously failed file."""
    from store.pg.repos.storage_file_repo import StorageFileRepo

    raw_uuid = _parse_uuid(raw_id)
    file_repo = StorageFileRepo(session, tenant_id=tenant_id)
    row = file_repo.get_by_raw_id(session, raw_uuid, graph_id)
    if row is None:
        raise ValueError("Storage file not found")
    row.delete_requested = False
    row.delete_requested_at = None
    session.commit()
    return _reingest_file(
        session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        raw_id=raw_id,
        profile=profile,
        persist_mode=persist_mode,
    )


async def faim_storage_upload(
    tenant_id: str,
    graph_id: str,
    filename: str,
    content_base64: str,
    mime_type: str = "application/octet-stream",
    profile: str = "strict",
    persist_mode: str = "relaxed",
    reason: str = "",
    session_id: Optional[str] = None,
    turn_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Propose a file upload; requires human approval before ingestion."""
    repos = _resolve_session(tenant_id)
    session = repos["session"]
    try:
        return propose_approval(
            session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            tool_name="faim_storage_upload",
            args={
                "filename": filename,
                "content_base64": content_base64,
                "mime_type": mime_type,
                "profile": profile,
                "persist_mode": persist_mode,
            },
            reason=reason or f"Upload {filename}",
            session_id=session_id,
            turn_id=turn_id,
        )
    finally:
        session.close()


async def faim_storage_delete(
    tenant_id: str,
    graph_id: str,
    raw_id: str,
    reason: str = "",
    session_id: Optional[str] = None,
    turn_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Propose a hard delete; requires human approval before execution."""
    repos = _resolve_session(tenant_id)
    session = repos["session"]
    try:
        return propose_approval(
            session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            tool_name="faim_storage_delete",
            args={"raw_id": raw_id, "reason": reason},
            reason=reason or f"Delete {raw_id}",
            session_id=session_id,
            turn_id=turn_id,
        )
    finally:
        session.close()


async def faim_storage_reingest(
    tenant_id: str,
    graph_id: str,
    raw_id: str,
    profile: str = "strict",
    persist_mode: str = "relaxed",
    reason: str = "",
    session_id: Optional[str] = None,
    turn_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Propose a re-ingest; requires human approval before execution."""
    repos = _resolve_session(tenant_id)
    session = repos["session"]
    try:
        return propose_approval(
            session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            tool_name="faim_storage_reingest",
            args={
                "raw_id": raw_id,
                "profile": profile,
                "persist_mode": persist_mode,
            },
            reason=reason or f"Re-ingest {raw_id}",
            session_id=session_id,
            turn_id=turn_id,
        )
    finally:
        session.close()


async def faim_storage_retry(
    tenant_id: str,
    graph_id: str,
    raw_id: str,
    reason: str = "",
    session_id: Optional[str] = None,
    turn_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Propose a retry of a failed file; requires human approval."""
    repos = _resolve_session(tenant_id)
    session = repos["session"]
    try:
        return propose_approval(
            session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            tool_name="faim_storage_retry",
            args={"raw_id": raw_id},
            reason=reason or f"Retry {raw_id}",
            session_id=session_id,
            turn_id=turn_id,
        )
    finally:
        session.close()


_EXECUTORS = {
    "faim_storage_upload": _upload_file,
    "faim_storage_delete": _delete_file,
    "faim_storage_reingest": _reingest_file,
    "faim_storage_retry": _retry_file,
}


def get_cortex_storage_tools() -> List[Any]:
    """Return the executable storage tool callables for the agent."""
    return [
        faim_storage_status,
        faim_storage_files,
        faim_storage_get_file,
        faim_storage_download,
        faim_storage_orphan_scan,
        faim_storage_upload,
        faim_storage_delete,
        faim_storage_reingest,
        faim_storage_retry,
    ]
