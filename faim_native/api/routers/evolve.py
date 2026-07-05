"""FAIM-Native API: Evolve Router.

POST /v1/evolve - Run evolution cycle on graph.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["evolve"])


# =============================================================================
# Request/Response Models
# =============================================================================


class EvolveRequest(BaseModel):
    """Evolve request body."""

    graph_id: str
    profile: str = "strict"
    persist_mode: str = "relaxed"
    self_invent_requested: Optional[bool] = None


class EvolveResponse(BaseModel):
    """Evolve response."""

    status: str
    graph_version: int
    merges: int
    prunes: int
    inventions: int = 0
    diagnostics: Optional[Dict[str, Any]] = None
    events_emitted: List[str]
    latency_ms: int
    requested_profile: Optional[str] = None
    requested_persist_mode: Optional[str] = None
    effective_profile: Optional[str] = None
    effective_persist_mode: Optional[str] = None
    durability_path: Optional[str] = None
    evolve_aggressiveness: Optional[str] = None
    completion_mode: Optional[str] = None
    state_update_status: Optional[str] = None
    state_update_error: Optional[str] = None
    error: Optional[str] = None


class EvolveStatusRuntime(BaseModel):
    """Runtime flags that influence self-evolve behavior."""

    self_evolve_enabled: bool
    self_evolve_trigger_mode: str
    self_evolve_min_interval_seconds: int
    self_evolve_min_version_delta: int
    self_evolve_max_actions: int
    self_evolve_scan_interval_seconds: int
    self_invent_enabled: bool
    self_invent_on_evolve: bool
    jobs_enabled: bool


class EvolveStatusGuardrails(BaseModel):
    """Human-facing summary of the self-evolve guardrail state."""

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
    control_updated_at: Optional[str] = None
    control_updated_by: Optional[str] = None


class EvolveControlState(BaseModel):
    """Persisted graph-scoped autonomy controls."""

    self_evolve_enabled: bool
    self_evolve_trigger_mode: str
    self_invent_enabled: bool
    self_invent_on_evolve: bool
    self_invent_after_upload: bool
    source: str
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    can_edit: bool = False


class EvolveControlUpdateRequest(BaseModel):
    """Request body for updating graph-scoped autonomy controls."""

    self_evolve_enabled: bool
    self_evolve_trigger_mode: str
    self_invent_enabled: bool
    self_invent_on_evolve: bool
    self_invent_after_upload: bool


class EvolveStatusState(BaseModel):
    """Durable scheduler state summary for one graph."""

    graph_id: str
    graph_version: int
    last_seen_version: int
    last_evolved_version: int
    last_evolved_at: Optional[str] = None
    last_enqueued_job_id: Optional[str] = None


class EvolveStatusDue(BaseModel):
    """Read-only due-evaluation summary."""

    source: str
    is_due: bool
    reason: str
    graph_version: int
    last_seen_version: int
    last_evolved_version: int
    version_delta: int
    min_version_delta: int
    min_interval_seconds: int
    elapsed_since_last_evolved_seconds: Optional[int] = None


class EvolveStatusJobSummary(BaseModel):
    """Compact evolve job summary for status views."""

    job_id: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    source: Optional[str] = None
    trigger_graph_version: Optional[int] = None
    trigger_version_delta: Optional[int] = None
    self_invent_requested: Optional[bool] = None


class EvolveStatusLastEvent(BaseModel):
    """Last event summary with evolve-specific hints."""

    last_event_seq: int
    last_event_kind: Optional[str] = None
    last_event_ts: Optional[str] = None
    last_snapshot_hash: Optional[str] = None
    last_skip_reason: Optional[str] = None


class EvolveStatusResponse(BaseModel):
    """Aggregate status response for Evolution dashboard Step B."""

    graph_id: str
    tenant_id: str
    runtime: EvolveStatusRuntime
    control: EvolveControlState
    guardrails: EvolveStatusGuardrails
    state: EvolveStatusState
    due: EvolveStatusDue
    active_job: Optional[EvolveStatusJobSummary] = None
    last_enqueued_job: Optional[EvolveStatusJobSummary] = None
    last_event: EvolveStatusLastEvent


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        return value.isoformat()
    except Exception:  # nosec B110
        return None


def _job_summary(job: Any) -> Optional[EvolveStatusJobSummary]:
    if job is None:
        return None
    payload = getattr(job, "payload_json", {}) or {}
    return EvolveStatusJobSummary(
        job_id=str(job.job_id),
        status=str(job.status),
        created_at=_iso(getattr(job, "created_at", None)),
        updated_at=_iso(getattr(job, "updated_at", None)),
        started_at=_iso(getattr(job, "started_at", None)),
        completed_at=_iso(getattr(job, "completed_at", None)),
        error_message=getattr(job, "error_message", None),
        source=payload.get("source"),
        trigger_graph_version=payload.get("trigger_graph_version"),
        trigger_version_delta=payload.get("trigger_version_delta"),
        self_invent_requested=payload.get("self_invent_requested"),
    )


def _control_access_allowed(request: Request) -> bool:
    tenant_id = str(getattr(request.state, "tenant_id", "") or "").strip()
    return bool(tenant_id)


def _control_access_or_403(request: Request) -> None:
    if not _control_access_allowed(request):
        raise HTTPException(
            status_code=403,
            detail="Evolution control changes require an authenticated tenant session",
        )


def _control_state_to_response(
    *,
    control: Any,
    can_edit: bool,
) -> EvolveControlState:
    return EvolveControlState(
        self_evolve_enabled=bool(getattr(control, "self_evolve_enabled", False)),
        self_evolve_trigger_mode=str(
            getattr(control, "self_evolve_trigger_mode", "") or "manual"
        ),
        self_invent_enabled=bool(getattr(control, "self_invent_enabled", False)),
        self_invent_on_evolve=bool(getattr(control, "self_invent_on_evolve", False)),
        self_invent_after_upload=bool(
            getattr(control, "self_invent_after_upload", False)
        ),
        source=str(getattr(control, "source", "runtime_default") or "runtime_default"),
        updated_at=_iso(getattr(control, "updated_at", None)),
        updated_by=getattr(control, "updated_by", None),
        can_edit=bool(can_edit),
    )


# =============================================================================
# Evolve Endpoint
# =============================================================================


@router.post("/evolve", response_model=EvolveResponse)
async def evolve_graph(
    request: EvolveRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> EvolveResponse:
    """Run one evolution cycle on the graph.

    Uses lock manager to prevent concurrent evolution.
    Returns MetricsSnapshot (Stage-4.1.1 contract).
    """
    try:
        from orchestration.evolve_flow import FAIMProfile, PersistMode, run_evolve

        profile = FAIMProfile(request.profile.lower())
        persist_mode = PersistMode(request.persist_mode.lower())

        result = run_evolve(
            graph_id=request.graph_id,
            tenant_id=ctx.tenant_id,
            session=ctx.session,
            profile=profile,
            persist_mode=persist_mode,
            self_invent_requested=request.self_invent_requested,
            node_repo=ctx.node_repo,
            edge_repo=ctx.edge_repo,
            event_repo=ctx.event_repo,
            gv_repo=ctx.gv_repo,
        )

        return EvolveResponse(
            status=result.status,
            graph_version=result.graph_version,
            merges=result.merges,
            prunes=result.prunes,
            inventions=result.inventions,
            diagnostics=result.diagnostics,
            events_emitted=result.events_emitted,
            latency_ms=result.latency_ms,
            requested_profile=result.requested_profile,
            requested_persist_mode=result.requested_persist_mode,
            effective_profile=result.effective_profile,
            effective_persist_mode=result.effective_persist_mode,
            durability_path=result.durability_path,
            evolve_aggressiveness=result.evolve_aggressiveness,
            completion_mode=result.completion_mode,
            state_update_status=result.state_update_status,
            state_update_error=result.state_update_error,
            error=result.error,
        )

    except Exception as e:
        logger.error(f"Evolve failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


@router.get("/evolve/status", response_model=EvolveStatusResponse)
async def evolve_status(
    request: Request,
    graph_id: str = Query(...),
    source: str = Query("memory_write"),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> EvolveStatusResponse:
    """Return read-only self-evolve runtime/scheduler status for one graph."""
    try:
        from orchestration.self_evolve_scheduler import (
            build_self_evolve_guardrail_summary,
            evaluate_self_evolve_due,
        )
        from runtime.feature_flags import get_feature_flags
        from store.pg.models_faim import JobModel
        from store.pg.repos.self_evolution_state_repo import SelfEvolutionStateRepo

        flags = get_feature_flags()
        control_repo = SelfEvolutionStateRepo(
            session=ctx.session, tenant_id=ctx.tenant_id
        )
        control = control_repo.resolve_control_state(
            graph_id=graph_id, session=ctx.session
        )
        can_edit = _control_access_allowed(request)
        guardrails = build_self_evolve_guardrail_summary(
            session=ctx.session,
            tenant_id=ctx.tenant_id,
            graph_id=graph_id,
        )
        due = evaluate_self_evolve_due(
            session=ctx.session,
            tenant_id=ctx.tenant_id,
            graph_id=graph_id,
            source=source,
            update_seen_version=False,
        )

        state_repo = SelfEvolutionStateRepo(
            session=ctx.session, tenant_id=ctx.tenant_id
        )
        state = state_repo.get(graph_id=graph_id, session=ctx.session)

        active_job = (
            ctx.session.query(JobModel)
            .filter(
                JobModel.tenant_id == ctx.tenant_id,
                JobModel.graph_id == graph_id,
                JobModel.kind == "evolve",
                JobModel.status.in_(["pending", "running"]),
            )
            .order_by(JobModel.created_at.asc())
            .first()
        )

        last_enqueued_job = None
        if due.last_enqueued_job_id is not None:
            last_enqueued_job = (
                ctx.session.query(JobModel)
                .filter(
                    JobModel.tenant_id == ctx.tenant_id,
                    JobModel.job_id == due.last_enqueued_job_id,
                )
                .first()
            )

        latest_event = ctx.event_repo.get_latest(ctx.session, graph_id=graph_id)
        recent = ctx.event_repo.get_by_seq(
            ctx.session,
            graph_id=graph_id,
            after_seq=0,
            limit=200,
        )
        last_snapshot_hash = None
        last_skip_reason = None
        for event in reversed(recent):
            if last_snapshot_hash is None and event.kind == "DIAGNOSTICS_SNAPSHOT":
                payload = event.payload or {}
                last_snapshot_hash = payload.get("graph_hash")
            if last_skip_reason is None and event.kind == "EVOLUTION_SKIPPED":
                payload = event.payload or {}
                reason = payload.get("reason")
                if isinstance(reason, str) and reason.strip():
                    last_skip_reason = reason
            if last_snapshot_hash is not None and last_skip_reason is not None:
                break

        return EvolveStatusResponse(
            graph_id=graph_id,
            tenant_id=ctx.tenant_id,
            runtime=EvolveStatusRuntime(
                self_evolve_enabled=bool(control.self_evolve_enabled),
                self_evolve_trigger_mode=str(control.self_evolve_trigger_mode),
                self_evolve_min_interval_seconds=int(
                    flags.self_evolve_min_interval_seconds
                ),
                self_evolve_min_version_delta=int(flags.self_evolve_min_version_delta),
                self_evolve_max_actions=int(flags.self_evolve_max_actions),
                self_evolve_scan_interval_seconds=int(
                    flags.self_evolve_scan_interval_seconds
                ),
                self_invent_enabled=bool(control.self_invent_enabled),
                self_invent_on_evolve=bool(control.self_invent_on_evolve),
                jobs_enabled=bool(due.jobs_enabled),
            ),
            control=_control_state_to_response(control=control, can_edit=can_edit),
            guardrails=EvolveStatusGuardrails(
                self_evolve_enabled=guardrails.self_evolve_enabled,
                self_invent_enabled=guardrails.self_invent_enabled,
                self_invent_on_evolve=guardrails.self_invent_on_evolve,
                self_invent_after_upload=guardrails.self_invent_after_upload,
                jobs_enabled=guardrails.jobs_enabled,
                trigger_mode=guardrails.trigger_mode,
                automation_path=guardrails.automation_path,
                automation_label=guardrails.automation_label,
                automation_enabled=guardrails.automation_enabled,
                guardrail_reason=guardrails.guardrail_reason,
                control_source=guardrails.control_source,
                control_updated_at=_iso(guardrails.control_updated_at),
                control_updated_by=guardrails.control_updated_by,
            ),
            state=EvolveStatusState(
                graph_id=graph_id,
                graph_version=int(due.graph_version or 0),
                last_seen_version=int(getattr(state, "last_seen_version", 0) or 0),
                last_evolved_version=int(
                    getattr(state, "last_evolved_version", 0) or 0
                ),
                last_evolved_at=_iso(getattr(state, "last_evolved_at", None)),
                last_enqueued_job_id=(
                    str(getattr(state, "last_enqueued_job_id", ""))
                    if getattr(state, "last_enqueued_job_id", None) is not None
                    else None
                ),
            ),
            due=EvolveStatusDue(
                source=due.source,
                is_due=bool(due.is_due),
                reason=due.reason,
                graph_version=int(due.graph_version or 0),
                last_seen_version=int(due.last_seen_version or 0),
                last_evolved_version=int(due.last_evolved_version or 0),
                version_delta=int(due.version_delta or 0),
                min_version_delta=int(due.min_version_delta or 0),
                min_interval_seconds=int(due.min_interval_seconds or 0),
                elapsed_since_last_evolved_seconds=due.elapsed_since_last_evolved_seconds,
            ),
            active_job=_job_summary(active_job),
            last_enqueued_job=_job_summary(last_enqueued_job),
            last_event=EvolveStatusLastEvent(
                last_event_seq=int(getattr(latest_event, "seq", 0) or 0),
                last_event_kind=getattr(latest_event, "kind", None),
                last_event_ts=_iso(getattr(latest_event, "ts", None)),
                last_snapshot_hash=last_snapshot_hash,
                last_skip_reason=last_skip_reason,
            ),
        )
    except Exception as e:
        logger.error("Failed to load evolve status: %s", e)
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


@router.patch("/evolve/control", response_model=EvolveStatusResponse)
async def update_evolve_control(
    graph_id: str,
    body: EvolveControlUpdateRequest,
    request: Request,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> EvolveStatusResponse:
    """Persist graph-scoped self-evolve/self-invent controls."""
    _control_access_or_403(request)
    try:
        from store.pg.repos.self_evolution_state_repo import SelfEvolutionStateRepo

        control_repo = SelfEvolutionStateRepo(
            session=ctx.session, tenant_id=ctx.tenant_id
        )
        control_repo.update_control_state(
            graph_id=graph_id,
            self_evolve_enabled=body.self_evolve_enabled,
            self_evolve_trigger_mode=body.self_evolve_trigger_mode,
            self_invent_enabled=body.self_invent_enabled,
            self_invent_on_evolve=body.self_invent_on_evolve,
            self_invent_after_upload=body.self_invent_after_upload,
            updated_by=str(getattr(request.state, "email", "") or "").strip() or None,
            session=ctx.session,
        )
        ctx.session.commit()
        return await evolve_status(graph_id=graph_id, source="memory_write", ctx=ctx, request=request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update evolve control: %s", e)
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


__all__ = ["router"]
