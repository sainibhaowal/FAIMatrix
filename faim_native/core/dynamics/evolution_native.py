"""FAIM-Native Evolution.

Deterministic evolution operations with D/H/λ diagnostics.

Actions:
- Compute diagnostics (D, H, λ, R, N, E)
- Find high-redundancy pairs via antisym score
- Adapt thresholds based on diagnostics
- Merge/cancel if above threshold
- Prune safe nodes
- Emit events for each action + DIAGNOSTICS_SNAPSHOT
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Flexible imports
try:
    from faim.Faim_Native.core.antisym import (  # noqa: I001
        merge_vectors,
        opposition_score,
        should_merge,
    )
    from faim.Faim_Native.core.metrics.fractal_physics import GOLDEN_S  # noqa: F401
    from faim.Faim_Native.core.metrics.fractal_physics import (
        DEFAULT_CONFIG,
        FractalConfig,
        FractalDiagnostics,
        compute_diagnostics,
    )
    from faim.Faim_Native.core.operators.prune import (
        PrunePolicy,
        can_prune,
        compute_similarity_matrix,
    )
    from faim.Faim_Native.store.pg.repos.edge_repo import EdgeRepo
    from faim.Faim_Native.store.pg.repos.node_repo import NodeRepo
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.antisym import merge_vectors, opposition_score, should_merge
    from core.metrics.fractal_physics import (
        DEFAULT_CONFIG,
        FractalConfig,
        FractalDiagnostics,
        compute_diagnostics,
    )
    from core.operators.prune import PrunePolicy, can_prune, compute_similarity_matrix
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.node_repo import NodeRepo


logger = logging.getLogger(__name__)


def _cosine(a, b):
    """Cosine similarity."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    import math

    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class EvolutionResult:
    """Result of evolution operation.

    Attributes:
        graph_version: Graph version after evolution.
        merges: Number of merge operations.
        prunes: Number of prune operations.
        events_emitted: Number of events emitted.
        diagnostics: FractalDiagnostics computed at start.
    """

    graph_version: int = 0
    merges: int = 0
    prunes: int = 0
    inventions: int = 0
    events_emitted: int = 0
    actions: List[Dict[str, Any]] = field(default_factory=list)
    diagnostics: Optional[FractalDiagnostics] = None
    skip_reason: Optional[str] = None


def _emit_graph_event(
    *,
    session: Any,
    event_repo: Any,
    graph_id: str,
    kind: str,
    payload: Dict[str, Any],
    result: EvolutionResult,
) -> None:
    """Emit graph event and keep EvolutionResult counters in sync."""
    if session is None:
        return
    event_repo.emit(
        session=session,
        graph_id=graph_id,
        kind=kind,
        payload=payload,
    )
    result.events_emitted += 1


