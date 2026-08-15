"""Storage retention cleanup worker utilities (Phase B).

Provides dry-run and irreversible physical cleanup for delete-requested files.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import urlparse
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetentionItemResult:
    raw_id: str
    graph_id: str
    filename: str
    status: str
    detail: Optional[str] = None
    blob_deleted: bool = False
    raw_ref_deleted: bool = False


@dataclass(frozen=True)
class RetentionRunResult:
    dry_run: bool
    irreversible: bool
    scanned: int
    deleted: int
    skipped: int
    failed: int
    results: List[RetentionItemResult]


def _delete_from_uri(uri: str) -> bool:
    """Best-effort file:// URI delete fallback."""
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return False
    path = Path(parsed.path)
    if not path.exists():
        return False
    path.unlink()
    return True


def run_storage_retention_cleanup(
    *,
    session: Any,
    tenant_id: str,
    storage_file_repo: Any,
    raw_repo: Any,
    raw_store: Any,
    event_repo: Optional[Any],
    graph_id: Optional[str] = None,
    limit: int = 100,
    dry_run: bool = True,
    irreversible: bool = False,
    reason: Optional[str] = None,
) -> RetentionRunResult:
    """Execute retention cleanup for delete-requested storage files."""
    run_started = datetime.now(timezone.utc)
    logger.info(
        "storage_retention started",
        extra={
            "tenant_id": tenant_id,
            "graph_id": graph_id,
            "op": "retention_cleanup",
            "status": "started",
        },
    )
    if not dry_run and not irreversible:
        raise ValueError("Physical delete requires irreversible=true")

    rows = storage_file_repo.list_delete_requested(
        session,
        graph_id=graph_id,
        limit=limit,
    )
    results: List[RetentionItemResult] = []
    deleted = 0
    skipped = 0
    failed = 0

    for row in rows:
        raw_id_text = str(row.raw_id)
        graph_text = str(row.graph_id)
        filename = str(row.filename)

        try:
            raw_uuid = UUID(raw_id_text)
            active_refs = storage_file_repo.count_active_references(
                session,
                raw_id=raw_uuid,
                exclude_graph_id=graph_text,
            )
            if active_refs > 0:
                skipped += 1
                results.append(
                    RetentionItemResult(
                        raw_id=raw_id_text,
                        graph_id=graph_text,
                        filename=filename,
                        status="skipped",
                        detail=f"raw_id still referenced by {active_refs} active storage rows",
                    )
                )
                continue

            if dry_run:
                skipped += 1
                results.append(
                    RetentionItemResult(
                        raw_id=raw_id_text,
                        graph_id=graph_text,
                        filename=filename,
                        status="would_delete",
                        detail="Dry-run mode",
                    )
                )
                continue

            raw_ref = raw_repo.get_by_id(session, raw_uuid)
            blob_deleted = False
            raw_ref_deleted = False

            if raw_ref is not None:
                delete_fn = getattr(raw_store, "delete", None)
                if callable(delete_fn):
                    blob_deleted = bool(delete_fn(raw_ref))
                else:
                    blob_deleted = _delete_from_uri(str(raw_ref.uri))
                raw_ref_deleted = bool(raw_repo.delete_by_id(session, raw_uuid))

            storage_file_repo.mark_delete_executed(
                session,
                raw_id=raw_uuid,
                graph_id=graph_text,
                note=reason,
            )

            # Purge graph artifacts (edges, coactivations, reprs, nodes) so
            # irreversible retention cleanup never leaves orphaned edges.
            try:
                from store.pg.graph_cleanup import purge_graph_artifacts_for_raw_ids

                purge_graph_artifacts_for_raw_ids(
                    session=session,
                    tenant_id=tenant_id,
                    graph_id=graph_text,
                    raw_ids=[raw_uuid],
                )
            except Exception as exc:  # nosec B110
                logger.warning("Graph artifact purge failed for %s: %s", raw_id_text, exc)

            if event_repo is not None:
                try:
                    event_repo.emit(
                        session,
                        graph_text,
                        "STORAGE_DELETE_EXECUTED",
                        {
                            "raw_id": raw_id_text,
                            "filename": filename,
                            "reason": reason,
                            "blob_deleted": blob_deleted,
                            "raw_ref_deleted": raw_ref_deleted,
                            "tenant_id": tenant_id,
                        },
                    )
                except Exception as exc:  # nosec B110
                    logger.warning("Failed to emit STORAGE_DELETE_EXECUTED: %s", exc)

            session.commit()
            deleted += 1
            logger.info(
                "storage_retention item deleted",
                extra={
                    "tenant_id": tenant_id,
                    "graph_id": graph_text,
                    "raw_id": raw_id_text,
                    "op": "retention_cleanup",
                    "status": "deleted",
                },
            )
            results.append(
                RetentionItemResult(
                    raw_id=raw_id_text,
                    graph_id=graph_text,
                    filename=filename,
                    status="deleted",
                    detail="Physical delete executed",
                    blob_deleted=blob_deleted,
                    raw_ref_deleted=raw_ref_deleted,
                )
            )
        except Exception as exc:
            session.rollback()
            failed += 1
            logger.warning(
                "storage_retention item failed",
                extra={
                    "tenant_id": tenant_id,
                    "graph_id": graph_text,
                    "raw_id": raw_id_text,
                    "op": "retention_cleanup",
                    "status": "failed",
                    "failure_reason": str(exc)[:120],
                },
            )
            results.append(
                RetentionItemResult(
                    raw_id=raw_id_text,
                    graph_id=graph_text,
                    filename=filename,
                    status="failed",
                    detail=str(exc),
                )
            )

    elapsed_ms = int((datetime.now(timezone.utc) - run_started).total_seconds() * 1000)
    logger.info(
        "storage_retention completed",
        extra={
            "tenant_id": tenant_id,
            "graph_id": graph_id,
            "op": "retention_cleanup",
            "status": "completed" if failed == 0 else "partial_failed",
            "latency_ms": elapsed_ms,
        },
    )

    return RetentionRunResult(
        dry_run=dry_run,
        irreversible=irreversible,
        scanned=len(rows),
        deleted=deleted,
        skipped=skipped,
        failed=failed,
        results=results,
    )


__all__ = [
    "RetentionItemResult",
    "RetentionRunResult",
    "run_storage_retention_cleanup",
]
