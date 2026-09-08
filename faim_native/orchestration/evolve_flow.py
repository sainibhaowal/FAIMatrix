"""FAIM-Native Orchestration: Evolve Flow.

Pure wiring layer for evolution operations.

Calls core.dynamics.evolution_native.evolve_once() and returns
MetricsSnapshot in Stage-4.1.1 contract format.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy.orm import Session

from .ingest_flow import FAIMProfile, PersistMode
from .profile_persist_policy import PolicyOperation, resolve_profile_persist_policy

logger = logging.getLogger(__name__)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


# =============================================================================
# Types
# =============================================================================


@dataclass(frozen=True)
class EvolveResult:
    """Result returned by run_evolve.

    Attributes:
        status: "completed" or "error"
        graph_version: Graph version after evolution
        merges: Number of merge operations
        prunes: Number of prune operations
        inventions: Number of self-invention macro creations
        theories: Number of self-evolution theories generated
        diagnostics: MetricsSnapshot in Stage-4.1.1 format
        events_emitted: List of event types emitted
        latency_ms: Total latency in milliseconds
        error: Error message if status is "error"
    """

    status: str
    graph_version: int
    merges: int
    prunes: int
    inventions: int
    diagnostics: Optional[Dict[str, Any]]  # MetricsSnapshot.to_dict()
    events_emitted: List[str]
    latency_ms: int
    theories: int = 0
    requested_profile: str = "strict"
    requested_persist_mode: str = "relaxed"
    effective_profile: str = "strict"
    effective_persist_mode: str = "relaxed"
    durability_path: str = "core_sync_secondary_async"
    evolve_aggressiveness: str = "conservative"
    completion_mode: str = "core_sync_state_best_effort"
    state_update_status: str = "not_required"
    state_update_error: Optional[str] = None
    learning: Optional[Dict[str, Any]] = None
    advanced_warnings: List[Dict[str, str]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for API response."""
        return {
            "status": self.status,
            "graph_version": self.graph_version,
            "merges": self.merges,
            "prunes": self.prunes,
            "inventions": self.inventions,
            "theories": self.theories,
            "diagnostics": self.diagnostics,
            "events_emitted": self.events_emitted,
            "latency_ms": self.latency_ms,
            "requested_profile": self.requested_profile,
            "requested_persist_mode": self.requested_persist_mode,
            "effective_profile": self.effective_profile,
            "effective_persist_mode": self.effective_persist_mode,
            "durability_path": self.durability_path,
            "evolve_aggressiveness": self.evolve_aggressiveness,
            "completion_mode": self.completion_mode,
            "state_update_status": self.state_update_status,
            "state_update_error": self.state_update_error,
            "learning": self.learning,
            "advanced_warnings": self.advanced_warnings,
            "error": self.error,
        }


# =============================================================================
# Event Emission
# =============================================================================


def _emit_event(
    event_type: str,
    graph_id: str,
    payload: Dict[str, Any],
    event_repo: Optional[Any] = None,
    session: Optional[Any] = None,
) -> None:
    """Emit event for UI/API consumption."""
    datetime.now(timezone.utc).isoformat()

    logger.info(f"[Event] {event_type}: {payload}")

    if event_repo is not None and session is not None:
        try:
            event_repo.emit(session, graph_id, event_type, payload)
        except Exception as e:
            logger.warning(f"Failed to persist event: {e}")


def _resolve_max_actions(
    *,
    runtime_cfg: Optional[Any],
    flags: Any,
    budget_scale: float,
) -> int:
    base_actions = int(
        getattr(
            runtime_cfg,
            "self_evolve_max_actions",
            getattr(flags, "self_evolve_max_actions", 25),
        )
    )
    scaled = int(round(base_actions * max(0.1, float(budget_scale))))
    return max(1, min(base_actions, scaled))


def _resolve_invention_overrides(
    *,
    runtime_cfg: Optional[Any],
    policy: Any,
) -> Dict[str, Any]:
    base_lambda = float(getattr(runtime_cfg, "self_invent_lambda_threshold", 0.3))
    base_reduction = float(
        getattr(runtime_cfg, "self_invent_min_redundancy_reduction", 0.01)
    )
    base_macros = int(getattr(runtime_cfg, "self_invent_max_macros_per_cycle", 3))
    cap = max(0, int(getattr(policy, "evolve_invention_max_macros_cap", base_macros)))
    macros = min(base_macros, cap) if cap > 0 else 0

    mode = str(getattr(policy, "evolve_invention_mode", "runtime_default"))
    if mode == "conservative":
        base_lambda = min(1.0, base_lambda + 0.10)
        base_reduction = min(1.0, base_reduction + 0.02)
    elif mode == "aggressive":
        base_lambda = max(0.0, base_lambda - 0.05)
        base_reduction = max(0.0, base_reduction - 0.005)

    return {
        "max_macros_per_cycle": max(0, macros),
        "lambda_threshold": base_lambda,
        "min_redundancy_reduction": base_reduction,
    }