def _with_event_context(
    payload: Dict[str, Any],
    event_context: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Add optional runtime policy metadata to emitted evolve events."""
    if not event_context:
        return payload
    merged = dict(payload)
    for key in (
        "requested_profile",
        "requested_persist_mode",
        "effective_profile",
        "effective_persist_mode",
        "durability_path",
        "completion_mode",
        "evolve_aggressiveness",
    ):
        value = event_context.get(key)
        if value is not None and key not in merged:
            merged[key] = value
    return merged


def _resolve_invention_settings(runtime_config: Optional[Any]) -> Dict[str, Any]:
    """Resolve self-invention settings from runtime config with safe defaults.

    This keeps evolve core free from direct environment reads while preserving
    testability when runtime config is unavailable.
    """
    defaults: Dict[str, Any] = {
        "enabled": False,
        "on_evolve": True,
        "min_coactivation_count": 3,
        "lambda_threshold": 0.3,
        "min_redundancy_reduction": 0.01,
        "max_macros_per_cycle": 3,
        "event_window": 5000,
    }

    cfg = runtime_config
    if cfg is None:
        try:
            from runtime.config import get_config

            cfg = get_config()
        except Exception:  # nosec B110 - keep core callable without runtime env
            cfg = None

    if cfg is None:
        return defaults

    return {
        "enabled": bool(getattr(cfg, "self_invent_enabled", defaults["enabled"])),
        "on_evolve": bool(getattr(cfg, "self_invent_on_evolve", defaults["on_evolve"])),
        "min_coactivation_count": int(
            getattr(
                cfg,
                "self_invent_min_coactivation_count",
                defaults["min_coactivation_count"],
            )
        ),
        "lambda_threshold": float(
            getattr(
                cfg,
                "self_invent_lambda_threshold",
                defaults["lambda_threshold"],
            )
        ),
        "min_redundancy_reduction": float(
            getattr(
                cfg,
                "self_invent_min_redundancy_reduction",
                defaults["min_redundancy_reduction"],
            )
        ),
        "max_macros_per_cycle": int(
            getattr(
                cfg,
                "self_invent_max_macros_per_cycle",
                defaults["max_macros_per_cycle"],
            )
        ),
        "event_window": int(
            getattr(
                cfg,
                "self_invent_event_window",
                defaults["event_window"],
            )
        ),
    }


def compute_graph_diagnostics(
    graph_id: str,
    nodes: List,
    edges: List,
    graph_version: int,
    config: FractalConfig = DEFAULT_CONFIG,
) -> FractalDiagnostics:
    """Compute diagnostics for a graph.

    Args:
        graph_id: Graph identifier.
        nodes: List of node models.
        edges: List of edge models.
        graph_version: Current graph version.
        config: Fractal configuration.

    Returns:
        FractalDiagnostics.
    """
    vectors = [n.v_native for n in nodes if n.v_native]

    # Extract residuals (scaled from DB storage)
    residuals = []
    for n in nodes:
        if n.residual is not None:
            residuals.append(n.residual / 1e9)
        else:
            residuals.append(0.0)

    return compute_diagnostics(
        graph_id=graph_id,
        vectors=vectors,
        residuals=residuals,
        edge_count=len(edges),
        graph_version=graph_version,
        region_id="global",
        config=config,
    )


def adapt_merge_threshold(
    base_threshold: float,
    diagnostics: FractalDiagnostics,
) -> float:
    """Adapt merge threshold based on diagnostics.

    If redundancy is high (R > 0.5), lower threshold to merge more aggressively.
    If redundancy is low (R < 0.2), raise threshold to be more conservative.

    Args:
        base_threshold: Base merge threshold.
        diagnostics: Current diagnostics.

    Returns:
        Adapted threshold in [0.8, 0.99].
    """
    R = diagnostics.redundancy_R

    if R > 0.5:
        # High redundancy - merge more (lower threshold)
        adapted = base_threshold - 0.05 * (R - 0.5) / 0.5
    elif R < 0.2:
        # Low redundancy - merge less (raise threshold)
        adapted = base_threshold + 0.02 * (0.2 - R) / 0.2
    else:
        adapted = base_threshold

    return max(0.80, min(0.99, adapted))


def adapt_prune_policy(
    base_policy: PrunePolicy,
    diagnostics: FractalDiagnostics,
) -> PrunePolicy:
    """Adapt prune policy based on diagnostics.

    If redundancy is high, prune more aggressively.
    If novelty is high, protect more nodes.

    Args:
        base_policy: Base prune policy.
        diagnostics: Current diagnostics.

    Returns:
        Adapted PrunePolicy.
    """
    R = diagnostics.redundancy_R
    N = diagnostics.novelty_N

    if R > 0.5:
        # High redundancy - prune more (lower similarity threshold)
        sim_threshold = max(0.90, base_policy.min_similarity_for_redundancy - 0.05)
    elif N > 0.5:
        # High novelty - protect (raise similarity threshold)
        sim_threshold = min(0.99, base_policy.min_similarity_for_redundancy + 0.03)
    else:
        sim_threshold = base_policy.min_similarity_for_redundancy

    return PrunePolicy(
        min_age_days=base_policy.min_age_days,
        max_touch_count=base_policy.max_touch_count,
        min_similarity_for_redundancy=sim_threshold,
        protect_macros=base_policy.protect_macros,
    )


def evolve_once(
    graph_id: str,
    node_repo: NodeRepo,
    edge_repo: EdgeRepo,
    event_repo,
    graph_version_repo,
    *,
    max_actions: int = 25,
    merge_threshold: float = 0.95,
    prune_policy: Optional[PrunePolicy] = None,
    fractal_config: FractalConfig = DEFAULT_CONFIG,
    self_invent_requested: Optional[bool] = None,
    runtime_config: Optional[Any] = None,
    invention_overrides: Optional[Dict[str, Any]] = None,
    event_context: Optional[Dict[str, Any]] = None,
) -> EvolutionResult:
    """Run one evolution cycle with D/H/λ diagnostics.

    1. Compute diagnostics (D, H, λ, R, N, E)
    2. Emit DIAGNOSTICS_SNAPSHOT event
    3. Adapt merge/prune thresholds based on diagnostics
    4. Find high-redundancy pairs
    5. Merge if above adapted threshold
    6. Prune safe nodes
    7. Emit events
    8. Bump graph version

    Args:
        graph_id: Graph identifier.
        node_repo: Node repository.
        edge_repo: Edge repository.
        event_repo: Event repository.
        graph_version_repo: Graph version repository.
        max_actions: Maximum actions per cycle.
        merge_threshold: Base threshold for merge.
        prune_policy: Base prune policy (optional).
        fractal_config: Fractal configuration.

    Returns:
        EvolutionResult summary with diagnostics.
    """
    result = EvolutionResult()
    base_prune_policy = prune_policy or PrunePolicy()
    merged_ids = set()
    action_count = 0

    # Get current graph version (may be int or GraphVersion object)
    gv = graph_version_repo.get(None, graph_id)
    if gv is None:
        current_version = 0
    elif hasattr(gv, "version"):
        current_version = gv.version
    else:
        current_version = int(gv)
    result.graph_version = current_version

    # Get all nodes and edges
    nodes = node_repo.list_nodes(graph_id, limit=1000)
    edges = edge_repo.list_all_edges(graph_id, limit=10000)

    # 1. Compute diagnostics (even for < 2 nodes)
    diagnostics = compute_graph_diagnostics(
        graph_id=graph_id,
        nodes=nodes,
        edges=edges,
        graph_version=current_version,
        config=fractal_config,
    )
    result.diagnostics = diagnostics

    # 2. Emit DIAGNOSTICS_SNAPSHOT event
    _sess = getattr(node_repo, "session", None)
    _emit_graph_event(
        session=_sess,
        event_repo=event_repo,
        graph_id=graph_id,
        kind="DIAGNOSTICS_SNAPSHOT",
        payload=diagnostics.to_event_payload(),
        result=result,
    )

    if len(nodes) < 2:
        result.skip_reason = "insufficient_nodes"
        _emit_graph_event(
            session=_sess,
            event_repo=event_repo,
            graph_id=graph_id,
            kind="EVOLUTION_SKIPPED",
            payload=_with_event_context(
                {
                    "reason": result.skip_reason,
                    "graph_version": current_version,
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "D_hat": diagnostics.D_hat,
                    "H_hat": diagnostics.H_hat,
                    "lambda_hat": diagnostics.lambda_hat,
                },
                event_context,
            ),
            result=result,
        )
        return result

    # 3. Adapt thresholds based on diagnostics
    adapted_merge_threshold = adapt_merge_threshold(merge_threshold, diagnostics)
    adapted_prune_policy = adapt_prune_policy(base_prune_policy, diagnostics)

    # Build similarity matrix
    sim_matrix = compute_similarity_matrix(nodes, _cosine)

    # 4-5. Find merge candidates and merge
    for i, node_a in enumerate(nodes):
        if action_count >= max_actions:
            break
        if node_a.node_id in merged_ids:
            continue

        for j, node_b in enumerate(nodes):
            if j <= i:
                continue
            if node_b.node_id in merged_ids:
                continue

            score = opposition_score(node_a.v_native, node_b.v_native)

            if should_merge(score, adapted_merge_threshold):
                merge_result = merge_vectors(
                    a_id=node_a.node_id,
                    b_id=node_b.node_id,
                    a_hash=node_a.vector_hash,
                    b_hash=node_b.vector_hash,
                    score=score,
                )

                merged_ids.add(merge_result.loser_id)

                # Add opposition edge
                edge_repo.add_opposition_edge(
                    graph_id=graph_id,
                    a_id=merge_result.winner_id,
                    b_id=merge_result.loser_id,
                    weight=score,
                    meta=merge_result.meta,
                )

                # Emit event
                _emit_graph_event(
                    session=_sess,
                    event_repo=event_repo,
                    graph_id=graph_id,
                    kind="EVOLUTION_MERGE",
                    payload={
                        "winner_id": str(merge_result.winner_id),
                        "loser_id": str(merge_result.loser_id),
                        "score": score,
                        "adapted_threshold": adapted_merge_threshold,
                    },
                    result=result,
                )

                result.merges += 1
                result.actions.append(
                    {
                        "type": "merge",
                        "winner": str(merge_result.winner_id),
                        "loser": str(merge_result.loser_id),
                    }
                )
                action_count += 1
                break

    # 6. Prune pass
    for node in nodes:
        if action_count >= max_actions:
            break
        if node.node_id in merged_ids:
            continue

        max_sim = sim_matrix.get(node.node_id, 0.0)

        if can_prune(node, max_sim, adapted_prune_policy):
            # Delete edges first
            edge_repo.delete_edges_for_node(graph_id, node.node_id)

            # Delete node
            node_repo.delete_node(graph_id, node.node_id)

            # Emit event
            _emit_graph_event(
                session=_sess,
                event_repo=event_repo,
                graph_id=graph_id,
                kind="PRUNE_NODE",
                payload={
                    "node_id": str(node.node_id),
                    "reason": "low_usage_high_redundancy",
                    "max_similarity": max_sim,
                    "adapted_sim_threshold": adapted_prune_policy.min_similarity_for_redundancy,
                },
                result=result,
            )

            result.prunes += 1
            result.actions.append(
                {
                    "type": "prune",
                    "node_id": str(node.node_id),
                }
            )
            action_count += 1

    # 7. Optional self-invention pass (config + orchestration controlled)
    invention_settings = _resolve_invention_settings(runtime_config)
    if invention_overrides:
        if "enabled" in invention_overrides:
            invention_settings["enabled"] = bool(invention_overrides["enabled"])
        if "on_evolve" in invention_overrides:
            invention_settings["on_evolve"] = bool(invention_overrides["on_evolve"])
        if "min_coactivation_count" in invention_overrides:
            invention_settings["min_coactivation_count"] = max(
                2, int(invention_overrides["min_coactivation_count"])
            )
        if "lambda_threshold" in invention_overrides:
            invention_settings["lambda_threshold"] = max(
                0.0, min(1.0, float(invention_overrides["lambda_threshold"]))
            )
        if "min_redundancy_reduction" in invention_overrides:
            invention_settings["min_redundancy_reduction"] = max(
                0.0, min(1.0, float(invention_overrides["min_redundancy_reduction"]))
            )
        if "max_macros_per_cycle" in invention_overrides:
            invention_settings["max_macros_per_cycle"] = max(
                0, int(invention_overrides["max_macros_per_cycle"])
            )
        if "event_window" in invention_overrides:
            invention_settings["event_window"] = max(
                100, int(invention_overrides["event_window"])
            )
    invention_allowed = bool(
        invention_settings["enabled"] and invention_settings["on_evolve"]
    )
    if self_invent_requested is not None:
        invention_allowed = invention_allowed and bool(self_invent_requested)

    if invention_allowed and _sess is not None:
        try:
            from core.dynamics.invention_native import run_invention_cycle
            from store.pg.repos.self_invention_state_repo import SelfInventionStateRepo

            invention_result = run_invention_cycle(
                graph_id=graph_id,
                session=_sess,
                node_repo=node_repo,
                edge_repo=edge_repo,
                event_repo=event_repo,
                state_repo=SelfInventionStateRepo(
                    session=_sess,
                    tenant_id=node_repo.tenant_id,
                ),
                lambda_hat=diagnostics.lambda_hat,
                min_coactivation_count=invention_settings["min_coactivation_count"],
                lambda_threshold=invention_settings["lambda_threshold"],
                min_redundancy_reduction=invention_settings["min_redundancy_reduction"],
                max_macros_per_cycle=invention_settings["max_macros_per_cycle"],
                event_window=invention_settings["event_window"],
            )
            result.inventions = invention_result.macros_created
            if invention_result.macros_created > 0:
                action_count += invention_result.macros_created
                result.actions.append(
                    {
                        "type": "invention",
                        "count": invention_result.macros_created,
                        "macro_ids": [str(mid) for mid in invention_result.macro_ids],
                    }
                )
                _emit_graph_event(
                    session=_sess,
                    event_repo=event_repo,
                    graph_id=graph_id,
                    kind="EVOLUTION_INVENTION_SUMMARY",
                    payload={
                        "inventions": invention_result.macros_created,
                        "signatures_tracked": invention_result.signatures_tracked,
                        "processed_events": invention_result.processed_events,
                        "last_event_seq": invention_result.last_event_seq,
                    },
                    result=result,
                )
            result.events_emitted += invention_result.events_emitted
        except Exception as exc:
            logger.warning("Self-invention pass failed: %s", exc)
            _emit_graph_event(
                session=_sess,
                event_repo=event_repo,
                graph_id=graph_id,
                kind="EVOLUTION_INVENTION_ERROR",
                payload={"error": str(exc)[:300]},
                result=result,
            )

    # 8. Bump graph version if any actions
    if action_count > 0:
        new_version = graph_version_repo.bump(
            _sess,
            graph_id=graph_id,
            reason=(
                "evolution: "
                f"{result.merges} merges, {result.prunes} prunes, "
                f"{result.inventions} inventions"
            ),
        )

        _emit_graph_event(
            session=_sess,
            event_repo=event_repo,
            graph_id=graph_id,
            kind="EVOLUTION_COMPLETE",
            payload=_with_event_context(
                {
                    "version": new_version,
                    "merges": result.merges,
                    "prunes": result.prunes,
                    "inventions": result.inventions,
                    "D_hat": diagnostics.D_hat,
                    "H_hat": diagnostics.H_hat,
                    "lambda_hat": diagnostics.lambda_hat,
                    "diagnostics_hash": diagnostics.diagnostics_hash,
                },
                event_context,
            ),
            result=result,
        )
        result.graph_version = new_version
    else:
        result.skip_reason = "no_actions_after_evaluation"
        _emit_graph_event(
            session=_sess,
            event_repo=event_repo,
            graph_id=graph_id,
            kind="EVOLUTION_SKIPPED",
            payload=_with_event_context(
                {
                    "reason": result.skip_reason,
                    "graph_version": current_version,
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "merge_threshold": adapted_merge_threshold,
                    "prune_similarity_threshold": adapted_prune_policy.min_similarity_for_redundancy,
                    "invention_allowed": invention_allowed,
                    "D_hat": diagnostics.D_hat,
                    "H_hat": diagnostics.H_hat,
                    "lambda_hat": diagnostics.lambda_hat,
                },
                event_context,
            ),
            result=result,
        )

    return result


# Exports
__all__ = [
    "EvolutionResult",
    "evolve_once",
    "compute_graph_diagnostics",
    "adapt_merge_threshold",
    "adapt_prune_policy",
]
