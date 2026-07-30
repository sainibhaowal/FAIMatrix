"""Tenant crypto rotation / rewrap job utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional

from store.crypto.envelope import (
    generate_dek,
    get_master_key_ring,
    master_key_fingerprint,
    unwrap_dek_with_ring,
    wrap_dek_with_current_key,
)
from store.pg.models_crypto import TenantCryptoKey

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TenantCryptoRotationItemResult:
    tenant_id: str
    status: str
    detail: Optional[str] = None
    source_master_key_fingerprint: Optional[str] = None
    master_key_fingerprint: Optional[str] = None


@dataclass(frozen=True)
class TenantCryptoRotationRunResult:
    tenant_id: Optional[str]
    dry_run: bool
    scanned: int
    already_current: int
    rewrapped: int
    created: int
    failed: int
    results: List[TenantCryptoRotationItemResult] = field(default_factory=list)


def run_tenant_crypto_rotation_backfill(
    *,
    session: Any,
    tenant_id: Optional[str],
    dry_run: bool = True,
    reason: Optional[str] = None,
) -> TenantCryptoRotationRunResult:
    """Rewrap tenant DEKs under the current master key.

    This is a metadata-only rotation: payload blobs remain encrypted under the
    same tenant DEK. The job only rewraps the tenant DEK with the active master
    key so a master-key cutover can complete safely.
    """
    master_keys = get_master_key_ring()
    current_fingerprint = master_key_fingerprint(master_keys[0])

    query = session.query(TenantCryptoKey)
    if tenant_id is not None:
        query = query.filter(TenantCryptoKey.tenant_id == tenant_id)
    rows = query.order_by(TenantCryptoKey.tenant_id.asc()).all()

    scanned = 0
    already_current = 0
    rewrapped = 0
    created = 0
    failed = 0
    results: List[TenantCryptoRotationItemResult] = []

    for row in rows:
        scanned += 1
        row_tenant = str(row.tenant_id)
        row_fingerprint = str(getattr(row, "master_key_fingerprint", "") or "").strip()

        if row.dek_wrapped and row_fingerprint == current_fingerprint:
            already_current += 1
            results.append(
                TenantCryptoRotationItemResult(
                    tenant_id=row_tenant,
                    status="already_current",
                    detail="Tenant DEK already wrapped by current master key",
                    source_master_key_fingerprint=row_fingerprint or None,
                    master_key_fingerprint=current_fingerprint,
                )
            )
            continue

        try:
            if dry_run:
                if row.dek_wrapped:
                    _, source_index = unwrap_dek_with_ring(
                        bytes(row.dek_wrapped), master_keys
                    )
                    source_fp = master_key_fingerprint(master_keys[source_index])
                    detail = "Tenant DEK would be rewrapped under current master key"
                else:
                    source_fp = None
                    detail = "Tenant DEK would be created and wrapped under current master key"
                results.append(
                    TenantCryptoRotationItemResult(
                        tenant_id=row_tenant,
                        status="would_rewrap",
                        detail=detail,
                        source_master_key_fingerprint=source_fp,
                        master_key_fingerprint=current_fingerprint,
                    )
                )
                continue

            if row.dek_wrapped:
                dek, source_index = unwrap_dek_with_ring(bytes(row.dek_wrapped), master_keys)
                source_fp = master_key_fingerprint(master_keys[source_index])
            else:
                dek = generate_dek()
                source_fp = None
                created += 1

            new_wrapped, fingerprint = wrap_dek_with_current_key(dek, master_keys)
            row.dek_wrapped = new_wrapped
            row.master_key_fingerprint = fingerprint
            row.rotated_at = datetime.now(timezone.utc)
            rewrapped += 1
            session.flush()
            results.append(
                TenantCryptoRotationItemResult(
                    tenant_id=row_tenant,
                    status="rewrapped",
                    detail=(
                        "Tenant DEK rewrapped under current master key"
                        if reason is None
                        else f"Tenant DEK rewrapped under current master key ({reason})"
                    ),
                    source_master_key_fingerprint=source_fp,
                    master_key_fingerprint=fingerprint,
                )
            )
        except Exception as exc:  # nosec B110
            failed += 1
            logger.warning(
                "Tenant crypto rotation failed tenant=%s: %s", row_tenant, exc
            )
            results.append(
                TenantCryptoRotationItemResult(
                    tenant_id=row_tenant,
                    status="failed",
                    detail=str(exc),
                    source_master_key_fingerprint=row_fingerprint or None,
                    master_key_fingerprint=current_fingerprint,
                )
            )

    if not dry_run:
        session.commit()

    return TenantCryptoRotationRunResult(
        tenant_id=tenant_id,
        dry_run=dry_run,
        scanned=scanned,
        already_current=already_current,
        rewrapped=rewrapped,
        created=created,
        failed=failed,
        results=results,
    )


__all__ = [
    "TenantCryptoRotationItemResult",
    "TenantCryptoRotationRunResult",
    "run_tenant_crypto_rotation_backfill",
]