def _resolve_lambda_gate(
    *,
    runtime_cfg: Optional[Any],
    policy: Any,
) -> Dict[str, Any]:
    """Resolve lambda-based evolution gate settings from runtime config.

    Returns dict with:
    - enabled: whether lambda gate is enabled
    - min_lambda: minimum lambda to allow evolution (if enabled)
    - scale_actions: whether to scale max_actions by lambda
    """
    enabled = bool(getattr(runtime_cfg, "self_evolve_lambda_gate_enabled", False))
    min_lambda = float(getattr(runtime_cfg, "self_evolve_lambda_gate_min", 0.05))
    scale_actions = bool(getattr(runtime_cfg, "self_evolve_lambda_action_scale", False))

    # Allow policy to override (learning can adjust)
    if hasattr(policy, "evolve_lambda_gate_enabled") and policy.evolve_lambda_gate_enabled is not None:
        enabled = bool(policy.evolve_lambda_gate_enabled)
    if hasattr(policy, "evolve_lambda_gate_min") and policy.evolve_lambda_gate_min is not None:
        min_lambda = max(0.0, min(1.0, float(policy.evolve_lambda_gate_min)))
    if hasattr(policy, "evolve_lambda_action_scale") and policy.evolve_lambda_action_scale is not None:
        scale_actions = bool(policy.evolve_lambda_action_scale)

    return {
        "enabled": enabled,
        "min_lambda": min_lambda,
        "scale_actions": scale_actions,
    }


def _graph_seed(graph_id: str) -> int:
    """Deterministic per-graph seed for the policy RNG."""
    return int(hashlib.sha256(str(graph_id).encode()).hexdigest()[:8], 16)


def _load_learning_policy(
    *,
    graph_id: str,
    tenant_id: str,
    session: Session,
) -> Tuple[Optional[Any], Optional[Any], Optional[Any]]:
    """Load persisted policy + resolved knobs (best effort).

    Returns:
        (learning_repo, policy, knobs) or (None, None, None) on any failure.
    """
    try:
        from core.learning.evolution_policy import EvolutionPolicy
        from store.pg.repos.evolution_learning_repo import EvolutionLearningRepo

        repo = EvolutionLearningRepo(session=session, tenant_id=tenant_id)
        state = repo.load_policy_state(graph_id)
        policy = EvolutionPolicy.from_state(
            state, graph_id=graph_id, seed=_graph_seed(graph_id)
        )
        knobs = policy.resolve_knobs()
        return repo, policy, knobs
    except Exception:  # nosec B110 - learning is best effort
        logger.exception(
            "[Evolve] Learning policy load failed; falling back to defaults"
        )
        return None, None, None


def _compute_before_diagnostics(
    *,
    graph_id: str,
    tenant_id: str,
    session: Session,
    node_repo: Any,
    edge_repo: Any,
    gv_repo: Any,
) -> Optional[Dict[str, float]]:
    """Snapshot pre-evolution fractal diagnostics (best effort)."""
    try:
        from core.dynamics.evolution_native import compute_graph_diagnostics
        from core.metrics.fractal_physics import DEFAULT_CONFIG

        nodes = node_repo.list_nodes(graph_id) if node_repo else []
        edges = edge_repo.list_all_edges(graph_id) if edge_repo else []
        version = int(gv_repo.get_version(session, graph_id) or 0) if gv_repo else 0
        diag = compute_graph_diagnostics(
            graph_id=graph_id,
            nodes=nodes or [],
            edges=edges or [],
            graph_version=version,
            config=DEFAULT_CONFIG,
        )
        return {
            "R": float(diag.redundancy_R or 0.0),
            "N": float(diag.novelty_N or 0.0),
            "E": float(diag.energy_E or 0.0),
            "D": float(diag.D_hat or 0.0),
            "H": float(diag.H_hat or 0.0),
            "lambda": float(diag.lambda_hat or 0.0),
            "node_count": max(0, len(nodes or [])),
        }
    except Exception:  # nosec B110 - learning is best effort
        logger.debug("[Evolve] Before-diagnostics unavailable for learning", exc_info=True)
        return None


def _probe_retrieval(
    *,
    graph_id: str,
    node_repo: Any,
    sample_size: int = 3,
    k: int = 3,
) -> Optional[float]:
    """Deterministic retrieval-quality probe over sampled query nodes.

    For each sampled node (most-used first, deterministic), run a local
    top-k retrieval and score quality as:
        probe = 0.5 * mean_similarity(top-k) + 0.5 * (1 - mean_pairwise_sim)
    which rewards results that stay relevant (mean sim) while becoming more
    diverse (low pairwise redundancy among hits).

    Returns the mean probe value in [0, 1], or None if too few nodes.
    """
    try:
        from core.antisym import cosine_similarity

        nodes = node_repo.list_nodes(graph_id) if node_repo else []
        nodes = [n for n in nodes if getattr(n, "v_native", None)]
        if len(nodes) < 2:
            return None
        # Deterministic sampling: most touched first, then oldest.
        nodes.sort(
            key=lambda n: (
                -int(getattr(n, "touch_count", 0) or 0),
                str(getattr(n, "created_at", "") or ""),
            )
        )
        samples = nodes[: max(1, sample_size)]
        probes: List[float] = []
        for query in samples:
            qv = query.v_native
            scored = []
            for other in nodes:
                if other.node_id == query.node_id:
                    continue
                sim = cosine_similarity(qv, other.v_native)
                scored.append((sim, other.node_id))
            scored.sort(key=lambda x: (-x[0], str(x[1])))
            top = scored[:k]
            if not top:
                continue
            mean_sim = sum(s for s, _ in top) / len(top)
            pairwise = 0.0
            pair_count = 0
            for i in range(len(top)):
                for j in range(i + 1, len(top)):
                    a = next(o for o in nodes if str(o.node_id) == str(top[i][1]))
                    b = next(o for o in nodes if str(o.node_id) == str(top[j][1]))
                    pairwise += cosine_similarity(a.v_native, b.v_native)
                    pair_count += 1
            mean_pairwise = pairwise / max(1, pair_count)
            probes.append(0.5 * mean_sim + 0.5 * (1.0 - mean_pairwise))
        if not probes:
            return None
        return sum(probes) / len(probes)
    except Exception:  # nosec B110 - probe is best effort
        logger.debug("[Evolve] Retrieval probe unavailable", exc_info=True)
        return None


