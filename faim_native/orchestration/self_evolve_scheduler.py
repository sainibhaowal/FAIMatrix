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

from orchestration.jobs.job_store import JobStore
from runtime.feature_flags import get_feature_flags
from sqlalchemy import and_, asc
from sqlalchemy.orm import Session
from store.pg.models_faim import GraphVersionModel, JobModel
from store.pg.repos.graph_version_repo import GraphVersionRepo
from store.pg.repos.self_evolution_state_repo import (
    SelfEvolutionStateRepo,
)

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


@dataclass(frozen=True)
class SelfEvolveDueEvaluation:
    """Read-only self-evolve due evaluation result."""

    is_due: bool
    reason: str
    source: str
    trigger_mode: str
    self_evolve_enabled: bool
    jobs_enabled: bool
    source_allowed: bool
    graph_version: int = 0
    last_seen_version: int = 0
    last_evolved_version: int = 0
    version_delta: int = 0
    min_version_delta: int = 0
    min_interval_seconds: int = 0
    elapsed_since_last_evolved_seconds: Optional[int] = None
    last_evolved_at: Optional[datetime] = None
    active_job_id: Optional[UUID] = None
    last_enqueued_job_id: Optional[UUID] = None


@dataclass(frozen=True)
class SelfEvolveGuardrailSummary:
    """Human-facing summary of the self-evolve automation guardrails."""

    self_evolve_enabled: bool
    self_invent_enabled: bool
    self_invent_on_evolve: bool
    self_invent_after_upload: bool
    jobs_enabled: bool
    trigger_mode: str
    automation_path: str
    automation_label: str
    automation_enabled: bool
    guardrail_reason: str
    control_source: str
    control_updated_at: Optional[datetime]
    control_updated_by: Optional[str]


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


def build_self_evolve_guardrail_summary(
    *,
    session: Session,
    tenant_id: str,
    graph_id: str,
) -> SelfEvolveGuardrailSummary:
    """Summarize the currently active self-evolve/self-invent guardrails.

    The result is intentionally operator-facing: it explains whether the system
    is manual-only, after-upload, periodic, hybrid, or legacy-compat.
    """
    state_repo = SelfEvolutionStateRepo(session=session, tenant_id=tenant_id)
    control = state_repo.resolve_control_state(graph_id=graph_id, session=session)
    jobs_enabled = _jobs_enabled()
    trigger_mode = str(control.self_evolve_trigger_mode or "").strip().lower()
    legacy_upload_compat = bool(
        not control.self_evolve_enabled
        and control.self_invent_enabled
        and control.self_invent_after_upload
    )

    if legacy_upload_compat:
        return SelfEvolveGuardrailSummary(
            self_evolve_enabled=bool(control.self_evolve_enabled),
            self_invent_enabled=bool(control.self_invent_enabled),
            self_invent_on_evolve=bool(control.self_invent_on_evolve),
            self_invent_after_upload=bool(control.self_invent_after_upload),
            jobs_enabled=jobs_enabled,
            trigger_mode=trigger_mode or "manual",
            automation_path="legacy_post_upload_compat",
            automation_label="Legacy after-upload compatibility",
            automation_enabled=bool(jobs_enabled),
            guardrail_reason="legacy_upload_compat",
            control_source=control.source,
            control_updated_at=control.updated_at,
            control_updated_by=control.updated_by,
        )

    if not control.self_evolve_enabled:
        return SelfEvolveGuardrailSummary(
            self_evolve_enabled=False,
            self_invent_enabled=bool(control.self_invent_enabled),
            self_invent_on_evolve=bool(control.self_invent_on_evolve),
            self_invent_after_upload=bool(control.self_invent_after_upload),
            jobs_enabled=jobs_enabled,
            trigger_mode=trigger_mode or "manual",
            automation_path="disabled",
            automation_label="Disabled",
            automation_enabled=False,
            guardrail_reason="self_evolve_disabled",
            control_source=control.source,
            control_updated_at=control.updated_at,
            control_updated_by=control.updated_by,
        )

    if trigger_mode == "manual":
        return SelfEvolveGuardrailSummary(
            self_evolve_enabled=True,
            self_invent_enabled=bool(control.self_invent_enabled),
            self_invent_on_evolve=bool(control.self_invent_on_evolve),
            self_invent_after_upload=bool(control.self_invent_after_upload),
            jobs_enabled=jobs_enabled,
            trigger_mode=trigger_mode,
            automation_path="manual_only",
            automation_label="Manual only",
            automation_enabled=False,
            guardrail_reason="manual_mode",
            control_source=control.source,
            control_updated_at=control.updated_at,
            control_updated_by=control.updated_by,
        )

    if trigger_mode == "post_upload":
        return SelfEvolveGuardrailSummary(
            self_evolve_enabled=True,
            self_invent_enabled=bool(control.self_invent_enabled),
            self_invent_on_evolve=bool(control.self_invent_on_evolve),
            self_invent_after_upload=bool(control.self_invent_after_upload),
            jobs_enabled=jobs_enabled,
            trigger_mode=trigger_mode,
            automation_path="post_upload_worker",
            automation_label="After upload",
            automation_enabled=bool(jobs_enabled),
            guardrail_reason="post_upload_worker",
            control_source=control.source,
            control_updated_at=control.updated_at,
            control_updated_by=control.updated_by,
        )

    if trigger_mode == "periodic":
        return SelfEvolveGuardrailSummary(
            self_evolve_enabled=True,
            self_invent_enabled=bool(control.self_invent_enabled),
            self_invent_on_evolve=bool(control.self_invent_on_evolve),
            self_invent_after_upload=bool(control.self_invent_after_upload),
            jobs_enabled=jobs_enabled,
            trigger_mode=trigger_mode,
            automation_path="periodic_worker",
            automation_label="Periodic worker",
            automation_enabled=bool(jobs_enabled),
            guardrail_reason="periodic_worker",
            control_source=control.source,
            control_updated_at=control.updated_at,
            control_updated_by=control.updated_by,
        )

    return SelfEvolveGuardrailSummary(
        self_evolve_enabled=True,
        self_invent_enabled=bool(control.self_invent_enabled),
        self_invent_on_evolve=bool(control.self_invent_on_evolve),
        self_invent_after_upload=bool(control.self_invent_after_upload),
        jobs_enabled=jobs_enabled,
        trigger_mode=trigger_mode,
        automation_path="hybrid_worker",
        automation_label="Upload + periodic",
        automation_enabled=bool(jobs_enabled),
        guardrail_reason="hybrid_worker",
        control_source=control.source,
        control_updated_at=control.updated_at,
        control_updated_by=control.updated_by,
    )


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


