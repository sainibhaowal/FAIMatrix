"""Autonomous domain adaptation scheduling and execution."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_

from orchestration.jobs.job_store import JobStore
from store.pg.models_faim import JobModel

logger = logging.getLogger(__name__)


def _jobs_enabled() -> bool:
    raw = os.getenv("FAIM_ENABLE_JOBS", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _domain_autonomy_enabled() -> bool:
    raw = os.getenv("FAIM_DOMAIN_AUTONOMY_ENABLED", "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    return True


@dataclass(frozen=True)
class DomainAutonomyScheduleResult:
    status: str
    reason: str
    job_id: Optional[UUID] = None


def enqueue_domain_autonomy_if_needed(
    *,
    session,
    tenant_id: str,
    graph_id: str,
    source: str,
    request_id: Optional[str] = None,
) -> DomainAutonomyScheduleResult:
    if not _domain_autonomy_enabled():
        return DomainAutonomyScheduleResult(
            status="skipped", reason="domain_autonomy_disabled"
        )
    existing = (
        session.query(JobModel)
        .filter(
            and_(
                JobModel.tenant_id == tenant_id,
                JobModel.graph_id == graph_id,
                JobModel.kind == "domain_autonomy",
                JobModel.status.in_(["pending", "running"]),
            )
        )
        .order_by(JobModel.created_at.asc())
        .first()
    )
    if existing is not None:
        return DomainAutonomyScheduleResult(
            status="existing",
            reason="domain_autonomy_job_already_active",
            job_id=existing.job_id,
        )

    job_id = JobStore.enqueue(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        kind="domain_autonomy",
        payload={
            "source": str(source or "unknown"),
            "request_id": str(request_id or "").strip() or None,
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    JobStore.append_event(
        session,
        job_id,
        "step_start",
        {
            "message": "Autonomous domain adaptation enqueued",
            "source": str(source or "unknown"),
        },
    )
    return DomainAutonomyScheduleResult(
        status="enqueued",
        reason="domain_autonomy_job_enqueued",
        job_id=job_id,
    )


def run_domain_autonomy_now(
    *,
    session,
    tenant_id: str,
    graph_id: str,
    raw_repo,
    storage_file_repo,
    raw_store,
    node_repo,
    gv_repo,
    event_repo=None,
):
    from orchestration.domain_profile_rebuild import run_domain_profile_rebuild

    return run_domain_profile_rebuild(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        raw_repo=raw_repo,
        storage_file_repo=storage_file_repo,
        raw_store=raw_store,
        node_repo=node_repo,
        gv_repo=gv_repo,
        event_repo=event_repo,
        domain_pack=None,
    )


__all__ = [
    "DomainAutonomyScheduleResult",
    "enqueue_domain_autonomy_if_needed",
    "run_domain_autonomy_now",
]