@dataclass
class _LearningCtx:
    """Everything the learning loop needs across one cycle."""

    repo: Any
    policy: Any
    knobs: Any
    before: Optional[Dict[str, float]]
    retrieval_before: Optional[float]
    retrieval_after: Optional[float] = None


def _record_learning_outcome(
    *,
    graph_id: str,
    tenant_id: str,
    session: Session,
    repo: Any,
    policy: Any,
    knobs: Any,
    before: Optional[Dict[str, float]],
    result: Any,
    diagnostics_dict: Optional[Dict[str, Any]],
    node_repo: Any = None,
    retrieval_delta: Optional[float] = None,
    theories: int = 0,
) -> Optional[Dict[str, Any]]:
    """Record one learning cycle: outcome + meta-metrics + policy update.

    Best effort: never raises, never blocks the evolution result.
    """
    try:
        from core.learning.evolution_policy import compute_reward
        from store.pg.repos.evolution_learning_repo import (
            EvolutionOutcome,
            MetaMetricSnapshot,
        )

        if before is None:
            before = {
                "R": 0.0,
                "N": 0.0,
                "E": 0.0,
                "D": 0.0,
                "H": 0.0,
                "lambda": 0.0,
                "node_count": 0,
            }
        after_diag = (diagnostics_dict or {}).get("metrics") or diagnostics_dict or {}
        after = {
            "R": float(after_diag.get("R", after_diag.get("redundancy_R", 0.0))),
            "N": float(
                after_diag.get("novelty", after_diag.get("novelty_N", 0.0))
            ),
            "E": float(after_diag.get("energy", after_diag.get("energy_E", 0.0))),
            "D": float(after_diag.get("D_hat", after_diag.get("D", 0.0))),
            "H": float(after_diag.get("H_hat", after_diag.get("H", 0.0))),
            "lambda": float(
                after_diag.get(
                    "lambda_hat", after_diag.get("lambda", 0.0)
                )
            ),
        }

        reward = compute_reward(
            merges=max(0, int(getattr(result, "merges", 0) or 0)),
            prunes=max(0, int(getattr(result, "prunes", 0) or 0)),
            r_before=before["R"],
            r_after=after["R"],
            n_before=before["N"],
            n_after=after["N"],
            e_before=before["E"],
            e_after=after["E"],
            retrieval_delta=retrieval_delta,
        )

        outcome = EvolutionOutcome(
            graph_version=max(0, int(getattr(result, "graph_version", 0) or 0)),
            merges=max(0, int(getattr(result, "merges", 0) or 0)),
            prunes=max(0, int(getattr(result, "prunes", 0) or 0)),
            inventions=max(0, int(getattr(result, "inventions", 0) or 0)),
            theories=max(0, int(theories or 0)),
            lambda_before=before["lambda"],
            lambda_after=after["lambda"],
            r_before=before["R"],
            r_after=after["R"],
            n_before=before["N"],
            n_after=after["N"],
            d_before=before["D"],
            d_after=after["D"],
            h_before=before["H"],
            h_after=after["H"],
            e_before=before["E"],
            e_after=after["E"],
            retrieval_delta=retrieval_delta,
            reward=reward,
            policy_snapshot=knobs.to_dict() if knobs is not None else {},
        )
        repo.record_outcome(graph_id, outcome, session=session)

        # ---- Meta-metrics: maturity proof derived from this cycle --------
        merges = outcome.merges
        prunes = outcome.prunes
        r_red = (outcome.r_before - outcome.r_after) / max(
            0.05, outcome.r_before
        )
        merge_usefulness = _clamp01(r_red) if merges > 0 else 0.5
        # Regret: pruning that fails to relieve redundancy was wasted work.
        prune_regret = (
            _clamp01(1.0 - r_red) if prunes > 0 and r_red < 0.01 else 0.0
        )
        invention_utilization = _invention_utilization(
            graph_id=graph_id, node_repo=node_repo, session=session
        )
        d_drift = abs(outcome.d_after - outcome.d_before)
        h_drift = abs(outcome.h_after - outcome.h_before)
        alerts: Dict[str, Any] = {}
        if merges > 0 and outcome.r_after > outcome.r_before + 0.01:
            alerts["over_merge_risk"] = True
        if outcome.d_after < outcome.d_before - 0.05:
            alerts["d_collapse"] = True  # collapsing D = over-merging
        if prunes > 0 and prune_regret > 0.5:
            alerts["prune_regret_high"] = True
        meta_snapshot = MetaMetricSnapshot(
            merge_usefulness=merge_usefulness,
            invention_utilization=invention_utilization,
            prune_regret=prune_regret,
            d_drift=d_drift,
            h_drift=h_drift,
            alerts=alerts,
            detail={
                "reward": round(float(reward), 6),
                "retrieval_delta": (
                    round(float(retrieval_delta), 6)
                    if retrieval_delta is not None
                    else None
                ),
                "merges": merges,
                "prunes": prunes,
                "inventions": outcome.inventions,
                "knobs": knobs.to_dict() if knobs is not None else {},
            },
        )
        repo.record_meta_metrics(graph_id, meta_snapshot, session=session)

        if policy is not None and knobs is not None:
            policy.update_from_outcome(
                knobs,
                merges=outcome.merges,
                prunes=outcome.prunes,
                r_before=outcome.r_before,
                r_after=outcome.r_after,
                n_before=outcome.n_before,
                n_after=outcome.n_after,
                e_before=outcome.e_before,
                e_after=outcome.e_after,
                lambda_after=outcome.lambda_after,
                retrieval_delta=retrieval_delta,
                context={
                    "R": outcome.r_before,
                    "N": outcome.n_before,
                    "D": outcome.d_before,
                    "H": outcome.h_before,
                    "node_count": float(before.get("node_count", 0) or 0),
                },
            )
            repo.save_policy_state(
                graph_id,
                arms=policy.to_state()["arms"],
                lambda_calibration=policy.to_state()["lambda_calibration"],
                meta={
                    "schema": "v2",
                    "reward": reward,
                    "retrieval_delta": retrieval_delta,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                policy_version=policy.version,
                session=session,
            )

        try:
            session.commit()
        except Exception:  # nosec B110
            session.rollback()

        return {
            "enabled": True,
            "reward": round(float(reward), 6),
            "retrieval_delta": (
                round(float(retrieval_delta), 6)
                if retrieval_delta is not None
                else None
            ),
            "meta_metrics": {
                "merge_usefulness": round(float(merge_usefulness), 6),
                "invention_utilization": round(
                    float(invention_utilization), 6
                ),
                "prune_regret": round(float(prune_regret), 6),
                "alerts": alerts,
            },
            "policy_version": int(policy.version) if policy is not None else 0,
            "knobs": knobs.to_dict() if knobs is not None else {},
            "before": before,
            "after": after,
        }
    except Exception:  # nosec B110 - learning is best effort
        logger.exception("[Evolve] Learning outcome recording failed")
        try:
            session.rollback()
        except Exception:  # nosec B110
            pass
        return None


def _invention_utilization(
    *,
    graph_id: str,
    node_repo: Any,
    session: Session,
) -> float:
    """Fraction of existing macros that were actually used (touch_count>0).

    Measures whether invented abstractions pay for themselves. Returns 0.0
    when there are no macros (nothing to measure).
    """
    try:
        from store.pg.models_faim import NodeModel

        if node_repo is None or session is None:
            return 0.0
        macros = (
            session.query(NodeModel)
            .filter(
                NodeModel.tenant_id == getattr(node_repo, "tenant_id", "default"),
                NodeModel.graph_id == graph_id,
                NodeModel.kind == "macro",
            )
            .all()
        )
        if not macros:
            return 0.0
        used = sum(1 for m in macros if int(m.touch_count or 0) > 0)
        return _clamp01(used / len(macros))
    except Exception:  # nosec B110 - best effort
        return 0.0


def _mark_self_evolved_state(
    *,
    session: Session,
    tenant_id: str,
    graph_id: str,
    evolved_version: int,
) -> None:
    from store.pg.repos.self_evolution_state_repo import SelfEvolutionStateRepo

    state_repo = SelfEvolutionStateRepo(session=session, tenant_id=tenant_id)
    state_repo.mark_evolved(
        graph_id=graph_id,
        evolved_version=max(0, int(evolved_version)),
        session=session,
    )


# =============================================================================
# Main Evolve Function
# =============================================================================


def run_evolve(
    graph_id: str,
    *,
    tenant_id: str = "default",
    session: Optional[Session] = None,
    profile: Union[FAIMProfile, str] = FAIMProfile.STRICT,
    persist_mode: Union[PersistMode, str] = PersistMode.RELAXED,
    node_repo: Optional[Any] = None,
    edge_repo: Optional[Any] = None,
    event_repo: Optional[Any] = None,
    gv_repo: Optional[Any] = None,
    self_invent_requested: Optional[bool] = None,
) -> EvolveResult:
    """Run one evolution cycle on graph.

    This calls core.dynamics.evolution_native.evolve_once() which:
    1. Computes fractal diagnostics (D/H/λ)
    2. Emits DIAGNOSTICS_SNAPSHOT event
    3. Performs merge operations (based on redundancy)
    4. Performs prune operations (based on policy)
    5. Emits EVOLUTION_COMPLETE on action or EVOLUTION_SKIPPED with reason

    Uses lock manager to prevent concurrent evolution on the same graph.

    Args:
        graph_id: Target graph identifier.
        profile: STRICT (deterministic) or FAST (may use approximations).
        persist_mode: STRICT (wait for commit) or RELAXED (async).
        node_repo: Node repository.
        edge_repo: Edge repository.
        event_repo: Event repository.
        gv_repo: Graph version repository.

    Returns:
        EvolveResult with diagnostics in MetricsSnapshot format.
    """
    start_time = time.time()
    events_emitted: List[str] = []
    advanced_warnings: List[Dict[str, str]] = []

    # Normalize requested values
    if isinstance(profile, str):
        profile = FAIMProfile(profile.lower())
    if isinstance(persist_mode, str):
        persist_mode = PersistMode(persist_mode.lower())
    requested_profile = profile
    requested_persist_mode = persist_mode
    policy = resolve_profile_persist_policy(
        operation=PolicyOperation.EVOLVE,
        requested_profile=requested_profile.value,
        requested_persist_mode=requested_persist_mode.value,
    )
    effective_profile = FAIMProfile(policy.effective_profile)
    effective_persist_mode = PersistMode(policy.effective_persist_mode)

    logger.info(
        "[Evolve] Starting: graph=%s requested=%s/%s effective=%s/%s compat=%s",
        graph_id,
        requested_profile.value,
        requested_persist_mode.value,
        effective_profile.value,
        effective_persist_mode.value,
        policy.compatibility_mode,
    )
    # =========================================================================
    # Initialize repositories if not provided
    # =========================================================================
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.graph_version_repo import GraphVersionRepo
    from store.pg.repos.node_repo import NodeRepo
    from store.pg.session import get_session

    # If session is provided, we use it (typical for worker or transaction-wrapped calls)
    # If not, we open a new one
    own_session = False
    if session is None:
        # Reuse an existing repo-backed session when caller provided repos.
        session = (
            getattr(node_repo, "session", None)
            or getattr(edge_repo, "session", None)
            or getattr(event_repo, "session", None)
            or getattr(gv_repo, "session", None)
        )
        if session is None:
            session = get_session()
            own_session = True

    try:
        if node_repo is None:
            node_repo = NodeRepo(session, tenant_id=tenant_id)
        if edge_repo is None:
            edge_repo = EdgeRepo(session, tenant_id=tenant_id)
        if event_repo is None:
            event_repo = EventRepo(session, tenant_id=tenant_id)
        if gv_repo is None:
            gv_repo = GraphVersionRepo(session, tenant_id=tenant_id)

        # Acquire lock to prevent concurrent evolution on same graph
        from cache.locks import evolve_lock

        with evolve_lock(graph_id) as lock_acquired:
            if not lock_acquired:
                logger.warning(f"[Evolve] Could not acquire lock for graph {graph_id}")
                return EvolveResult(
                    status="error",
                    graph_version=0,
                    merges=0,
                    prunes=0,
                    inventions=0,
                    diagnostics=None,
                    events_emitted=[],
                    latency_ms=int((time.time() - start_time) * 1000),
                    requested_profile=requested_profile.value,
                    requested_persist_mode=requested_persist_mode.value,
                    effective_profile=effective_profile.value,
                    effective_persist_mode=effective_persist_mode.value,
                    durability_path=policy.durability_path,
                    evolve_aggressiveness=policy.evolve_aggressiveness,
                    completion_mode=(
                        "sync_strict"
                        if effective_persist_mode == PersistMode.STRICT
                        else "core_sync_state_best_effort"
                    ),
                    state_update_status="not_started",
                    error="Could not acquire evolution lock (another evolution in progress)",
                )

            try:
                # =====================================================================
                # STEP 0: Emit EVOLUTION_START
                # =====================================================================
                _emit_event(
                    "EVOLUTION_START",
                    graph_id,
                    {
                        "profile": requested_profile.value,
                        "persist_mode": requested_persist_mode.value,
                        "requested_profile": requested_profile.value,
                        "requested_persist_mode": requested_persist_mode.value,
                        "effective_profile": effective_profile.value,
                        "effective_persist_mode": effective_persist_mode.value,
                        "durability_path": policy.durability_path,
                        "profile_persist_compat_mode": policy.compatibility_mode,
                        "profile_persist_coercion_reason": policy.coercion_reason,
                        "evolve_aggressiveness": policy.evolve_aggressiveness,
                        "evolve_action_budget_scale": policy.evolve_action_budget_scale,
                        "evolve_merge_threshold": policy.evolve_merge_threshold,
                        "evolve_prune_min_age_days": policy.evolve_prune_min_age_days,
                        "evolve_prune_max_touch_count": policy.evolve_prune_max_touch_count,
                        "evolve_prune_similarity_threshold": (
                            policy.evolve_prune_similarity_threshold
                        ),
                        "evolve_invention_mode": policy.evolve_invention_mode,
                        "evolve_invention_requested_default": (
                            policy.evolve_invention_requested_default
                        ),
                        "evolve_invention_max_macros_cap": (
                            policy.evolve_invention_max_macros_cap
                        ),
                        "tenant_id": tenant_id,
                    },
                    event_repo,
                    session=session,
                )
                events_emitted.append("EVOLUTION_START")

                # =====================================================================
                # STEP 1: Call evolution_native.evolve_once
                # =====================================================================
                from core.dynamics.evolution_native import evolve_once
                from core.operators.prune import PrunePolicy
                from runtime.feature_flags import get_feature_flags

                runtime_cfg = None
                try:
                    from runtime.config import get_config

                    runtime_cfg = get_config()
                except Exception:  # nosec B110 - fallback for isolated tests
                    runtime_cfg = None

                flags = get_feature_flags()
                learning_enabled = bool(
                    getattr(flags, "evolution_learning_enabled", False)
                )
                learning_ctx: Optional[_LearningCtx] = None
                winner_selector: Optional[Any] = None
                max_actions = _resolve_max_actions(
                    runtime_cfg=runtime_cfg,
                    flags=flags,
                    budget_scale=policy.evolve_action_budget_scale,
                )
                completion_mode = (
                    "sync_strict"
                    if effective_persist_mode == PersistMode.STRICT
                    else "core_sync_state_best_effort"
                )
                event_context = {
                    "requested_profile": requested_profile.value,
                    "requested_persist_mode": requested_persist_mode.value,
                    "effective_profile": effective_profile.value,
                    "effective_persist_mode": effective_persist_mode.value,
                    "durability_path": policy.durability_path,
                    "completion_mode": completion_mode,
                    "evolve_aggressiveness": policy.evolve_aggressiveness,
                }
                prune_policy = PrunePolicy(
                    min_age_days=policy.evolve_prune_min_age_days,
                    max_touch_count=policy.evolve_prune_max_touch_count,
                    min_similarity_for_redundancy=(
                        policy.evolve_prune_similarity_threshold
                    ),
                    protect_macros=True,
                )
                resolved_self_invent_requested = (
                    bool(policy.evolve_invention_requested_default)
                    if self_invent_requested is None
                    else bool(self_invent_requested)
                )
                invention_overrides = _resolve_invention_overrides(
                    runtime_cfg=runtime_cfg,
                    policy=policy,
                )
                lambda_gate = _resolve_lambda_gate(
                    runtime_cfg=runtime_cfg,
                    policy=policy,
                )

                if learning_enabled:
                    learning_repo, l_policy, l_knobs = _load_learning_policy(
                        graph_id=graph_id,
                        tenant_id=tenant_id,
                        session=session,
                    )
                    if l_knobs is not None:
                        from core.dynamics.winner_selection import (
                            select_winner_semantic,
                        )

                        learning_before = _compute_before_diagnostics(
                            graph_id=graph_id,
                            tenant_id=tenant_id,
                            session=session,
                            node_repo=node_repo,
                            edge_repo=edge_repo,
                            gv_repo=gv_repo,
                        )
                        # Contextual bandit features from pre-cycle state.
                        context = None
                        if learning_before is not None:
                            context = {
                                "R": learning_before.get("R", 0.0),
                                "N": learning_before.get("N", 0.0),
                                "D": learning_before.get("D", 0.0),
                                "H": learning_before.get("H", 0.0),
                                "node_count": float(
                                    learning_before.get("node_count", 0) or 0
                                ),
                            }
                        resolved = l_policy.resolve_knobs(context=context)
                        merge_threshold = resolved.merge_threshold
                        prune_policy = PrunePolicy(
                            min_age_days=resolved.prune_min_age_days,
                            max_touch_count=prune_policy.max_touch_count,
                            min_similarity_for_redundancy=(
                                resolved.prune_similarity_threshold
                            ),
                            protect_macros=True,
                        )
                        invention_overrides = dict(invention_overrides)
                        invention_overrides["lambda_threshold"] = (
                            resolved.lambda_threshold
                        )
                        winner_selector = select_winner_semantic
                        learning_ctx = _LearningCtx(
                            repo=learning_repo,
                            policy=l_policy,
                            knobs=resolved,
                            before=learning_before,
                            retrieval_before=_probe_retrieval(
                                graph_id=graph_id,
                                node_repo=node_repo,
                            ),
                        )
                        logger.info(
                            "[Evolve] Learning knobs applied graph=%s "
                            "merge=%.4f sim=%.4f age=%.1fd lambda=%.4f source=%s",
                            graph_id,
                            merge_threshold,
                            prune_policy.min_similarity_for_redundancy,
                            prune_policy.min_age_days,
                            invention_overrides["lambda_threshold"],
                            resolved.source,
                        )

                result = evolve_once(
                    graph_id=graph_id,
                    node_repo=node_repo,
                    edge_repo=edge_repo,
                    event_repo=event_repo,
                    graph_version_repo=gv_repo,
                    max_actions=max_actions,
                    merge_threshold=(
                        merge_threshold
                        if learning_ctx is not None
                        else policy.evolve_merge_threshold
                    ),
                    prune_policy=prune_policy,
                    self_invent_requested=resolved_self_invent_requested,
                    runtime_config=runtime_cfg,
                    invention_overrides=invention_overrides,
                    event_context=event_context,
                    winner_selector=winner_selector,
                    lambda_gate=lambda_gate,
                )
                for warning in list(getattr(result, "warnings", []) or []):
                    advanced_warnings.append(dict(warning))
                    _emit_event(
                        "EVOLUTION_COMPONENT_DEGRADED",
                        graph_id,
                        dict(warning),
                        event_repo,
                        session=session,
                    )

                # evolve_once emits DIAGNOSTICS_SNAPSHOT and either
                # EVOLUTION_COMPLETE or EVOLUTION_SKIPPED.
                events_emitted.append("DIAGNOSTICS_SNAPSHOT")
                if result.skip_reason:
                    events_emitted.append("EVOLUTION_SKIPPED")
                else:
                    events_emitted.append("EVOLUTION_COMPLETE")

                logger.info(
                    f"[Evolve] Complete: {result.merges} merges, "
                    f"{result.prunes} prunes, version={result.graph_version}"
                )

                # =====================================================================
                # STEP 2: Convert diagnostics to MetricsSnapshot format
                # =====================================================================
                diagnostics_dict = None

                if result.diagnostics is not None:
                    try:
                        # Get graph hash for MetricsSnapshot
                        graph_hash = ""
                        if gv_repo is not None:
                            try:
                                gv = gv_repo.get(None, graph_id)
                                graph_hash = getattr(gv, "graph_hash", "")
                            except Exception:  # nosec B110 - graceful fallback
                                pass

                        # Convert FractalDiagnostics to MetricsSnapshot
                        snapshot = result.diagnostics.to_metrics_snapshot(graph_hash)
                        diagnostics_dict = snapshot.to_dict()
                    except Exception as e:
                        warning = {
                            "component": "diagnostics_snapshot",
                            "code": "conversion_failed",
                            "message": type(e).__name__,
                        }
                        advanced_warnings.append(warning)
                        _emit_event(
                            "EVOLUTION_COMPONENT_DEGRADED",
                            graph_id,
                            warning,
                            event_repo,
                            session=session,
                        )
                        logger.warning("Failed to convert diagnostics: %s", e)

                    try:
                        from orchestration.query_flow import persist_graph_diagnostics_snapshot

                        persist_graph_diagnostics_snapshot(
                            session,
                            tenant_id,
                            graph_id,
                            result.diagnostics,
                            graph_version=result.graph_version,
                        )
                        _emit_event(
                            "DIAGNOSTICS_CACHE_REFRESHED",
                            graph_id,
                            {
                                "graph_version": result.graph_version,
                                "diagnostics_hash": getattr(
                                    result.diagnostics, "diagnostics_hash", ""
                                ),
                                "source": "evolution",
                            },
                            event_repo,
                            session=session,
                        )
                        events_emitted.append("DIAGNOSTICS_CACHE_REFRESHED")
                    except Exception as exc:
                        warning = {
                            "component": "diagnostics_cache",
                            "code": "persist_failed",
                            "message": type(exc).__name__,
                        }
                        advanced_warnings.append(warning)
                        _emit_event(
                            "EVOLUTION_COMPONENT_DEGRADED",
                            graph_id,
                            warning,
                            event_repo,
                            session=session,
                        )

                state_update_status = "not_required"
                state_update_error: Optional[str] = None

                # =====================================================================
                # STEP 2c: Self-evolution theory generation (bounded, λ-gated)
                # =====================================================================
                theories_created = 0
                try:
                    from core.dynamics.theory_native import run_theory_cycle
                    from store.pg.repos.theory_repo import TheoryRepo

                    lambda_hat = 0.0
                    if diagnostics_dict is not None:
                        metrics = (
                            diagnostics_dict.get("metrics")
                            or diagnostics_dict.get("metrics_dict")
                            or diagnostics_dict
                        )
                        lambda_hat = float(
                            metrics.get("lambda_hat", metrics.get("λ", 0.0)) or 0.0
                        )
                    theory_result = run_theory_cycle(
                        graph_id=graph_id,
                        session=session,
                        node_repo=node_repo,
                        theory_repo=TheoryRepo(session, tenant_id),
                        graph_version=result.graph_version,
                        lambda_hat=lambda_hat,
                        lambda_threshold=float(
                            (invention_overrides or {}).get(
                                "lambda_threshold", 0.3
                            )
                        ),
                    )
                    theories_created = theory_result.theories_created
                    for error in list(getattr(theory_result, "errors", []) or []):
                        warning = {
                            "component": "theory_generation",
                            "code": "partial_failure",
                            "message": str(error)[:200],
                        }
                        advanced_warnings.append(warning)
                        _emit_event(
                            "EVOLUTION_COMPONENT_DEGRADED",
                            graph_id,
                            warning,
                            event_repo,
                            session=session,
                        )
                    if theories_created > 0:
                        _emit_event(
                            "EVOLUTION_THEORY_SUMMARY",
                            graph_id,
                            {
                                "theories": theories_created,
                                "theory_ids": theory_result.theory_ids,
                                "lambda_hat": round(lambda_hat, 6),
                                "graph_version": result.graph_version,
                            },
                            event_repo,
                            session=session,
                        )
                        events_emitted.append("EVOLUTION_THEORY_SUMMARY")
                        session.commit()
                except Exception as exc:  # nosec B110 - theories are best effort
                    warning = {
                        "component": "theory_generation",
                        "code": "cycle_failed",
                        "message": type(exc).__name__,
                    }
                    advanced_warnings.append(warning)
                    _emit_event(
                        "EVOLUTION_COMPONENT_DEGRADED",
                        graph_id,
                        warning,
                        event_repo,
                        session=session,
                    )
                    logger.warning(
                        "[Evolve] Theory generation skipped graph=%s: %s",
                        graph_id,
                        "exception",
                        exc_info=True,
                    )

                if effective_persist_mode == PersistMode.STRICT:
                    _mark_self_evolved_state(
                        session=session,
                        tenant_id=tenant_id,
                        graph_id=graph_id,
                        evolved_version=result.graph_version,
                    )
                    state_update_status = "completed_sync"
                    _emit_event(
                        "EVOLUTION_PERSISTENCE_APPLIED",
                        graph_id,
                        {
                            "requested_profile": requested_profile.value,
                            "requested_persist_mode": requested_persist_mode.value,
                            "effective_profile": effective_profile.value,
                            "effective_persist_mode": effective_persist_mode.value,
                            "durability_path": policy.durability_path,
                            "completion_mode": completion_mode,
                            "state_update_status": state_update_status,
                            "graph_version": result.graph_version,
                        },
                        event_repo,
                        session=session,
                    )
                    events_emitted.append("EVOLUTION_PERSISTENCE_APPLIED")
                    session.commit()
                else:
                    # Relaxed mode commits core evolution first, then applies
                    # scheduler-state durability as non-fatal best effort.
                    session.commit()
                    state_update_status = "core_committed"
                    try:
                        _mark_self_evolved_state(
                            session=session,
                            tenant_id=tenant_id,
                            graph_id=graph_id,
                            evolved_version=result.graph_version,
                        )
                        state_update_status = "completed_best_effort"
                    except Exception as e:  # nosec B110
                        session.rollback()
                        state_update_status = "best_effort_failed_nonfatal"
                        state_update_error = str(e)[:300]
                        logger.warning(
                            "[Evolve] Relaxed state update failed graph=%s: %s",
                            graph_id,
                            e,
                        )

                    try:
                        _emit_event(
                            "EVOLUTION_PERSISTENCE_APPLIED",
                            graph_id,
                            {
                                "requested_profile": requested_profile.value,
                                "requested_persist_mode": requested_persist_mode.value,
                                "effective_profile": effective_profile.value,
                                "effective_persist_mode": effective_persist_mode.value,
                                "durability_path": policy.durability_path,
                                "completion_mode": completion_mode,
                                "state_update_status": state_update_status,
                                "state_update_error": state_update_error,
                                "graph_version": result.graph_version,
                            },
                            event_repo,
                            session=session,
                        )
                        events_emitted.append("EVOLUTION_PERSISTENCE_APPLIED")
                        session.commit()
                    except Exception as e:  # nosec B110
                        session.rollback()
                        logger.warning(
                            "[Evolve] Failed to persist relaxed completion metadata graph=%s: %s",
                            graph_id,
                            e,
                        )
                        if state_update_error is None:
                            state_update_error = str(e)[:300]
                        state_update_status = "best_effort_failed_nonfatal"

                # =====================================================================
                # STEP 2b: Record learning outcome (opt-in, best effort)
                # =====================================================================
                learning_summary: Optional[Dict[str, Any]] = None
                if learning_enabled and learning_ctx is not None:
                    learning_ctx.retrieval_after = _probe_retrieval(
                        graph_id=graph_id,
                        node_repo=node_repo,
                    )
                    retrieval_delta = None
                    if (
                        learning_ctx.retrieval_before is not None
                        and learning_ctx.retrieval_after is not None
                        and learning_ctx.retrieval_before > 0.05
                    ):
                        delta = (
                            learning_ctx.retrieval_after
                            - learning_ctx.retrieval_before
                        ) / learning_ctx.retrieval_before
                        retrieval_delta = max(-1.0, min(1.0, delta))
                    learning_summary = _record_learning_outcome(
                        graph_id=graph_id,
                        tenant_id=tenant_id,
                        session=session,
                        repo=learning_ctx.repo,
                        policy=learning_ctx.policy,
                        knobs=learning_ctx.knobs,
                        before=learning_ctx.before,
                        result=result,
                        diagnostics_dict=diagnostics_dict,
                        node_repo=node_repo,
                        retrieval_delta=retrieval_delta,
                        theories=theories_created,
                    )

                # =====================================================================
                # STEP 3: Build result
                # =====================================================================
                latency_ms = int((time.time() - start_time) * 1000)

                return EvolveResult(
                    status="completed",
                    graph_version=result.graph_version,
                    merges=result.merges,
                    prunes=result.prunes,
                    inventions=result.inventions,
                    theories=theories_created,
                    diagnostics=diagnostics_dict,
                    events_emitted=events_emitted,
                    latency_ms=latency_ms,
                    requested_profile=requested_profile.value,
                    requested_persist_mode=requested_persist_mode.value,
                    effective_profile=effective_profile.value,
                    effective_persist_mode=effective_persist_mode.value,
                    durability_path=policy.durability_path,
                    evolve_aggressiveness=policy.evolve_aggressiveness,
                    completion_mode=completion_mode,
                    state_update_status=state_update_status,
                    state_update_error=state_update_error,
                    learning=learning_summary,
                    advanced_warnings=advanced_warnings,
                )

            except Exception as e:
                if session is not None:
                    try:
                        session.rollback()
                    except Exception:  # nosec B110
                        pass
                logger.error(f"[Evolve] Error: {e}")
                latency_ms = int((time.time() - start_time) * 1000)

                _emit_event(
                    "EVOLUTION_ERROR",
                    graph_id,
                    {
                        "error": str(e),
                        "requested_profile": requested_profile.value,
                        "requested_persist_mode": requested_persist_mode.value,
                        "effective_profile": effective_profile.value,
                        "effective_persist_mode": effective_persist_mode.value,
                        "durability_path": policy.durability_path,
                    },
                    event_repo,
                    session=session,
                )
                events_emitted.append("EVOLUTION_ERROR")
                if session is not None:
                    try:
                        session.commit()
                    except Exception:  # nosec B110
                        try:
                            session.rollback()
                        except Exception:  # nosec B110
                            pass

                return EvolveResult(
                    status="error",
                    graph_version=0,
                    merges=0,
                    prunes=0,
                    inventions=0,
                    diagnostics=None,
                    events_emitted=events_emitted,
                    latency_ms=latency_ms,
                    requested_profile=requested_profile.value,
                    requested_persist_mode=requested_persist_mode.value,
                    effective_profile=effective_profile.value,
                    effective_persist_mode=effective_persist_mode.value,
                    durability_path=policy.durability_path,
                    evolve_aggressiveness=policy.evolve_aggressiveness,
                    completion_mode=(
                        "sync_strict"
                        if effective_persist_mode == PersistMode.STRICT
                        else "core_sync_state_best_effort"
                    ),
                    state_update_status="error",
                    advanced_warnings=advanced_warnings,
                    error=str(e),
                )
    finally:
        if own_session:
            session.close()


# =============================================================================
# Batch Evolution
# =============================================================================


def run_evolve_batch(
    graph_id: str,
    cycles: int = 1,
    *,
    profile: Union[FAIMProfile, str] = FAIMProfile.STRICT,
    persist_mode: Union[PersistMode, str] = PersistMode.RELAXED,
    node_repo: Optional[Any] = None,
    edge_repo: Optional[Any] = None,
    event_repo: Optional[Any] = None,
    gv_repo: Optional[Any] = None,
) -> List[EvolveResult]:
    """Run multiple evolution cycles.

    Args:
        graph_id: Target graph identifier.
        cycles: Number of evolution cycles to run.
        profile: Execution profile.
        persist_mode: Durability mode.
        node_repo, edge_repo, event_repo, gv_repo: Repositories.

    Returns:
        List of EvolveResult, one per cycle.
    """
    results = []

    for i in range(cycles):
        logger.info(f"[Evolve] Cycle {i + 1}/{cycles}")
        result = run_evolve(
            graph_id=graph_id,
            profile=profile,
            persist_mode=persist_mode,
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            gv_repo=gv_repo,
        )
        results.append(result)

        if result.status == "error":
            logger.warning(f"[Evolve] Stopping after error in cycle {i + 1}")
            break

    return results


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "EvolveResult",
    "run_evolve",
    "run_evolve_batch",
]