def evaluate_self_evolve_due(
    *,
    session: Session,
    tenant_id: str,
    graph_id: str,
    source: str,
    now: Optional[datetime] = None,
    update_seen_version: bool = False,
) -> SelfEvolveDueEvaluation:
    """Evaluate self-evolve due decision without enqueue side effects."""
    source_key = str(source or "").strip().lower() or "unknown"
    state_repo = SelfEvolutionStateRepo(session=session, tenant_id=tenant_id)
    control = state_repo.resolve_control_state(graph_id=graph_id, session=session)
    trigger_mode = str(control.self_evolve_trigger_mode or "").strip().lower()
    legacy_storage_compat = (
        source_key == "storage_upload"
        and not control.self_evolve_enabled
        and control.self_invent_enabled
        and control.self_invent_after_upload
    )

    if not control.self_evolve_enabled and not legacy_storage_compat:
        return SelfEvolveDueEvaluation(
            is_due=False,
            reason="self_evolve_disabled",
            source=source_key,
            trigger_mode=trigger_mode,
            self_evolve_enabled=bool(control.self_evolve_enabled),
            jobs_enabled=_jobs_enabled(),
            source_allowed=False,
        )

    if control.self_evolve_enabled:
        if _is_write_trigger_source(source_key) and trigger_mode not in {
            "post_upload",
            "hybrid",
        }:
            return SelfEvolveDueEvaluation(
                is_due=False,
                reason=f"trigger_mode_not_write_triggered:{trigger_mode or 'unknown'}",
                source=source_key,
                trigger_mode=trigger_mode,
                self_evolve_enabled=bool(control.self_evolve_enabled),
                jobs_enabled=_jobs_enabled(),
                source_allowed=False,
            )
        if _is_periodic_source(source_key) and trigger_mode not in {
            "periodic",
            "hybrid",
        }:
            return SelfEvolveDueEvaluation(
                is_due=False,
                reason=f"trigger_mode_not_periodic:{trigger_mode or 'unknown'}",
                source=source_key,
                trigger_mode=trigger_mode,
                self_evolve_enabled=bool(control.self_evolve_enabled),
                jobs_enabled=_jobs_enabled(),
                source_allowed=False,
            )
        source_allowed = _source_allowed_for_mode(
            source_key=source_key,
            trigger_mode=trigger_mode,
        )
        if not source_allowed:
            return SelfEvolveDueEvaluation(
                is_due=False,
                reason=f"unsupported_source:{source_key}",
                source=source_key,
                trigger_mode=trigger_mode,
                self_evolve_enabled=bool(control.self_evolve_enabled),
                jobs_enabled=_jobs_enabled(),
                source_allowed=False,
            )
    else:
        source_allowed = True

    jobs_enabled = _jobs_enabled()
    if not jobs_enabled:
        return SelfEvolveDueEvaluation(
            is_due=False,
            reason="jobs_disabled",
            source=source_key,
            trigger_mode=trigger_mode,
            self_evolve_enabled=bool(control.self_evolve_enabled),
            jobs_enabled=False,
            source_allowed=source_allowed,
        )

    ts_now = _normalize_dt(now) or datetime.now(timezone.utc)
    gv_repo = GraphVersionRepo(session=session, tenant_id=tenant_id)
    state_repo = SelfEvolutionStateRepo(session=session, tenant_id=tenant_id)

    current_version = int(gv_repo.get_version(session, graph_id) or 0)
    if update_seen_version:
        state = state_repo.mark_seen_version(
            graph_id=graph_id,
            seen_version=current_version,
            session=session,
        )
    else:
        state = state_repo.get(graph_id=graph_id, session=session)

    last_seen_version = int(getattr(state, "last_seen_version", 0) or 0)
    last_evolved_version = int(getattr(state, "last_evolved_version", 0) or 0)
    last_enqueued_job_id = getattr(state, "last_enqueued_job_id", None)
    if last_enqueued_job_id is not None and not isinstance(last_enqueued_job_id, UUID):
        try:
            last_enqueued_job_id = UUID(str(last_enqueued_job_id))
        except (TypeError, ValueError):
            last_enqueued_job_id = None

    version_delta = current_version - last_evolved_version
    flags = get_feature_flags()
    min_version_delta = int(flags.self_evolve_min_version_delta)
    if version_delta < min_version_delta:
        return SelfEvolveDueEvaluation(
            is_due=False,
            reason=f"not_due_version_delta:{version_delta}<{min_version_delta}",
            source=source_key,
            trigger_mode=trigger_mode,
            self_evolve_enabled=bool(control.self_evolve_enabled),
            jobs_enabled=jobs_enabled,
            source_allowed=source_allowed,
            graph_version=current_version,
            last_seen_version=last_seen_version,
            last_evolved_version=last_evolved_version,
            version_delta=version_delta,
            min_version_delta=min_version_delta,
            min_interval_seconds=int(flags.self_evolve_min_interval_seconds),
            last_enqueued_job_id=last_enqueued_job_id,
        )

    min_interval_seconds = int(flags.self_evolve_min_interval_seconds)
    last_evolved_at = _normalize_dt(getattr(state, "last_evolved_at", None))
    elapsed_seconds: Optional[int] = None
    if last_evolved_at is not None:
        elapsed_seconds = int((ts_now - last_evolved_at).total_seconds())
        if elapsed_seconds < min_interval_seconds:
            return SelfEvolveDueEvaluation(
                is_due=False,
                reason=f"not_due_interval:{elapsed_seconds}<{min_interval_seconds}",
                source=source_key,
                trigger_mode=trigger_mode,
                self_evolve_enabled=bool(control.self_evolve_enabled),
                jobs_enabled=jobs_enabled,
                source_allowed=source_allowed,
                graph_version=current_version,
                last_seen_version=last_seen_version,
                last_evolved_version=last_evolved_version,
                version_delta=version_delta,
                min_version_delta=min_version_delta,
                min_interval_seconds=min_interval_seconds,
                elapsed_since_last_evolved_seconds=elapsed_seconds,
                last_evolved_at=last_evolved_at,
                last_enqueued_job_id=last_enqueued_job_id,
            )

    active_job = _active_evolve_job(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
    )
    if active_job is not None:
        return SelfEvolveDueEvaluation(
            is_due=False,
            reason="active_evolve_job_exists",
            source=source_key,
            trigger_mode=trigger_mode,
            self_evolve_enabled=bool(control.self_evolve_enabled),
            jobs_enabled=jobs_enabled,
            source_allowed=source_allowed,
            graph_version=current_version,
            last_seen_version=last_seen_version,
            last_evolved_version=last_evolved_version,
            version_delta=version_delta,
            min_version_delta=min_version_delta,
            min_interval_seconds=min_interval_seconds,
            elapsed_since_last_evolved_seconds=elapsed_seconds,
            last_evolved_at=last_evolved_at,
            active_job_id=active_job.job_id,
            last_enqueued_job_id=last_enqueued_job_id,
        )

    return SelfEvolveDueEvaluation(
        is_due=True,
        reason="due_enqueued",
        source=source_key,
        trigger_mode=trigger_mode,
        self_evolve_enabled=bool(control.self_evolve_enabled),
        jobs_enabled=jobs_enabled,
        source_allowed=source_allowed,
        graph_version=current_version,
        last_seen_version=last_seen_version,
        last_evolved_version=last_evolved_version,
        version_delta=version_delta,
        min_version_delta=min_version_delta,
        min_interval_seconds=min_interval_seconds,
        elapsed_since_last_evolved_seconds=elapsed_seconds,
        last_evolved_at=last_evolved_at,
        last_enqueued_job_id=last_enqueued_job_id,
    )


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
    evaluation = evaluate_self_evolve_due(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        source=source,
        now=now,
        update_seen_version=True,
    )
    source_key = evaluation.source
    current_version = int(evaluation.graph_version or 0)
    version_delta = int(evaluation.version_delta or 0)

    if not evaluation.is_due:
        if (
            evaluation.reason == "active_evolve_job_exists"
            and evaluation.active_job_id is not None
        ):
            state_repo = SelfEvolutionStateRepo(session=session, tenant_id=tenant_id)
            state_repo.mark_enqueued(
                graph_id=graph_id,
                job_id=evaluation.active_job_id,
                seen_version=current_version,
                session=session,
            )
            session.commit()
            return SelfEvolveEnqueueResult(
                status="existing",
                reason=evaluation.reason,
                job_id=evaluation.active_job_id,
                graph_version=current_version,
                version_delta=version_delta,
            )
        return SelfEvolveEnqueueResult(
            status="skipped",
            reason=evaluation.reason,
            graph_version=current_version,
            version_delta=version_delta,
        )

    if self_invent_requested is None:
        self_invent_requested = bool(
            flags.self_invent_enabled and flags.self_invent_on_evolve
        )

    from orchestration.profile_persist_policy import (
        PolicyOperation,
        resolve_profile_persist_policy,
    )

    policy = resolve_profile_persist_policy(
        operation=PolicyOperation.EVOLVE,
        requested_profile=str(profile or "strict"),
        requested_persist_mode=str(persist_mode or "relaxed"),
    )

    payload = {
        "profile": policy.effective_profile,
        "persist_mode": policy.effective_persist_mode,
        "requested_profile": str(profile or "strict"),
        "requested_persist_mode": str(persist_mode or "relaxed"),
        "effective_profile": policy.effective_profile,
        "effective_persist_mode": policy.effective_persist_mode,
        "durability_path": policy.durability_path,
        "evolve_aggressiveness": policy.evolve_aggressiveness,
        "evolve_action_budget_scale": policy.evolve_action_budget_scale,
        "evolve_merge_threshold": policy.evolve_merge_threshold,
        "evolve_prune_min_age_days": policy.evolve_prune_min_age_days,
        "evolve_prune_max_touch_count": policy.evolve_prune_max_touch_count,
        "evolve_prune_similarity_threshold": policy.evolve_prune_similarity_threshold,
        "evolve_invention_mode": policy.evolve_invention_mode,
        "evolve_invention_requested_default": (
            policy.evolve_invention_requested_default
        ),
        "evolve_invention_max_macros_cap": policy.evolve_invention_max_macros_cap,
        "profile_persist_compat_mode": policy.compatibility_mode,
        "profile_persist_coercion_reason": policy.coercion_reason,
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
    state_repo = SelfEvolutionStateRepo(session=session, tenant_id=tenant_id)
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

    # Refuse to scan when the trigger mode forbids periodic automation. The
    # mode gate must be cheap and at the scan boundary so non-periodic
    # deployments never run due-graph selection or materialize scheduler state.
    source_key = str(source or "").strip().lower() or "periodic_worker"
    if _is_periodic_source(source_key) and trigger_mode not in {
        "periodic",
        "hybrid",
    }:
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
    default_profile = "strict"
    try:
        from runtime.config import get_config

        cfg = get_config()
        candidate = str(getattr(cfg, "profile_default", "STRICT")).strip().lower()
        if candidate in {"strict", "fast", "relaxed"}:
            default_profile = candidate
    except Exception:  # nosec B110
        default_profile = "strict"

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
                profile=default_profile,
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
    "SelfEvolveDueEvaluation",
    "SelfEvolveEnqueueResult",
    "SelfEvolveScanSummary",
    "SelfEvolveGuardrailSummary",
    "build_self_evolve_guardrail_summary",
    "evaluate_self_evolve_due",
    "enqueue_self_evolve_if_due",
    "list_self_evolve_tenants",
    "scan_and_enqueue_due_self_evolve_jobs",
]
