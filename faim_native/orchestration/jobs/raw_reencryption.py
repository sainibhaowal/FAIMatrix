"""Legacy raw-blob re-encryption job utilities.

This migration is intentionally conservative:
- it only targets raw refs older than an explicit cutoff timestamp
- it skips rows that already decrypt with the current encrypted raw store
- it leaves old shared plaintext blobs on disk until no raw ref still points to
  the legacy SHA across any tenant
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import urlparse

from store.pg.models_faim import RawRefModel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RawReencryptionItemResult:
    """Per-item result for a legacy raw-blob re-encryption run."""

    raw_id: str
    graph_id: str
    filename: str
    old_sha256: str
    status: str
    detail: Optional[str] = None
    new_sha256: Optional[str] = None
    raw_ref_updated: bool = False
    storage_rows_updated: int = 0
    legacy_blob_deleted: bool = False


@dataclass(frozen=True)
class RawReencryptionRunResult:
    """Summary for a legacy raw-blob re-encryption run."""

    graph_id: Optional[str]
    cutoff_created_at: datetime
    dry_run: bool
    irreversible: bool
    scanned: int
    already_encrypted: int
    reencrypted: int
    failed: int
    results: List[RawReencryptionItemResult] = field(default_factory=list)


def _resolve_base_store(raw_store: Any) -> Any:
    base_store = getattr(raw_store, "_inner", None)
    return base_store if base_store is not None else raw_store


def _is_encrypted_store(raw_store: Any) -> bool:
    return getattr(raw_store, "_inner", None) is not None


def _fallback_filename(raw_ref: Any) -> str:
    uri = str(getattr(raw_ref, "uri", "") or "")
    parsed = urlparse(uri)
    if parsed.path:
        return Path(parsed.path).name or str(getattr(raw_ref, "id", "raw_ref"))
    return str(getattr(raw_ref, "id", "raw_ref"))


def run_raw_reencryption_backfill(
    *,
    session: Any,
    tenant_id: str,
    graph_id: Optional[str],
    cutoff_created_at: datetime,
    raw_repo: Any,
    storage_file_repo: Any,
    raw_store: Any,
    event_repo: Optional[Any] = None,
    page_size: int = 100,
    dry_run: bool = True,
    irreversible: bool = False,
    reason: Optional[str] = None,
) -> RawReencryptionRunResult:
    """Re-encrypt legacy plaintext raw blobs in a tenant-scoped, cutoff-based run."""
    page_size = max(1, int(page_size))
    if cutoff_created_at.tzinfo is None:
        cutoff_created_at = cutoff_created_at.replace(tzinfo=timezone.utc)
    else:
        cutoff_created_at = cutoff_created_at.astimezone(timezone.utc)

    if not dry_run and not irreversible:
        raise ValueError("Physical re-encryption requires irreversible=true")

    if not _is_encrypted_store(raw_store):
        raise ValueError(
            "Legacy raw re-encryption requires an encrypted raw store wrapper"
        )

    base_store = _resolve_base_store(raw_store)
    scanned = 0
    already_encrypted = 0
    reencrypted = 0
    failed = 0
    results: List[RawReencryptionItemResult] = []

    offset = 0
    while True:
        rows = raw_repo.list_before(
            session,
            created_before=cutoff_created_at,
            graph_id=graph_id,
            limit=page_size,
            offset=offset,
        )
        if not rows:
            break

        for raw_ref in rows:
            scanned += 1
            raw_id_text = str(raw_ref.id)
            graph_text = str(raw_ref.graph_id or graph_id or "default")
            filename = _fallback_filename(raw_ref)
            old_sha = str(raw_ref.sha256)
            new_sha: Optional[str] = None
            new_blob_written = False

            try:
                storage_rows = storage_file_repo.list_by_raw_id(
                    session,
                    raw_id=raw_ref.id,
                )

                try:
                    raw_store.load(raw_ref, verify=True)
                    already_encrypted += 1
                    results.append(
                        RawReencryptionItemResult(
                            raw_id=raw_id_text,
                            graph_id=graph_text,
                            filename=filename,
                            old_sha256=old_sha,
                            status="already_encrypted",
                            detail="Blob already decrypts with the current encrypted store.",
                        )
                    )
                    continue
                except Exception:
                    pass

                plaintext = base_store.load_by_sha(old_sha, verify=True)

                if dry_run:
                    results.append(
                        RawReencryptionItemResult(
                            raw_id=raw_id_text,
                            graph_id=graph_text,
                            filename=filename,
                            old_sha256=old_sha,
                            status="would_reencrypt",
                            detail=(
                                "Legacy plaintext blob would be re-encrypted at the "
                                "provided cutoff."
                            ),
                        )
                    )
                    continue

                new_raw_ref = raw_store.store(
                    plaintext,
                    mime_type=str(
                        getattr(raw_ref, "mime_type", "")
                        or "application/octet-stream"
                    ),
                    graph_id=graph_text or None,
                )
                new_blob_written = True
                new_sha = str(new_raw_ref.sha256)
                new_uri = str(new_raw_ref.uri)
                new_size = int(new_raw_ref.size_bytes)

                updated_raw_ref = raw_repo.update_reference(
                    session,
                    raw_id=raw_ref.id,
                    sha256=new_sha,
                    uri=new_uri,
                    size_bytes=new_size,
                    mime_type=str(
                        getattr(raw_ref, "mime_type", "")
                        or "application/octet-stream"
                    ),
                )
                if updated_raw_ref is None:
                    raise RuntimeError(f"Raw reference missing for {raw_id_text}")

                storage_rows_updated = 0
                for row in storage_rows:
                    row.sha256 = new_sha
                    row.updated_at = datetime.now(timezone.utc)
                    storage_rows_updated += 1

                session.flush()

                remaining_old_refs = (
                    session.query(RawRefModel)
                    .filter(RawRefModel.sha256 == old_sha)
                    .count()
                )

                legacy_blob_deleted = False
                legacy_blob_delete_attempted = False
                delete_fn = getattr(base_store, "delete_by_sha", None)
                session.commit()

                if remaining_old_refs == 0 and callable(delete_fn):
                    try:
                        legacy_blob_delete_attempted = True
                        legacy_blob_deleted = bool(delete_fn(old_sha))
                    except Exception as exc:  # nosec B110
                        logger.warning(
                            "Failed to delete legacy plaintext blob sha=%s: %s",
                            old_sha,
                            exc,
                        )

                reencrypted += 1
                if legacy_blob_deleted:
                    detail = (
                        "Legacy plaintext blob migrated to encrypted storage. "
                        "Old blob deleted."
                    )
                elif remaining_old_refs > 0:
                    detail = (
                        "Legacy plaintext blob migrated to encrypted storage. "
                        "Old blob retained because other raw refs still use it."
                    )
                elif legacy_blob_delete_attempted:
                    detail = (
                        "Legacy plaintext blob migrated to encrypted storage. "
                        "Old blob deletion attempt failed."
                    )
                else:
                    detail = (
                        "Legacy plaintext blob migrated to encrypted storage. "
                        "Old blob retained."
                    )
                results.append(
                    RawReencryptionItemResult(
                        raw_id=raw_id_text,
                        graph_id=graph_text,
                        filename=filename,
                        old_sha256=old_sha,
                        status="reencrypted",
                        detail=detail,
                        new_sha256=new_sha,
                        raw_ref_updated=True,
                        storage_rows_updated=storage_rows_updated,
                        legacy_blob_deleted=legacy_blob_deleted,
                    )
                )
            except Exception as exc:  # nosec B110
                session.rollback()
                failed += 1

                if new_blob_written and new_sha:
                    try:
                        delete_new_fn = getattr(base_store, "delete_by_sha", None)
                        if callable(delete_new_fn):
                            delete_new_fn(new_sha)
                    except Exception:
                        pass

                results.append(
                    RawReencryptionItemResult(
                        raw_id=raw_id_text,
                        graph_id=graph_text,
                        filename=filename,
                        old_sha256=old_sha,
                        status="failed",
                        detail=str(exc),
                    )
                )

        offset += len(rows)

    result = RawReencryptionRunResult(
        graph_id=graph_id,
        cutoff_created_at=cutoff_created_at,
        dry_run=dry_run,
        irreversible=irreversible,
        scanned=scanned,
        already_encrypted=already_encrypted,
        reencrypted=reencrypted,
        failed=failed,
        results=results,
    )

    if event_repo is not None:
        try:
            event_repo.emit(
                session,
                graph_id or "default",
                "RAW_REENCRYPTION",
                {
                    "tenant_id": tenant_id,
                    "graph_id": graph_id,
                    "cutoff_created_at": cutoff_created_at.isoformat(),
                    "dry_run": dry_run,
                    "irreversible": irreversible,
                    "reason": reason,
                    "scanned": result.scanned,
                    "already_encrypted": result.already_encrypted,
                    "reencrypted": result.reencrypted,
                    "failed": result.failed,
                },
            )
            session.commit()
        except Exception:  # nosec B110
            session.rollback()

    return result


__all__ = [
    "RawReencryptionItemResult",
    "RawReencryptionRunResult",
    "run_raw_reencryption_backfill",
]
