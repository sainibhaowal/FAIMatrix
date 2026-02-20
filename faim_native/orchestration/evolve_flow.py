"""FAIM-Native Orchestration: Evolve Flow.

Pure wiring layer for evolution operations.

Calls core.dynamics.evolution_native.evolve_once() and returns
MetricsSnapshot in Stage-4.1.1 contract format.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from .ingest_flow import FAIMProfile, PersistMode
from .profile_persist_policy import PolicyOperation, resolve_profile_persist_policy

logger = logging.getLogger(__name__)


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
    requested_profile: str = "strict"
    requested_persist_mode: str = "relaxed"
    effective_profile: str = "strict"
    effective_persist_mode: str = "relaxed"
    durability_path: str = "core_sync_secondary_async"
    evolve_aggressiveness: str = "conservative"
    completion_mode: str = "core_sync_state_best_effort"
    state_update_status: str = "not_required"
    state_update_error: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for API response."""
        return {
            "status": self.status,
            "graph_version": self.graph_version,
            "merges": self.merges,
            "prunes": self.prunes,
            "inventions": self.inventions,
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
                max_actions = _resolve_max_actions(
                    runtime_cfg=runtime_cfg,
                    flags=flags,
                    budget_scale=policy.evolve_action_budget_scale,
                )
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

                result = evolve_once(
                    graph_id=graph_id,
                    node_repo=node_repo,
                    edge_repo=edge_repo,
                    event_repo=event_repo,
                    graph_version_repo=gv_repo,
                    max_actions=max_actions,
                    merge_threshold=policy.evolve_merge_threshold,
                    prune_policy=prune_policy,
                    self_invent_requested=resolved_self_invent_requested,
                    runtime_config=runtime_cfg,
                    invention_overrides=invention_overrides,
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
                        logger.warning(f"Failed to convert diagnostics: {e}")

                completion_mode = (
                    "sync_strict"
                    if effective_persist_mode == PersistMode.STRICT
                    else "core_sync_state_best_effort"
                )
                state_update_status = "not_required"
                state_update_error: Optional[str] = None

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
                # STEP 3: Build result
                # =====================================================================
                latency_ms = int((time.time() - start_time) * 1000)

                return EvolveResult(
                    status="completed",
                    graph_version=result.graph_version,
                    merges=result.merges,
                    prunes=result.prunes,
                    inventions=result.inventions,
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
