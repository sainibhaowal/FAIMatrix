"""Shared self-evolve enqueue scheduler (Phase S3).

Single source of truth for write-triggered self-evolution enqueue decisions.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Union
from uuid import UUID

from sqlalchemy import and_, asc
from sqlalchemy.orm import Session

from orchestration.jobs.job_store import JobStore
from runtime.feature_flags import get_feature_flags
from store.pg.models_faim import GraphVersionModel, JobModel
from store.pg.repos.graph_version_repo import GraphVersionRepo
from store.pg.repos.self_evolution_state_repo import SelfEvolutionStateRepo

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SelfEvolveEnqueueResult:
    """Result of shared self-evolve enqueue decision."""

    status: str  # enqueued | existing | skipped
    reason: str
    job_id: Optional[UUID] = None
    graph_version: int = 0
    version_delta: int = 0


@dataclass(frozen=True)
class SelfEvolveScanSummary:
    """Periodic scan summary for autonomous worker scheduling."""

    tenant_id: str
    scanned_graphs: int
    enqueued: int
    existing: int
    skipped: int
    errors: int
    trigger_mode: str
    reason: Optional[str] = None


def _jobs_enabled() -> bool:
    raw = os.getenv("FAIM_ENABLE_JOBS", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _normalize_dt(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _active_evolve_job(
    *,
    session: Session,
    tenant_id: str,
    graph_id: str,
) -> Optional[JobModel]:
    return (
        session.query(JobModel)
        .filter(
            and_(
                JobModel.tenant_id == tenant_id,
                JobModel.graph_id == graph_id,
                JobModel.kind == "evolve",
                JobModel.status.in_(["pending", "running"]),
            )
        )
        .order_by(JobModel.created_at.asc())
        .first()
    )


def _is_write_trigger_source(source_key: str) -> bool:
    return source_key in {
        "storage_upload",
        "ingest_json",
        "ingest_upload",
        "memory_write",
    }


def _is_periodic_source(source_key: str) -> bool:
    return source_key in {"periodic_worker", "worker_periodic"}


def _source_allowed_for_mode(*, source_key: str, trigger_mode: str) -> bool:
    if _is_write_trigger_source(source_key):
        return trigger_mode in {"post_upload", "hybrid"}
    if _is_periodic_source(source_key):
        return trigger_mode in {"periodic", "hybrid"}
    return False


def list_self_evolve_tenants(
    *,
    session: Session,
    limit: int = 1000,
) -> List[str]:
    """List tenants that currently have graph-version state."""
    rows = (
        session.query(GraphVersionModel.tenant_id)
        .filter(GraphVersionModel.tenant_id.isnot(None))
        .distinct()
        .order_by(asc(GraphVersionModel.tenant_id))
        .limit(max(1, int(limit)))
        .all()
    )
    tenants: List[str] = []
    for row in rows:
        value = str(row[0]).strip() if row and row[0] is not None else ""
        if value:
            tenants.append(value)
    return tenants


def enqueue_self_evolve_if_due(
    *,
    session: Session,
    tenant_id: str,
    graph_id: str,
    source: str,
    source_job_id: Optional[Union[str, UUID]] = None,
    request_id: Optional[str] = None,
    profile: str = "strict",
    persist_mode: str = "relaxed",
    self_invent_requested: Optional[bool] = None,
    now: Optional[datetime] = None,
) -> SelfEvolveEnqueueResult:
    """Enqueue evolve job if trigger policy and due conditions are satisfied.

    Dedup rule:
    - At most one pending/running evolve job per tenant+graph.
    """
    flags = get_feature_flags()

    source_key = str(source or "").strip().lower() or "unknown"
    legacy_storage_compat = (
        source_key == "storage_upload"
        and flags.self_invent_enabled
        and flags.self_invent_after_upload
    )

    if not flags.self_evolve_enabled and not legacy_storage_compat:
        return SelfEvolveEnqueueResult(
            status="skipped",
            reason="self_evolve_disabled",
        )

    # For write-triggered enqueue we only allow post_upload/hybrid modes.
    if flags.self_evolve_enabled:
        trigger_mode = str(flags.self_evolve_trigger_mode or "").strip().lower()
        if _is_write_trigger_source(source_key) and trigger_mode not in {
            "post_upload",
            "hybrid",
        }:
            return SelfEvolveEnqueueResult(
                status="skipped",
                reason=f"trigger_mode_not_write_triggered:{trigger_mode or 'unknown'}",
            )
        if _is_periodic_source(source_key) and trigger_mode not in {
            "periodic",
            "hybrid",
        }:
            return SelfEvolveEnqueueResult(
                status="skipped",
                reason=f"trigger_mode_not_periodic:{trigger_mode or 'unknown'}",
            )
        if not _source_allowed_for_mode(
            source_key=source_key,
            trigger_mode=trigger_mode,
        ):
            return SelfEvolveEnqueueResult(
                status="skipped",
                reason=f"unsupported_source:{source_key}",
            )

    if not _jobs_enabled():
        return SelfEvolveEnqueueResult(
            status="skipped",
            reason="jobs_disabled",
        )

    ts_now = _normalize_dt(now) or datetime.now(timezone.utc)

    gv_repo = GraphVersionRepo(session=session, tenant_id=tenant_id)
    state_repo = SelfEvolutionStateRepo(session=session, tenant_id=tenant_id)

    current_version = int(gv_repo.get_version(session, graph_id) or 0)
    state = state_repo.mark_seen_version(
        graph_id=graph_id,
        seen_version=current_version,
        session=session,
    )

    last_evolved_version = int(state.last_evolved_version or 0)
    version_delta = current_version - last_evolved_version
    if version_delta < int(flags.self_evolve_min_version_delta):
        return SelfEvolveEnqueueResult(
            status="skipped",
            reason=(
                "not_due_version_delta"
                f":{version_delta}<{int(flags.self_evolve_min_version_delta)}"
            ),
            graph_version=current_version,
            version_delta=version_delta,
        )

    last_evolved_at = _normalize_dt(state.last_evolved_at)
    if last_evolved_at is not None:
        elapsed_seconds = int((ts_now - last_evolved_at).total_seconds())
        if elapsed_seconds < int(flags.self_evolve_min_interval_seconds):
            return SelfEvolveEnqueueResult(
                status="skipped",
                reason=(
                    "not_due_interval"
                    f":{elapsed_seconds}<{int(flags.self_evolve_min_interval_seconds)}"
                ),
                graph_version=current_version,
                version_delta=version_delta,
            )

    existing = _active_evolve_job(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
    )
    if existing is not None:
        state_repo.mark_enqueued(
            graph_id=graph_id,
            job_id=existing.job_id,
            seen_version=current_version,
            session=session,
        )
        session.commit()
        return SelfEvolveEnqueueResult(
            status="existing",
            reason="active_evolve_job_exists",
            job_id=existing.job_id,
            graph_version=current_version,
            version_delta=version_delta,
        )

    if self_invent_requested is None:
        self_invent_requested = bool(
            flags.self_invent_enabled and flags.self_invent_on_evolve
        )

    payload = {
        "profile": str(profile or "strict"),
        "persist_mode": str(persist_mode or "relaxed"),
        "source": source_key,
        "self_invent_requested": bool(self_invent_requested),
        "trigger_graph_version": current_version,
        "trigger_version_delta": version_delta,
    }
    if source_job_id is not None:
        payload["source_job_id"] = str(source_job_id)
    if request_id:
        payload["request_id"] = str(request_id)

    evolve_job_id = JobStore.enqueue(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        kind="evolve",
        payload=payload,
    )
    state_repo.mark_enqueued(
        graph_id=graph_id,
        job_id=evolve_job_id,
        seen_version=current_version,
        session=session,
    )
    session.commit()

    try:
        JobStore.append_event(
            session,
            evolve_job_id,
            "step_start",
            {
                "message": "Evolve job enqueued from shared self-evolve scheduler",
                "source": source_key,
                "source_job_id": str(source_job_id) if source_job_id else None,
            },
        )
    except Exception as exc:  # nosec B110
        logger.warning(
            "Failed to append scheduler enqueue event for evolve job %s: %s",
            evolve_job_id,
            exc,
        )

    return SelfEvolveEnqueueResult(
        status="enqueued",
        reason="due_enqueued",
        job_id=evolve_job_id,
        graph_version=current_version,
        version_delta=version_delta,
    )


def scan_and_enqueue_due_self_evolve_jobs(
    *,
    session: Session,
    tenant_id: str,
    now: Optional[datetime] = None,
    request_id: Optional[str] = None,
    source: str = "periodic_worker",
) -> SelfEvolveScanSummary:
    """Periodic autonomous scan for due graphs within one tenant."""
    flags = get_feature_flags()
    trigger_mode = str(flags.self_evolve_trigger_mode or "").strip().lower()

    if not flags.self_evolve_enabled:
        return SelfEvolveScanSummary(
            tenant_id=tenant_id,
            scanned_graphs=0,
            enqueued=0,
            existing=0,
            skipped=0,
            errors=0,
            trigger_mode=trigger_mode,
            reason="self_evolve_disabled",
        )
    if not _jobs_enabled():
        return SelfEvolveScanSummary(
            tenant_id=tenant_id,
            scanned_graphs=0,
            enqueued=0,
            existing=0,
            skipped=0,
            errors=0,
            trigger_mode=trigger_mode,
            reason="jobs_disabled",
        )
    if trigger_mode not in {"periodic", "hybrid"}:
        return SelfEvolveScanSummary(
            tenant_id=tenant_id,
            scanned_graphs=0,
            enqueued=0,
            existing=0,
            skipped=0,
            errors=0,
            trigger_mode=trigger_mode,
            reason=f"trigger_mode_not_periodic:{trigger_mode or 'unknown'}",
        )

    state_repo = SelfEvolutionStateRepo(session=session, tenant_id=tenant_id)
    ts_now = _normalize_dt(now) or datetime.now(timezone.utc)
    due_candidates = state_repo.select_due_graphs(
        min_version_delta=int(flags.self_evolve_min_version_delta),
        min_interval_seconds=int(flags.self_evolve_min_interval_seconds),
        limit=max(1, int(flags.self_evolve_max_actions)),
        now=ts_now,
        session=session,
    )

    enqueued = 0
    existing = 0
    skipped = 0
    errors = 0

    for candidate in due_candidates:
        try:
            decision = enqueue_self_evolve_if_due(
                session=session,
                tenant_id=tenant_id,
                graph_id=candidate.graph_id,
                source=source,
                request_id=request_id,
                profile="strict",
                persist_mode="relaxed",
                self_invent_requested=None,
                now=ts_now,
            )
            if decision.status == "enqueued":
                enqueued += 1
            elif decision.status == "existing":
                existing += 1
            else:
                skipped += 1
        except Exception as exc:  # nosec B110
            errors += 1
            logger.warning(
                "self-evolve periodic enqueue failed tenant=%s graph=%s: %s",
                tenant_id,
                candidate.graph_id,
                exc,
            )

    return SelfEvolveScanSummary(
        tenant_id=tenant_id,
        scanned_graphs=len(due_candidates),
        enqueued=enqueued,
        existing=existing,
        skipped=skipped,
        errors=errors,
        trigger_mode=trigger_mode,
        reason=None,
    )


__all__ = [
    "SelfEvolveEnqueueResult",
    "SelfEvolveScanSummary",
    "enqueue_self_evolve_if_due",
    "list_self_evolve_tenants",
    "scan_and_enqueue_due_self_evolve_jobs",
]
