"""FAIM-Native API: Evolve Router.

POST /v1/evolve - Run evolution cycle on graph.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
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
    theories: int = 0
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
    learning: Optional[Dict[str, Any]] = None
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


class InventionFlowChildDetail(BaseModel):
    """One constituent (parent) chunk of a synthesized macro node."""

    id: str
    label: str
    type: str
    similarity: float


class MergeDecision(BaseModel):
    """Why a node won/lost a merge: the full verdict used by the selector."""

    selector: str  # semantic | legacy_hash
    score_winner: float
    score_loser: float
    tie_break: Optional[str] = None  # score | legacy_hash
    components_winner: Dict[str, float] = {}  # evidence/usage/recency/source/residual


class InventionFlowNode(BaseModel):
    """A single node in the invention flow pipeline view."""

    id: str
    stage: str  # "atom" | "macro" | "merge"
    title: str
    subtitle: str
    cognitive_type: str = "fact"
    pressure_lambda: Optional[float] = None
    child_count: Optional[int] = None
    status: Optional[str] = None  # active | synthesized | winner | pruned
    children_details: Optional[List[InventionFlowChildDetail]] = None
    decision: Optional[MergeDecision] = None
    recent: bool = False  # touched by the latest completed evolution cycle


class InventionFlowStage(BaseModel):
    """Real graph-derived invention pipeline stages."""

    atoms: List[InventionFlowNode]
    macros: List[InventionFlowNode]
    merges: List[InventionFlowNode]


class InventionFlowResponse(BaseModel):
    """Read-only invention flow topology derived from the live graph."""

    graph_id: str
    tenant_id: str
    node_count: int
    macro_count: int
    merge_count: int
    stages: InventionFlowStage
    computed_at: str


class VersionChangeItem(BaseModel):
    """One merge (winner/loser pair) that happened in a cycle."""

    winner_id: str
    loser_id: str
    winner_label: str
    loser_label: str
    score: float
    selector: str


class GraphVersionRow(BaseModel):
    """One completed evolution cycle mapped to a graph version."""

    version: int
    completed_at: Optional[str] = None
    merges: int = 0
    prunes: int = 0
    inventions: int = 0
    diagnostics: Dict[str, float] = {}
    changes: List[VersionChangeItem] = []
    backup_count: int = 0  # pre-action snapshots available for this cycle


class InventionVersionsResponse(BaseModel):
    """Version history with per-cycle diffs derived from the event journal."""

    graph_id: str
    tenant_id: str
    current_version: int
    versions: List[GraphVersionRow]


class BackupItem(BaseModel):
    """One pre-action snapshot held for safe undo."""

    backup_id: str
    node_id: str
    action_type: str
    reason: Optional[str] = None
    version: int
    created_at: Optional[str] = None


class BackupsResponse(BaseModel):
    """Backup journal listing for a graph (optionally per version)."""

    graph_id: str
    tenant_id: str
    count: int
    items: List[BackupItem]


class RestoreRequest(BaseModel):
    """Request to restore backed-up nodes (optionally one version's cycle)."""

    graph_id: str
    version: Optional[int] = None


class RestoreResponse(BaseModel):
    """Result of a restore: how many nodes came back vs already present."""

    graph_id: str
    tenant_id: str
    version: Optional[int] = None
    restored: int
    skipped: int
    node_ids: List[str]


class EvolveMetricsAlert(BaseModel):
    """One health alert with an actionable code and severity."""

    level: str  # info | warning | critical
    code: str
    message: str


class EvolveMetricsResponse(BaseModel):
    """Scrapeable evolution health snapshot for monitoring/alerting."""

    graph_id: str
    tenant_id: str
    generated_at: str
    cycles: Dict[str, Any] = {}
    data_safety: Dict[str, Any] = {}
    learning: Dict[str, Any] = {}
    alerts: List[EvolveMetricsAlert] = []


def _build_evolve_metrics(
    *,
    session: Any,
    tenant_id: str,
    graph_id: str,
) -> EvolveMetricsResponse:
    """Aggregate evolution health: cycles, data safety, learning, alerts."""
    from runtime.feature_flags import get_feature_flags
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.evolution_backup_repo import EvolutionBackupRepo
    from store.pg.repos.evolution_learning_repo import EvolutionLearningRepo

    event_repo = EventRepo(session=session, tenant_id=tenant_id)
    backup_repo = EvolutionBackupRepo(session=session, tenant_id=tenant_id)
    learning_repo = EvolutionLearningRepo(session=session, tenant_id=tenant_id)

    alerts: List[EvolveMetricsAlert] = []
    cycles: Dict[str, Any] = {"count": 0}
    data_safety: Dict[str, Any] = {
        "backups_available": 0,
        "latest_cycle_prunes": 0,
        "latest_cycle_backups": 0,
        "coverage_ok": True,
    }
    learning: Dict[str, Any] = {
        "enabled": False,
        "policy_version": 0,
        "source": "defaults",
        "learned": False,
        "outcomes_count": 0,
        "reward_trend_slope": None,
        "merge_usefulness": None,
        "knob_drift_count": 0,
        "trust_ready": False,
        "trust_threshold": 20,
    }

    # ---- cycles from the event journal ----
    complete_events = event_repo.get_all(
        session=session, graph_id=graph_id, kind="EVOLUTION_COMPLETE"
    )
    cycles["count"] = len(complete_events)
    if complete_events:
        latest = complete_events[-1]
        payload = getattr(latest, "payload", None) or {}
        cycles["last_version"] = int(payload.get("version", 0) or 0)
        cycles["last_completed_at"] = _iso(getattr(latest, "created_at", None))
        cycles["last_merges"] = int(payload.get("merges", 0) or 0)
        cycles["last_prunes"] = int(payload.get("prunes", 0) or 0)
        cycles["last_inventions"] = int(payload.get("inventions", 0) or 0)
        data_safety["latest_cycle_prunes"] = int(payload.get("prunes", 0) or 0)
    else:
        alerts.append(
            EvolveMetricsAlert(
                level="info",
                code="no_cycles_recorded",
                message="No completed evolution cycles recorded for this graph yet.",
            )
        )

    # ---- data safety (backup coverage) ----
    try:
        backups = backup_repo.list_by_graph(graph_id, limit=500)
        data_safety["backups_available"] = len(backups)
    except Exception:  # nosec B110 - backups sidecar is optional
        backups = []
        data_safety["backups_available"] = 0

    latest_version = int(cycles.get("last_version", 0) or 0)
    if latest_version > 0:
        try:
            data_safety["latest_cycle_backups"] = backup_repo.count_for_version(
                graph_id, latest_version
            )
        except Exception:  # nosec B110
            data_safety["latest_cycle_backups"] = 0
    prunes = int(data_safety.get("latest_cycle_prunes", 0) or 0)
    cycle_backups = int(data_safety.get("latest_cycle_backups", 0) or 0)
    data_safety["coverage_ok"] = prunes == 0 or cycle_backups >= prunes
    if prunes > 0 and cycle_backups < prunes:
        alerts.append(
            EvolveMetricsAlert(
                level="critical",
                code="backup_coverage_gap",
                message=(
                    f"Cycle v{latest_version} pruned {prunes} nodes but only "
                    f"{cycle_backups} pre-action backups exist — nodes may be "
                    "lost without a restore path."
                ),
            )
        )

    # ---- learning health ----
    try:
        enabled = bool(get_feature_flags().evolution_learning_enabled)
    except Exception:  # nosec B110
        enabled = False
    learning["enabled"] = enabled

    try:
        from core.learning.evolution_policy import KNOB_DEFAULTS

        outcomes = learning_repo.get_outcomes(graph_id, limit=50)
        learning["outcomes_count"] = len(outcomes)
        sorted_outcomes = sorted(
            outcomes, key=lambda row: row.get("graph_version", 0)
        )
        if len(sorted_outcomes) >= 3:
            xs = [float(r.get("graph_version", 0)) for r in sorted_outcomes]
            ys = [float(r.get("reward", 0.0) or 0.0) for r in sorted_outcomes]
            x_mean = sum(xs) / len(xs)
            y_mean = sum(ys) / len(ys)
            num = sum(
                (x - x_mean) * (y - y_mean)
                for x, y in zip(xs, ys, strict=False)
            )
            den = sum((x - x_mean) ** 2 for x in xs)
            if den > 0:
                learning["reward_trend_slope"] = round(num / den, 6)
        if outcomes:
            learning["last_reward"] = round(
                float(outcomes[0].get("reward", 0.0) or 0.0), 4
            )

        state = None
        try:
            state = learning_repo.load_policy_state(graph_id)
        except Exception:  # nosec B110
            state = None
        if isinstance(state, dict):
            knobs = state.get("knobs") or {}
            drift = sum(
                1
                for key, default in KNOB_DEFAULTS.items()
                if key in knobs
                and abs(float(knobs[key]) - float(default)) > 1e-9
            )
            learning["knob_drift_count"] = int(drift)
            learning["policy_version"] = int(state.get("version") or 0)
            learning["source"] = str(state.get("source") or "defaults")
            learning["learned"] = bool(state.get("learned", False))
            calibration = state.get("lambda_calibration") or {}
            if isinstance(calibration, dict):
                learning["calibration_n"] = int(calibration.get("n", 0) or 0)
                learning["calibration_mean"] = round(
                    float(calibration.get("mean", 0.0) or 0.0), 6
                )
            meta = state.get("meta") or {}
            if isinstance(meta, dict) and "merge_usefulness" in meta:
                learning["merge_usefulness"] = round(
                    float(meta["merge_usefulness"]), 6
                )

        # Latest meta metrics (leaderboard-style) if present.
        try:
            latest_meta = learning_repo.get_latest_meta_metrics(graph_id)
            if isinstance(latest_meta, dict) and latest_meta:
                learning["latest_meta"] = latest_meta
                if "merge_usefulness" in latest_meta:
                    learning["merge_usefulness"] = round(
                        float(latest_meta["merge_usefulness"]), 6
                    )
        except Exception:  # nosec B110
            pass

        outcomes_count = int(learning.get("outcomes_count", 0) or 0)
        learning["trust_ready"] = bool(
            enabled and outcomes_count >= int(learning.get("trust_threshold", 20))
        )

        if outcomes_count == 0:
            alerts.append(
                EvolveMetricsAlert(
                    level="info",
                    code="learning_waiting",
                    message="Learning has no feedback rows yet; reward data "
                    "appears after evolution cycles run under learning.",
                )
            )
        elif not enabled:
            alerts.append(
                EvolveMetricsAlert(
                    level="info",
                    code="learning_disabled",
                    message="Evolution learning is disabled "
                    "(FAIM_EVOLUTION_LEARNING_ENABLED=false) — knobs stay at "
                    "defaults.",
                )
            )
        elif outcomes_count < int(learning.get("trust_threshold", 20)):
            alerts.append(
                EvolveMetricsAlert(
                    level="warning",
                    code="learning_cold_start",
                    message=(
                        f"Learning is active but has only {outcomes_count} "
                        "outcome rows — below the 20-cycle trust threshold. "
                        "Knob movements are not yet trustworthy."
                    ),
                )
            )
    except Exception:  # nosec B110
        pass

    return EvolveMetricsResponse(
        graph_id=graph_id,
        tenant_id=tenant_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        cycles=cycles,
        data_safety=data_safety,
        learning=learning,
        alerts=alerts,
    )


@router.get("/evolve/metrics", response_model=EvolveMetricsResponse)
async def evolve_metrics(
    graph_id: str = Query(...),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> EvolveMetricsResponse:
    """Return a scrapeable evolution health snapshot for monitoring/alerting."""
    try:
        return _build_evolve_metrics(
            session=ctx.session,
            tenant_id=ctx.tenant_id,
            graph_id=graph_id,
        )
    except Exception as e:
        logger.error("Failed to build evolve metrics graph=%s: %s", graph_id, e)
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


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
# Invention Flow Topology (read-only, real graph data)
# =============================================================================

_MAX_ATOMS = 60
_MAX_MACROS = 30
_MAX_MERGES = 40


def _short_id(node_id: Any) -> str:
    value = str(node_id or "")
    if len(value) <= 12:
        return value
    return f"{value[:8]}…{value[-4:]}"


def _truncate(value: str, limit: int) -> str:
    value = (value or "").strip().replace("\n", " ")
    if len(value) <= limit:
        return value
    return f"{value[: limit - 1].rstrip()}…"


def _node_title_text(
    repr_by_id: Dict[str, str],
    node: Any,
    default: str,
) -> str:
    """Best-effort human title for a node from its representation text."""
    node_id = str(getattr(node, "node_id", "") or "")
    if node_id in repr_by_id:
        return _truncate(repr_by_id[node_id], 90)
    return default


def _node_subtitle(node: Any, fallback: str = "") -> str:
    raw_id = getattr(node, "raw_id", None)
    block_id = getattr(node, "block_id", None)
    if raw_id:
        prefix = str(raw_id)
        suffix = f" · {block_id}" if block_id else ""
        return _truncate(f"{prefix}{suffix}", 120)
    if fallback:
        return _truncate(fallback, 120)
    return f"Node {_short_id(getattr(node, 'node_id', ''))}"


def _node_pressure_lambda(node: Any) -> Optional[float]:
    signature = getattr(node, "opp_signature", None) or {}
    if isinstance(signature, dict):
        value = signature.get("lambda_at_invention")
        if isinstance(value, (int, float)):
            return round(float(value), 4)
    return None


def _load_repr_text(
    *,
    session: Any,
    tenant_id: str,
    graph_id: str,
    node_ids: List[str],
) -> Dict[str, str]:
    """Load normalized text for many nodes in one query (best effort)."""
    if not node_ids:
        return {}
    try:
        from store.pg.repos.representation_repo import RepresentationRepo

        repo = RepresentationRepo(session=session, tenant_id=tenant_id)
        rows = repo.list_by_node_ids(graph_id=graph_id, node_ids=node_ids)
        return {
            str(row.node_id): str(getattr(row, "normalized_text", "") or "")
            for row in rows
        }
    except Exception:  # nosec B110 - repr sidecar is optional
        return {}


def _build_invention_flow(
    *,
    session: Any,
    tenant_id: str,
    graph_id: str,
) -> InventionFlowResponse:
    """Derive the invention pipeline stages from the live graph."""
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.node_repo import NodeRepo

    node_repo = NodeRepo(session=session, tenant_id=tenant_id)
    edge_repo = EdgeRepo(session=session, tenant_id=tenant_id)
    event_repo = EventRepo(session=session, tenant_id=tenant_id)

    # Cycle boundary: "recent" = merges that happened since the previous
    # completed cycle (events after the second-to-last EVOLUTION_COMPLETE).
    # With fewer than two completed cycles every recorded merge is recent.
    boundary_seq = 0
    complete_events = event_repo.get_all(
        session=session,
        graph_id=graph_id,
        kind="EVOLUTION_COMPLETE",
    )
    if len(complete_events) >= 2:
        boundary_seq = int(getattr(complete_events[-2], "seq", 0) or 0)
    recent_node_ids: set[str] = set()
    for ev in event_repo.get_all(
        session=session,
        graph_id=graph_id,
        kind="EVOLUTION_MERGE",
        limit=_MAX_MERGES,
    ):
        if int(getattr(ev, "seq", 0) or 0) <= boundary_seq:
            continue
        payload = getattr(ev, "payload", None) or {}
        if isinstance(payload, dict):
            if payload.get("winner_id"):
                recent_node_ids.add(str(payload["winner_id"]))
            if payload.get("loser_id"):
                recent_node_ids.add(str(payload["loser_id"]))

    atoms = node_repo.list_atoms(graph_id=graph_id, limit=_MAX_ATOMS)
    all_nodes = node_repo.list_nodes(graph_id=graph_id, limit=400)
    macros = [n for n in all_nodes if int(getattr(n, "level", 0) or 0) > 0]
    macros = macros[:_MAX_MACROS]

    merge_edges = edge_repo.list_opposition_edges(graph_id=graph_id, limit=_MAX_MERGES)

    all_node_ids: List[str] = []
    for n in list(atoms) + list(macros):
        all_node_ids.append(str(getattr(n, "node_id", "") or ""))
    for edge in merge_edges:
        all_node_ids.append(str(getattr(edge, "src_node_id", "") or ""))
        all_node_ids.append(str(getattr(edge, "dst_node_id", "") or ""))
    repr_by_id = _load_repr_text(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        node_ids=all_node_ids,
    )

    atom_nodes: List[InventionFlowNode] = []
    for node in atoms:
        title = _node_title_text(
            repr_by_id,
            node,
            f"Atom {_short_id(getattr(node, 'node_id', ''))}",
        )
        atom_nodes.append(
            InventionFlowNode(
                id=str(getattr(node, "node_id", "") or ""),
                stage="atom",
                title=title,
                subtitle=_node_subtitle(node),
                cognitive_type=str(
                    getattr(node, "cognitive_type", "") or "fact"
                ).lower(),
                pressure_lambda=_node_pressure_lambda(node),
                status="active",
            )
        )

    macro_nodes: List[InventionFlowNode] = []
    for node in macros:
        macro_id = str(getattr(node, "node_id", "") or "")
        title = _node_title_text(
            repr_by_id,
            node,
            f"Macro {_short_id(macro_id)}",
        )
        parent_edges = edge_repo.get_parents(graph_id=graph_id, child_id=macro_id)
        details: List[InventionFlowChildDetail] = []
        for parent_edge in parent_edges:
            parent_id = str(getattr(parent_edge, "src_node_id", "") or "")
            parent_label = repr_by_id.get(parent_id, "") or _short_id(parent_id)
            details.append(
                InventionFlowChildDetail(
                    id=parent_id,
                    label=_truncate(parent_label, 70),
                    type="chunk",
                    similarity=round(
                        float(getattr(parent_edge, "weight", 0) or 0) / 1e9, 4
                    ),
                )
            )
        macro_nodes.append(
            InventionFlowNode(
                id=macro_id,
                stage="macro",
                title=title,
                subtitle=_node_subtitle(
                    node,
                    f"Synthesized macro · level {int(getattr(node, 'level', 0) or 0)}",
                ),
                cognitive_type=str(
                    getattr(node, "cognitive_type", "") or "work"
                ).lower(),
                pressure_lambda=_node_pressure_lambda(node),
                child_count=len(details),
                status="synthesized",
                children_details=details,
            )
        )

    merge_nodes: List[InventionFlowNode] = []
    for edge in merge_edges:
        src_id = str(getattr(edge, "src_node_id", "") or "")
        dst_id = str(getattr(edge, "dst_node_id", "") or "")
        score = round(float(getattr(edge, "weight", 0) or 0) / 1e9, 4)
        meta = getattr(edge, "meta", None) or {}
        winner_hash = meta.get("winner_hash") if isinstance(meta, dict) else None

        src_node = node_repo.get_by_id(graph_id, src_id)
        dst_node = node_repo.get_by_id(graph_id, dst_id)

        if winner_hash is not None and src_node is not None and dst_node is not None:
            src_is_winner = (
                str(getattr(src_node, "vector_hash", "") or "") == winner_hash
            )
        else:
            src_is_winner = True  # best effort when meta is absent

        winner_node, loser_node = (
            (src_node, dst_node) if src_is_winner else (dst_node, src_node)
        )

        if winner_node is not None:
            decision: Optional[MergeDecision] = None
            if isinstance(meta, dict):
                components = meta.get("components_winner")
                decision = MergeDecision(
                    selector=str(meta.get("selector", "legacy_hash")),
                    score_winner=round(
                        float(meta.get("score_winner", score) or score), 4
                    ),
                    score_loser=round(
                        float(meta.get("score_loser", 0.0) or 0.0), 4
                    ),
                    tie_break=(
                        str(meta["tie_break"]) if meta.get("tie_break") else None
                    ),
                    components_winner={
                        str(k): round(float(v), 4)
                        for k, v in (components or {}).items()
                        if isinstance(v, (int, float))
                    }
                    if isinstance(components, dict)
                    else {},
                )
            merge_nodes.append(
                InventionFlowNode(
                    id=str(getattr(winner_node, "node_id", "") or ""),
                    stage="merge",
                    title=_node_title_text(
                        repr_by_id,
                        winner_node,
                        f"Winner {_short_id(getattr(winner_node, 'node_id', ''))}",
                    ),
                    subtitle=f"Consensus winner · score {score}",
                    cognitive_type=str(
                        getattr(winner_node, "cognitive_type", "") or "fact"
                    ).lower(),
                    pressure_lambda=_node_pressure_lambda(winner_node),
                    status="winner",
                    decision=decision,
                    recent=str(getattr(winner_node, "node_id", "") or "")
                    in recent_node_ids,
                )
            )
        if loser_node is not None:
            merge_nodes.append(
                InventionFlowNode(
                    id=str(getattr(loser_node, "node_id", "") or ""),
                    stage="merge",
                    title=_node_title_text(
                        repr_by_id,
                        loser_node,
                        f"Pruned {_short_id(getattr(loser_node, 'node_id', ''))}",
                    ),
                    subtitle=f"Antisym pruned · score {score}",
                    cognitive_type=str(
                        getattr(loser_node, "cognitive_type", "") or "fact"
                    ).lower(),
                    pressure_lambda=_node_pressure_lambda(loser_node),
                    status="pruned",
                    recent=str(getattr(loser_node, "node_id", "") or "")
                    in recent_node_ids,
                )
            )

    return InventionFlowResponse(
        graph_id=graph_id,
        tenant_id=tenant_id,
        node_count=int(node_repo.count_nodes(graph_id) or 0),
        macro_count=int(node_repo.count_macros(graph_id) or 0),
        merge_count=len(merge_edges),
        stages=InventionFlowStage(
            atoms=atom_nodes,
            macros=macro_nodes,
            merges=merge_nodes,
        ),
        computed_at=datetime.now(timezone.utc).isoformat(),
    )


def _build_invention_versions(
    *,
    session: Any,
    tenant_id: str,
    graph_id: str,
) -> InventionVersionsResponse:
    """Derive per-version cycle diffs from the append-only event journal.

    Each EVOLUTION_COMPLETE event owns every EVOLUTION_MERGE event emitted
    after the previous completion. Merges before the first completion are
    attributed to version 1's cycle.
    """
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.evolution_backup_repo import EvolutionBackupRepo
    from store.pg.repos.graph_version_repo import GraphVersionRepo

    event_repo = EventRepo(session=session, tenant_id=tenant_id)
    gv_repo = GraphVersionRepo(session=session, tenant_id=tenant_id)
    backup_repo = EvolutionBackupRepo(session=session, tenant_id=tenant_id)

    complete_events = event_repo.get_all(
        session=session,
        graph_id=graph_id,
        kind="EVOLUTION_COMPLETE",
    )
    merge_events = event_repo.get_all(
        session=session,
        graph_id=graph_id,
        kind="EVOLUTION_MERGE",
    )

    versions: List[GraphVersionRow] = []
    prev_complete_seq = 0
    for ev in complete_events:
        seq = int(getattr(ev, "seq", 0) or 0)
        payload = getattr(ev, "payload", None) or {}
        version = int(payload.get("version", 0) or 0)
        backup_count = 0
        try:
            backup_count = int(
                backup_repo.count_for_version(graph_id=graph_id, version=version)
                or 0
            )
        except Exception:  # nosec B110 - backup sidecar is optional
            backup_count = 0
        diagnostics: Dict[str, float] = {}
        for key in ("D_hat", "H_hat", "lambda_hat", "redundancy_R",
                    "novelty_N", "energy_E"):
            value = payload.get(key)
            if isinstance(value, (int, float)):
                diagnostics[key] = round(float(value), 6)

        changes: List[VersionChangeItem] = []
        for merge_ev in merge_events:
            m_seq = int(getattr(merge_ev, "seq", 0) or 0)
            if m_seq <= prev_complete_seq or m_seq > seq:
                continue
            merge_payload = getattr(merge_ev, "payload", None) or {}
            winner_id = str(merge_payload.get("winner_id", "") or "")
            loser_id = str(merge_payload.get("loser_id", "") or "")
            if not winner_id or not loser_id:
                continue
            changes.append(
                VersionChangeItem(
                    winner_id=winner_id,
                    loser_id=loser_id,
                    winner_label="",
                    loser_label="",
                    score=round(float(merge_payload.get("score", 0.0) or 0.0), 4),
                    selector=str(
                        merge_payload.get("selector", "legacy_hash")
                    ),
                )
            )
        prev_complete_seq = seq
        versions.append(
            GraphVersionRow(
                version=version,
                completed_at=_iso(getattr(ev, "created_at", None)),
                merges=int(payload.get("merges", 0) or 0),
                prunes=int(payload.get("prunes", 0) or 0),
                inventions=int(payload.get("inventions", 0) or 0),
                diagnostics=diagnostics,
                changes=changes,
                backup_count=backup_count,
            )
        )

    # Resolve human labels for every change participant (best effort).
    change_ids: List[str] = []
    for row in versions:
        for change in row.changes:
            change_ids.append(change.winner_id)
            change_ids.append(change.loser_id)
    if change_ids:
        repr_by_id = _load_repr_text(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            node_ids=list(dict.fromkeys(change_ids)),
        )
        for row in versions:
            for change in row.changes:
                change.winner_label = _truncate(
                    repr_by_id.get(change.winner_id, "")
                    or f"Winner {_short_id(change.winner_id)}",
                    70,
                )
                change.loser_label = _truncate(
                    repr_by_id.get(change.loser_id, "")
                    or f"Pruned {_short_id(change.loser_id)}",
                    70,
                )

    current_version = 0
    try:
        current_version = int(
            gv_repo.get_version(session=session, graph_id=graph_id) or 0
        )
    except Exception:  # nosec B110 - version sidecar is optional
        current_version = 0

    return InventionVersionsResponse(
        graph_id=graph_id,
        tenant_id=tenant_id,
        current_version=current_version,
        versions=versions,
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
            theories=result.theories,
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
            learning=result.learning,
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


@router.get("/evolve/invention/flow", response_model=InventionFlowResponse)
async def invention_flow(
    graph_id: str = Query(...),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> InventionFlowResponse:
    """Return real invention-flow topology (atoms, macros, merges) for a graph.

    Read-only derivation from the live node/edge tables; never invents or
    mutates graph state.
    """
    try:
        return _build_invention_flow(
            session=ctx.session,
            tenant_id=ctx.tenant_id,
            graph_id=graph_id,
        )
    except Exception as e:
        logger.error("Failed to build invention flow graph=%s: %s", graph_id, e)
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


@router.get("/evolve/invention/versions", response_model=InventionVersionsResponse)
async def invention_versions(
    graph_id: str = Query(...),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> InventionVersionsResponse:
    """Return version history with per-cycle diffs for a graph.

    Read-only derivation from the append-only event journal; never mutates
    graph state.
    """
    try:
        return _build_invention_versions(
            session=ctx.session,
            tenant_id=ctx.tenant_id,
            graph_id=graph_id,
        )
    except Exception as e:
        logger.error("Failed to build invention versions graph=%s: %s", graph_id, e)
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


# =============================================================================
# Evolution Backup & Restore (safe undo)
# =============================================================================

_SEMANTIC_EDGE_KINDS = {"synonym", "hypernym", "hyponym", "related"}


def _restore_backups(
    *,
    session: Any,
    tenant_id: str,
    graph_id: str,
    version: Optional[int] = None,
) -> RestoreResponse:
    """Re-insert every backed-up node (and its sidecars) for a graph/version.

    Idempotent: nodes that already exist are skipped, never overwritten.
    """
    from store.pg.models_faim import NodeRepresentationV2Model
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.evolution_backup_repo import EvolutionBackupRepo
    from store.pg.repos.node_repo import NodeRepo

    backup_repo = EvolutionBackupRepo(session=session, tenant_id=tenant_id)
    node_repo = NodeRepo(session=session, tenant_id=tenant_id)
    edge_repo = EdgeRepo(session=session, tenant_id=tenant_id)

    restored: List[str] = []
    skipped: List[str] = []

    for backup in backup_repo.list_by_graph(graph_id, version=version):
        node_json = dict(backup.node_json or {})
        node_id = str(node_json.get("node_id", "") or "")
        if not node_id:
            continue

        if not node_repo.restore_node(graph_id, node_json):
            skipped.append(node_id)
            continue
        restored.append(node_id)

        repr_json = dict(backup.repr_json or {})
        if repr_json and repr_json.get("node_id"):
            try:
                session.add(
                    NodeRepresentationV2Model(
                        node_id=repr_json.get("node_id"),
                        tenant_id=tenant_id,
                        graph_id=graph_id,
                        repr_hash=repr_json.get("repr_hash", ""),
                        normalized_text=repr_json.get("normalized_text", ""),
                        word_counts=repr_json.get("word_counts") or {},
                        phrase_counts=repr_json.get("phrase_counts") or {},
                        skip_counts=repr_json.get("skip_counts") or {},
                        entity_tokens=repr_json.get("entity_tokens") or [],
                        time_tokens=repr_json.get("time_tokens") or [],
                        layout_tokens=repr_json.get("layout_tokens") or [],
                        semantic_phrase_counts=repr_json.get(
                            "semantic_phrase_counts"
                        )
                        or {},
                        concept_counts=repr_json.get("concept_counts") or {},
                        morphology_counts=repr_json.get("morphology_counts") or {},
                        alias_families=repr_json.get("alias_families") or [],
                        transliterated_tokens=repr_json.get(
                            "transliterated_tokens"
                        )
                        or [],
                        stem_families=repr_json.get("stem_families") or [],
                        relation_cues=repr_json.get("relation_cues") or [],
                        value_cues=repr_json.get("value_cues") or [],
                        temporal_cues=repr_json.get("temporal_cues") or [],
                        channel_lengths=repr_json.get("channel_lengths") or {},
                    )
                )
                session.flush()
            except Exception:  # nosec B110 - repr sidecar is optional
                logger.warning(
                    "Representation restore failed for node=%s",
                    node_id,
                    exc_info=True,
                )

        for edge_json in backup.edges_json or []:
            try:
                kind = str(edge_json.get("kind", "") or "")
                src_id = edge_json.get("src_node_id")
                dst_id = edge_json.get("dst_node_id")
                if not src_id or not dst_id:
                    continue
                weight = float(int(edge_json.get("weight", 0) or 0)) / 1e9
                meta = edge_json.get("meta") or {}
                if kind == "opposition":
                    edge_repo.add_opposition_edge(
                        graph_id=graph_id,
                        a_id=src_id,
                        b_id=dst_id,
                        weight=weight,
                        meta=meta,
                    )
                elif kind in _SEMANTIC_EDGE_KINDS:
                    edge_repo.add_semantic_edge(
                        graph_id=graph_id,
                        src_node_id=src_id,
                        dst_node_id=dst_id,
                        semantic_type=kind,
                        semantic_weight=weight,
                        meta=meta,
                    )
            except Exception:  # nosec B110 - edge restore is best-effort
                logger.warning(
                    "Edge restore failed for node=%s kind=%s",
                    node_id,
                    edge_json.get("kind"),
                    exc_info=True,
                )

    return RestoreResponse(
        graph_id=graph_id,
        tenant_id=tenant_id,
        version=version,
        restored=len(restored),
        skipped=len(skipped),
        node_ids=restored,
    )


@router.get("/evolve/backups", response_model=BackupsResponse)
async def list_backups(
    graph_id: str = Query(...),
    version: Optional[int] = Query(None),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> BackupsResponse:
    """List pre-action snapshots available for safe undo (optional version)."""
    from store.pg.repos.evolution_backup_repo import EvolutionBackupRepo

    try:
        backup_repo = EvolutionBackupRepo(
            session=ctx.session, tenant_id=ctx.tenant_id
        )
        rows = backup_repo.list_by_graph(graph_id, version=version)
        return BackupsResponse(
            graph_id=graph_id,
            tenant_id=ctx.tenant_id,
            count=len(rows),
            items=[
                BackupItem(
                    backup_id=str(row.backup_id),
                    node_id=str(row.node_id),
                    action_type=str(row.action_type),
                    reason=row.reason,
                    version=int(row.version or 0),
                    created_at=_iso(row.created_at),
                )
                for row in rows
            ],
        )
    except Exception as e:
        logger.error("Failed to list backups graph=%s: %s", graph_id, e)
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


@router.post("/evolve/backups/restore", response_model=RestoreResponse)
async def restore_backups(
    request: RestoreRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> RestoreResponse:
    """Restore backed-up nodes (and their sidecars) for a graph or version.

    Idempotent and non-destructive: existing nodes are skipped.
    """
    try:
        response = _restore_backups(
            session=ctx.session,
            tenant_id=ctx.tenant_id,
            graph_id=request.graph_id,
            version=request.version,
        )
        ctx.session.commit()
        return response
    except Exception as e:
        logger.error(
            "Failed to restore backups graph=%s: %s", request.graph_id, e
        )
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


# =============================================================================
# Evolution Learning (opt-in via FAIM_EVOLUTION_LEARNING_ENABLED)
# =============================================================================


class EvolutionLearningStateResponse(BaseModel):
    """Read-only learned policy state for a graph."""

    graph_id: str
    enabled: bool
    schema_tag: Optional[str] = None
    policy_version: int = 0
    source: str = "defaults"
    learned: bool = False
    knobs: Dict[str, Any] = {}
    calibration: Dict[str, Any] = {}
    samples: Dict[str, Any] = {}
    meta: Dict[str, Any] = {}
    defaults: Dict[str, float] = {}


class EvolutionLearningOutcomesResponse(BaseModel):
    """Recent learning outcome rows for a graph."""

    graph_id: str
    enabled: bool
    total: int
    outcomes: List[Dict[str, Any]] = []


class EvolutionLearningMetaResponse(BaseModel):
    """Recent meta-metric rows for a graph."""

    graph_id: str
    enabled: bool
    total: int
    meta_metrics: List[Dict[str, Any]] = []


@router.get(
    "/evolve/learning/state", response_model=EvolutionLearningStateResponse
)
async def evolution_learning_state(
    graph_id: str = Query(...),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> EvolutionLearningStateResponse:
    """Return the per-graph learned policy state (knobs + calibration).

    Read-only; never mutates. Shows defaults when learning is disabled.
    """
    from core.learning.evolution_policy import (
        KNOB_DEFAULTS,
        EvolutionPolicy,
    )
    from runtime.feature_flags import get_feature_flags
    from store.pg.repos.evolution_learning_repo import EvolutionLearningRepo

    enabled = bool(get_feature_flags().evolution_learning_enabled)
    repo = EvolutionLearningRepo(session=ctx.session, tenant_id=ctx.tenant_id)
    state = repo.load_policy_state(graph_id)
    policy = EvolutionPolicy.from_state(state, graph_id=graph_id)
    knobs = policy.resolve_knobs()
    calibration = policy.lambda_calibration.to_dict()
    samples = {
        knob: {
            "visits": arm.visits,
            "mean_reward": {
                k: round(float(arm.rewards.get(k, 0.0) / max(1, arm.visits.get(k, 1))), 6)
                for k in arm.visits
            },
        }
        for knob, arm in policy.arms.items()
    }
    return EvolutionLearningStateResponse(
        graph_id=graph_id,
        enabled=enabled,
        schema_tag=str(state.get("schema") or None) if isinstance(state, dict) else None,
        policy_version=int(state.get("version") or 0) if isinstance(state, dict) else 0,
        source=knobs.source,
        learned=knobs.learned,
        knobs=knobs.to_dict(),
        calibration=calibration,
        samples=samples,
        meta=state.get("meta", {}) if isinstance(state, dict) else {},
        defaults=dict(KNOB_DEFAULTS),
    )


@router.get(
    "/evolve/learning/outcomes", response_model=EvolutionLearningOutcomesResponse
)
async def evolution_learning_outcomes(
    graph_id: str = Query(...),
    limit: int = Query(20, ge=1, le=200),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> EvolutionLearningOutcomesResponse:
    """Return recent evolution outcome rows for a graph (newest first)."""
    from runtime.feature_flags import get_feature_flags
    from store.pg.repos.evolution_learning_repo import EvolutionLearningRepo

    enabled = bool(get_feature_flags().evolution_learning_enabled)
    repo = EvolutionLearningRepo(session=ctx.session, tenant_id=ctx.tenant_id)
    rows = repo.get_outcomes(graph_id, limit=limit)
    return EvolutionLearningOutcomesResponse(
        graph_id=graph_id,
        enabled=enabled,
        total=len(rows),
        outcomes=rows,
    )


@router.get(
    "/evolve/learning/meta", response_model=EvolutionLearningMetaResponse
)
async def evolution_learning_meta(
    graph_id: str = Query(...),
    limit: int = Query(20, ge=1, le=200),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> EvolutionLearningMetaResponse:
    """Return recent maturity meta-metric rows for a graph."""
    from runtime.feature_flags import get_feature_flags
    from store.pg.repos.evolution_learning_repo import EvolutionLearningRepo

    enabled = bool(get_feature_flags().evolution_learning_enabled)
    repo = EvolutionLearningRepo(session=ctx.session, tenant_id=ctx.tenant_id)
    rows = repo.get_latest_meta_metrics(graph_id, limit=limit)
    return EvolutionLearningMetaResponse(
        graph_id=graph_id,
        enabled=enabled,
        total=len(rows),
        meta_metrics=rows,
    )


class EvolutionTheoriesResponse(BaseModel):
    """Durable self-evolution theories for a graph."""

    graph_id: str
    total: int
    theories: List[Dict[str, Any]] = []


@router.get(
    "/evolve/theories", response_model=EvolutionTheoriesResponse
)
async def evolution_theories(
    graph_id: str = Query(...),
    limit: int = Query(50, ge=1, le=500),
    theory_type: Optional[str] = Query(None),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> EvolutionTheoriesResponse:
    """Return durable self-evolution theories for a graph (newest first).

    Theories are symbolic generalizations derived by the self-evolution
    loop from observed graph structure (cross-galaxy correlations,
    redundancy clusters, hierarchy composition, cognitive-type mix) and
    gated by evolution pressure λ.
    """
    from store.pg.repos.theory_repo import TheoryRepo

    repo = TheoryRepo(session=ctx.session, tenant_id=ctx.tenant_id)
    rows = repo.list_theories(graph_id, limit=limit, theory_type=theory_type)
    return EvolutionTheoriesResponse(
        graph_id=graph_id,
        total=len(rows),
        theories=rows,
    )


__all__ = ["router"]
