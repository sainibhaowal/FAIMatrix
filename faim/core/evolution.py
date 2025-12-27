from __future__ import annotations

# ============================================================================
#  FAIM Evolution Engine (Golden Edition)
# ============================================================================
#  Module
#  -------
#      faim.core.evolution
#
#  Purpose
#  -------
#      This module implements FAIM's evolution layer over the Fractal
#      Inheritance Graph (FIG), combining:
#
#        • P1 / P1.5 Objective Signatures
#            - D(M_n, Q): retrieval / divergence metric.
#            - H(M_n): fractal entropy proxy over a region.
#            - λ: trade-off parameter.
#            - J(M_n) = D + λ·H.
#
#        • P3 Graph-Level Evolution (FAIMStore-backed)
#            - Region discovery over a FIG (Region).
#            - Redundancy / objective proxies per region.
#            - Local rules: merge / prune / promote (heuristic evolution).
#            - One-shot evolution: evolve_graph_once(...)
#            - Background scheduler: EvolutionScheduler.
#
#        • P3 Region-Level Evolution (Adapter-based)
#            - QueryStats & RegionStats snapshots.
#            - EvolutionAdapter protocol (no direct FAIMStore dependency).
#            - evolve_region(...) using J(D, H, λ) with D, H stable formulas.
#
#  Design Goals
#  ------------
#      - Deterministic: same input state + config ⇒ same actions.
#      - Side-effect-controlled: all mutations go through FAIMStore or
#        EvolutionAdapter primitives (merge_nodes, prune_node, promote_node).
#      - Metrics-friendly: explicit EvolutionStats / EvolutionStepResult.
#      - Phase-clean: respects P1 / P1.5 / P2 invariants; P3 adds behaviour
#        without breaking earlier phases.
#
#  Layers
#  ------
#      Layer A (P1 Objective API)
#          DEFAULT_LAMBDA, EvolutionTerms, estimate_divergence(...),
#          estimate_fractal_entropy(...), region_objective(...),
#          compute_evolution_terms(...).
#
#      Layer B (P3 Graph-Level Evolution; FAIMStore-backed)
#          EvolutionConfig, Region, RegionObjective, EvolutionStats,
#          discover_regions, compute_region_objective, compute_region_redundancy,
#          _prune_cold_leaves, _merge_redundant_siblings, _promote_hubs,
#          evolve_graph_once, EvolutionScheduler.
#
#      Layer C (P3 Region-Level Evolution; Adapter-based)
#          QueryStats, RegionStats, RegionEvolutionConfig, EvolutionAction,
#          EvolutionStepResult, EvolutionAdapter, evolve_region(...).
#
#  Golden Edition Constraints
#  --------------------------
#      - No hidden globals or magic: all thresholds live in config classes.
#      - No FastAPI / DB / UI imports here – pure engine + interfaces only.
#      - Deterministic ordering of regions and merges.
#      - Background evolution is opt-in via EvolutionScheduler, never implicit.
# ============================================================================
import logging
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Protocol, Set, Tuple

import numpy as np

from faim.core.antisym import merge_records
from faim.core.math import l2_norm
from faim.core.types import GraphId, NodeId, NodeRecord, ParentRef, Vector
from faim.storage.store import FAIMStore

logger = logging.getLogger(__name__)


# ============================================================================
#  Layer A – P1 Objective Signatures: D, H, λ, J
# ============================================================================

DEFAULT_LAMBDA: float = 0.5


@dataclass(frozen=True)
class EvolutionTerms:
    """
    Container for analytic evolution objective terms.

    Attributes
    ----------
    D:
        Divergence term D(M_n, Q) between regional memory M_n and query
        distribution Q (e.g., retrieval error / KL divergence).
    H:
        Fractal entropy H(M_n), penalising over-collapsed or over-
        fragmented structure.
    lam:
        Trade-off parameter λ, analogous to an inverse temperature.
    J:
        Combined objective J = D + λ·H.
    """

    D: float
    H: float
    lam: float
    J: float


def region_objective(D: float, H: float, lam: float) -> float:
    """
    Combined evolution objective:

        J = D + λ·H

    This is the scalar we try to push down (or at least keep stable) over
    time by merge / prune / promote operations.
    """
    return float(D + lam * H)


# NOTE:
#   The public P1 functions below accept `Any` so that earlier phases
#   (tests, stubs) remain valid. Under the hood, once P3 types are in
#   play, they delegate to the concrete implementations that operate on
#   QueryStats and RegionStats (defined later in this file).


def estimate_divergence(region_stats: Any, query_stats: Any) -> float:
    """
    Estimate divergence D(M_n, Q) between region M_n and query distribution Q.

    Behaviour
    ---------
    - If `query_stats` is a QueryStats instance (P3), compute a numerically
      stable retrieval-error proxy:

          total = hits + misses
          p_err = misses / total
          D    = -log(1 - p_err + ε)

      D ≈ 0 means near-perfect recall; larger D means worse performance.

    - Otherwise (no stats available yet), returns 0.0 as a neutral value.
    """
    # NOTE: region_stats is currently unused here but kept for signature
    #       compatibility with the original P1 design.
    _ = region_stats

    # Importing the class here avoids circular import concerns if this file
    # is refactored later.
    try:
        from faim.core.evolution import QueryStats  # type: ignore  # pragma: no cover
    except Exception:  # pragma: no cover
        QueryStats = None  # type: ignore

    if QueryStats is not None and isinstance(query_stats, QueryStats):
        return _estimate_divergence_from_query_stats(query_stats)

    # No information available: treat as neutral.
    return 0.0


def estimate_fractal_entropy(region_stats: Any) -> float:
    """
    Estimate fractal entropy H(M_n) of a region.

    Behaviour
    ---------
    - If `region_stats` is a RegionStats instance (P3), compute:

          H = H_usage + R_penalty

      where
          H_usage = normalized Shannon entropy of usage weights,
          R_penalty ≈ redundancy_index (∈ [0, 1] ideally).

      This penalises both over-concentration (single hub) and
      over-fragmentation / redundancy.

    - Otherwise, returns 0.0 as a neutral value.
    """
    try:
        from faim.core.evolution import RegionStats  # type: ignore  # pragma: no cover
    except Exception:  # pragma: no cover
        RegionStats = None  # type: ignore

    if RegionStats is not None and isinstance(region_stats, RegionStats):
        return _estimate_fractal_entropy_from_region_stats(region_stats)

    return 0.0


def compute_evolution_terms(
    region_stats: Any,
    query_stats: Any,
    *,
    lam: float = DEFAULT_LAMBDA,
) -> EvolutionTerms:
    """
    Convenience helper to compute all D/H/λ/J terms in one shot.

    This function is intentionally decoupled from the concrete region
    metrics used below so tests and future metrics modules can evolve
    independently.
    """
    D = estimate_divergence(region_stats, query_stats)
    H = estimate_fractal_entropy(region_stats)
    J = region_objective(D, H, lam)
    return EvolutionTerms(D=D, H=H, lam=float(lam), J=J)


# ============================================================================
#  Layer B – Graph-Level Evolution (FAIMStore-Backed)
# ============================================================================


@dataclass(frozen=True)
class EvolutionConfig:
    """
    Tunable thresholds and knobs for FAIM evolution at graph level.

    Attributes
    ----------
    lambda_h:
        Weight for entropy term in region objective: J = D + lambda_h * H.
        This is a concrete analogue of λ for the local region proxy used
        in graph-level evolution.

    max_region_size:
        Soft cap on region size for objective calculations. Large regions
        are heuristically split during discovery.

    merge_similarity_threshold:
        Cosine similarity threshold above which two siblings are considered
        redundant and eligible for merge.

    redundancy_similarity_threshold:
        Similarity threshold used when computing redundancy R.

    prune_min_use_count:
        Nodes with use_count strictly below this and no children are
        considered cold leaves and eligible for pruning.

    promote_min_use_count:
        Nodes with use_count at or above this and multiple parents are
        considered hubs and eligible for promotion / rebalancing.
    """

    lambda_h: float = 0.1
    max_region_size: int = 512
    merge_similarity_threshold: float = 0.98
    redundancy_similarity_threshold: float = 0.98
    prune_min_use_count: int = 1
    promote_min_use_count: int = 8


@dataclass(frozen=True)
class Region:
    """
    A connected region / cluster of nodes in a single graph.

    Regions are the unit of graph-level evolution: objectives and local
    rules operate on Region instances, not on the whole graph at once.
    """

    graph_id: GraphId
    region_id: str
    node_ids: Tuple[NodeId, ...]


@dataclass(frozen=True)
class RegionObjective:
    """
    Estimated objective for a graph-level region: D, H, and J = D + λH.

    Note
    ----
    This uses the *concrete* region proxy:
        - D: centroid discrepancy,
        - H: Shannon entropy over usage weights,
    not the abstract P1 signatures (those are Layer A above).
    """

    D: float
    H: float
    J: float


@dataclass(frozen=True)
class EvolutionStats:
    """
    Summary statistics for one evolve_graph_once() pass over a graph.

    Attributes
    ----------
    graph_id:
        Graph on which evolution was run.

    regions:
        Number of regions discovered.

    merges:
        Number of merge operations performed.

    prunes:
        Number of pruned nodes.

    promotions:
        Number of hub-promotions / parent rebalance operations.

    redundancy_before / redundancy_after:
        Mean redundancy index R across regions, before and after.

    objective_before / objective_after:
        Mean region objective J across regions, before and after.
    """

    graph_id: GraphId
    regions: int
    merges: int
    prunes: int
    promotions: int
    redundancy_before: float
    redundancy_after: float
    objective_before: float
    objective_after: float


# ---------------------------------------------------------------------------
# Graph-Level Utility Helpers
# ---------------------------------------------------------------------------


def _cosine(a: Vector, b: Vector) -> float:
    """
    Numerically safe cosine similarity between two vectors.

    Returns 0.0 if either vector is effectively zero-norm.
    """
    na = l2_norm(a)
    nb = l2_norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _safe_log(x: float) -> float:
    """
    Log with a hard lower bound to avoid log(0) and NaNs.
    """
    return math.log(max(x, 1e-12))


# ---------------------------------------------------------------------------
# Region discovery (graph-level)
# ---------------------------------------------------------------------------


def discover_regions(
    store: FAIMStore,
    graph_id: GraphId,
    *,
    config: Optional[EvolutionConfig] = None,
) -> List[Region]:
    """
    Discover evolution regions for a given graph.

    Strategy (P3 baseline)
    ----------------------
    - Group nodes by their primary parent (parents[0].parent_id).
    - Nodes without parents are grouped into a synthetic ROOT region.
    - Extremely large regions are heuristically split into size-capped
      blocks of at most `max_region_size`.

    This is intentionally simple and deterministic; more advanced
    community detection can be layered on top later without
    breaking callers.
    """
    cfg = config or EvolutionConfig()

    # Map region key -> list of NodeIds
    regions: Dict[str, List[NodeId]] = {}

    for node in store.iter_nodes(graph_id):
        # Skip logically pruned/deleted nodes (flag bit 0).
        if node.flags & 0b1:
            continue
        primary_parent: Optional[NodeId] = node.parents[0].parent_id if node.parents else None
        key = primary_parent or f"{graph_id}:ROOT"
        regions.setdefault(str(key), []).append(node.id)

    result: List[Region] = []
    for key, node_ids in sorted(regions.items(), key=lambda kv: kv[0]):
        # Heuristic split for very large regions: chunk into blocks.
        if len(node_ids) > cfg.max_region_size:
            for chunk_idx in range(0, len(node_ids), cfg.max_region_size):
                chunk = node_ids[chunk_idx : chunk_idx + cfg.max_region_size]
                region_id = f"{key}#{chunk_idx // cfg.max_region_size}"
                result.append(
                    Region(
                        graph_id=graph_id,
                        region_id=region_id,
                        node_ids=tuple(chunk),
                    )
                )
        else:
            region_id = f"{key}#0"
            result.append(Region(graph_id=graph_id, region_id=region_id, node_ids=tuple(node_ids)))
    return result


# ---------------------------------------------------------------------------
# Region objectives (graph-level): D, H, J, Redundancy R
# ---------------------------------------------------------------------------


def compute_region_objective(
    store: FAIMStore,
    region: Region,
    *,
    config: Optional[EvolutionConfig] = None,
) -> RegionObjective:
    """
    Estimate D (discrepancy) and H (entropy) for a region.

    D (proxy)
    ---------
    Weighted mean-squared distance of node vectors from the usage-weighted
    centroid. In the production doc this approximates retrieval discrepancy
    vs. the query distribution.

    H (proxy)
    ---------
    Shannon entropy of the (normalized) usage weights over nodes in the
    region. This acts as a proxy for fractal entropy: it penalises both
    over-concentration (one giant hub) and over-fragmentation.

    J
    -
    Combined objective:

        J = D + λ H

    where λ is taken from EvolutionConfig.lambda_h.
    """
    cfg = config or EvolutionConfig()

    # Collect vectors and weights for all nodes in the region.
    vecs: List[Vector] = []
    weights: List[float] = []

    for node_id in region.node_ids:
        node = store.get_node(region.graph_id, node_id)
        if node is None or (node.flags & 0b1):
            continue
        vecs.append(node.vec)
        # use_count defaults to 1 if zero, to avoid degenerate weights
        w = float(node.use_count if node.use_count > 0 else 1.0)
        weights.append(w)

    if not vecs:
        return RegionObjective(D=0.0, H=0.0, J=0.0)

    w_arr = np.asarray(weights, dtype=np.float64)
    V = np.stack(vecs, axis=0).astype(np.float64)

    # Normalize weights
    w_sum = float(w_arr.sum())
    if w_sum <= 0.0:
        w_arr[:] = 1.0
        w_sum = float(w_arr.sum())
    p = w_arr / w_sum

    # Weighted centroid
    centroid = (p[:, None] * V).sum(axis=0)

    # D: weighted mean-squared distance to centroid
    diffs = V - centroid[None, :]
    sq_norms = np.sum(diffs * diffs, axis=1)
    D = float((p * sq_norms).sum())

    # H: Shannon entropy of p
    H = -float(sum(float(pi) * _safe_log(float(pi)) for pi in p))

    J = D + cfg.lambda_h * H
    return RegionObjective(D=D, H=H, J=J)


def compute_region_redundancy(
    store: FAIMStore,
    region: Region,
    *,
    config: Optional[EvolutionConfig] = None,
) -> float:
    """
    Compute a simple redundancy index R for a region.

    Definition (baseline)
    ---------------------
    R is defined as the fraction of node pairs whose cosine similarity
    exceeds `redundancy_similarity_threshold`. Values lie in [0, 1].

    This is a pragmatic proxy for "how many near-duplicates still survive"
    in the region.
    """
    cfg = config or EvolutionConfig()

    nodes: List[NodeRecord] = []
    for node_id in region.node_ids:
        node = store.get_node(region.graph_id, node_id)
        if node is None or (node.flags & 0b1):
            continue
        nodes.append(node)

    n = len(nodes)
    if n < 2:
        return 0.0

    similar_pairs = 0
    total_pairs = 0

    for i in range(n):
        for j in range(i + 1, n):
            total_pairs += 1
            sim = _cosine(nodes[i].vec, nodes[j].vec)
            if sim >= cfg.redundancy_similarity_threshold:
                similar_pairs += 1

    if total_pairs == 0:
        return 0.0
    return float(similar_pairs) / float(total_pairs)


# ---------------------------------------------------------------------------
# Local evolution rules (graph-level): prune / merge / promote
# ---------------------------------------------------------------------------


def _prune_cold_leaves(
    store: FAIMStore,
    region: Region,
    *,
    config: EvolutionConfig,
) -> int:
    """
    Prune cold leaf nodes: low use_count and no children.

    Behaviour
    ---------
    - Only leaf nodes (no children) are considered.
    - Nodes with use_count < prune_min_use_count are logically deleted by
      setting the lowest flag bit.
    - Parents are rewired to drop references to the pruned node.
    """
    pruned = 0
    for node_id in region.node_ids:
        node = store.get_node(region.graph_id, node_id)
        if node is None:
            continue
        if node.children:
            continue
        if node.use_count >= config.prune_min_use_count:
            continue

        # Detach from parents
        for pref in node.parents:
            parent = store.get_node(region.graph_id, pref.parent_id)
            if parent is None:
                continue
            new_children = [cid for cid in parent.children if cid != node.id]
            if len(new_children) != len(parent.children):
                parent = NodeRecord(
                    id=parent.id,
                    graph_id=parent.graph_id,
                    vec=parent.vec,
                    parents=parent.parents,
                    children=new_children,
                    payload_ref=parent.payload_ref,
                    created_at=parent.created_at,
                    last_used_at=parent.last_used_at,
                    use_count=parent.use_count,
                    merged_count=parent.merged_count,
                    flags=parent.flags,
                )
                store.upsert_node(parent)

        # Logical delete: set a "pruned" flag bit (LSB)
        if (node.flags & 0b1) == 0:
            node = NodeRecord(
                id=node.id,
                graph_id=node.graph_id,
                vec=node.vec,
                parents=node.parents,
                children=node.children,
                payload_ref=node.payload_ref,
                created_at=node.created_at,
                last_used_at=node.last_used_at,
                use_count=node.use_count,
                merged_count=node.merged_count,
                flags=node.flags | 0b1,
            )
            store.upsert_node(node)
            pruned += 1

    return pruned


def _merge_redundant_siblings(
    store: FAIMStore,
    region: Region,
    *,
    config: EvolutionConfig,
) -> int:
    """
    Merge highly similar siblings under the same parent.

    Strategy
    --------
    - For each parent, consider its children within the region.
    - Merge pairs whose cosine similarity exceeds merge_similarity_threshold.
    - Choose the representative based on use_count, then id.
    - Use antisymmetric `merge_records` to combine node vectors and counters.
    """
    merges = 0

    # Build parent -> list of child NodeRecords for this region.
    parent_to_children: Dict[NodeId, List[NodeRecord]] = {}

    for node_id in region.node_ids:
        node = store.get_node(region.graph_id, node_id)
        if node is None or (node.flags & 0b1):
            continue
        for pref in node.parents:
            parent_to_children.setdefault(pref.parent_id, []).append(node)

    for _parent_id, children in parent_to_children.items():
        # Work on a local mutable list but keep deterministic ordering.
        remaining: List[NodeRecord] = sorted(children, key=lambda n: str(n.id))
        changed = True

        while changed and len(remaining) > 1:
            changed = False
            new_remaining: List[NodeRecord] = []
            used: Set[NodeId] = set()

            for i, ni in enumerate(remaining):
                if ni.id in used:
                    continue
                best_j: Optional[int] = None
                best_sim = 0.0

                for j in range(i + 1, len(remaining)):
                    nj = remaining[j]
                    if nj.id in used:
                        continue
                    sim = _cosine(ni.vec, nj.vec)
                    if sim >= config.merge_similarity_threshold and sim > best_sim:
                        best_sim = sim
                        best_j = j

                if best_j is None:
                    new_remaining.append(ni)
                    continue

                nj = remaining[best_j]
                used.add(ni.id)
                used.add(nj.id)

                # Choose representative: older or higher use_count
                if ni.use_count > nj.use_count:
                    keep, drop = ni, nj
                elif nj.use_count > ni.use_count:
                    keep, drop = nj, ni
                else:
                    # Tie-breaker: lower id string wins
                    keep, drop = (ni, nj) if str(ni.id) <= str(nj.id) else (nj, ni)

                merged = merge_records(keep, drop)
                store.upsert_node(merged)

                # Mark drop as pruned/deleted
                drop = NodeRecord(
                    id=drop.id,
                    graph_id=drop.graph_id,
                    vec=drop.vec,
                    parents=drop.parents,
                    children=drop.children,
                    payload_ref=drop.payload_ref,
                    created_at=drop.created_at,
                    last_used_at=drop.last_used_at,
                    use_count=drop.use_count,
                    merged_count=drop.merged_count + 1,
                    flags=drop.flags | 0b1,
                )
                store.upsert_node(drop)
                merges += 1
                changed = True

            # Rebuild remaining set for another pass if needed
            remaining = [n for n in remaining if n.id not in used] + new_remaining

    return merges


def _promote_hubs(
    store: FAIMStore,
    region: Region,
    *,
    config: EvolutionConfig,
) -> int:
    """
    Promote hubs by rebalancing parent fractions towards frequently used parents.

    Intuition
    ---------
    This approximates "promoting heavy-hit parents upwards" from the FAIM
    spec: children with high use_count are nudged to lean more heavily on
    parents that themselves see more traffic.
    """
    promotions = 0

    for node_id in region.node_ids:
        node = store.get_node(region.graph_id, node_id)
        if node is None or not node.parents or (node.flags & 0b1):
            continue
        if node.use_count < config.promote_min_use_count:
            continue

        # Compute simple scores for parents based on their own use_count.
        parents: List[ParentRef] = list(node.parents)
        parent_nodes: List[NodeRecord] = []
        scores: List[float] = []

        for pref in parents:
            pnode = store.get_node(region.graph_id, pref.parent_id)
            if pnode is None:
                continue
            parent_nodes.append(pnode)
            scores.append(float(pnode.use_count if pnode.use_count > 0 else 1.0))

        if len(parent_nodes) < 2:
            # Nothing to rebalance if only one parent.
            continue

        score_sum = sum(scores)
        if score_sum <= 0.0:
            continue

        new_parents: List[ParentRef] = []
        for pref, score in zip(parents, scores, strict=False):
            frac = max(0.01, min(0.95, score / score_sum))
            new_parents.append(ParentRef(parent_id=pref.parent_id, fraction=frac))

        # Renormalise fractions to sum to 1.0 exactly.
        total = sum(p.fraction for p in new_parents)
        if total <= 0.0:
            continue
        norm_parents = [
            ParentRef(parent_id=p.parent_id, fraction=p.fraction / total) for p in new_parents
        ]

        node = NodeRecord(
            id=node.id,
            graph_id=node.graph_id,
            vec=node.vec,
            parents=norm_parents,
            children=node.children,
            payload_ref=node.payload_ref,
            created_at=node.created_at,
            last_used_at=node.last_used_at,
            use_count=node.use_count,
            merged_count=node.merged_count,
            flags=node.flags,
        )
        store.upsert_node(node)
        promotions += 1

    return promotions


# ---------------------------------------------------------------------------
# One-shot evolution over a graph
# ---------------------------------------------------------------------------


def evolve_graph_once(
    store: FAIMStore,
    graph_id: GraphId,
    *,
    config: Optional[EvolutionConfig] = None,
) -> EvolutionStats:
    """
    Run a single discrete evolution step over all regions in a graph.

    Behaviour
    ---------
    - Discovers regions.
    - Computes redundancy R and objective J per region (before).
    - Applies local evolution rules: prune, merge, promote.
    - Recomputes R and J per region (after).
    - Aggregates statistics to EvolutionStats.

    This function is deterministic given the same store state and config
    and is safe to call repeatedly. For a stable workload, redundancy R
    and J should be non-increasing on average.
    """
    cfg = config or EvolutionConfig()

    regions = discover_regions(store, graph_id, config=cfg)
    if not regions:
        return EvolutionStats(
            graph_id=graph_id,
            regions=0,
            merges=0,
            prunes=0,
            promotions=0,
            redundancy_before=0.0,
            redundancy_after=0.0,
            objective_before=0.0,
            objective_after=0.0,
        )

    redundancies_before: List[float] = []
    redundancies_after: List[float] = []
    objectives_before: List[float] = []
    objectives_after: List[float] = []

    total_merges = 0
    total_prunes = 0
    total_promotions = 0

    for region in regions:
        R_before = compute_region_redundancy(store, region, config=cfg)
        obj_before = compute_region_objective(store, region, config=cfg)

        pruned = _prune_cold_leaves(store, region, config=cfg)
        merges = _merge_redundant_siblings(store, region, config=cfg)
        promotions = _promote_hubs(store, region, config=cfg)

        R_after = compute_region_redundancy(store, region, config=cfg)
        obj_after = compute_region_objective(store, region, config=cfg)

        redundancies_before.append(R_before)
        redundancies_after.append(R_after)
        objectives_before.append(obj_before.J)
        objectives_after.append(obj_after.J)

        total_merges += merges
        total_prunes += pruned
        total_promotions += promotions

    # Aggregate metrics (simple means for now).
    redundancy_before = float(np.mean(redundancies_before)) if redundancies_before else 0.0
    redundancy_after = float(np.mean(redundancies_after)) if redundancies_after else 0.0
    objective_before = float(np.mean(objectives_before)) if objectives_before else 0.0
    objective_after = float(np.mean(objectives_after)) if objectives_after else 0.0

    return EvolutionStats(
        graph_id=graph_id,
        regions=len(regions),
        merges=total_merges,
        prunes=total_prunes,
        promotions=total_promotions,
        redundancy_before=redundancy_before,
        redundancy_after=redundancy_after,
        objective_before=objective_before,
        objective_after=objective_after,
    )


# ---------------------------------------------------------------------------
# Scheduler / background worker
# ---------------------------------------------------------------------------


class EvolutionScheduler:
    """
    Minimal background scheduler for periodic evolution.

    The scheduler is intentionally lightweight and does not auto-start.
    Higher-level runtimes (FastAPI, systemd services) are responsible
    for controlling its lifecycle.

    Usage
    -----
    - For tests / scripts: call `run_once(graph_id)` directly.
    - For background operation:

          scheduler = EvolutionScheduler(store)
          t = scheduler.start_in_background(graph_id, interval_seconds=60.0)
          ...
          scheduler.stop()
          t.join()
    """

    def __init__(
        self,
        store: FAIMStore,
        *,
        config: Optional[EvolutionConfig] = None,
    ) -> None:
        self._store = store
        self._config = config or EvolutionConfig()
        self._stop = threading.Event()

    @property
    def config(self) -> EvolutionConfig:
        """Return the active evolution configuration."""
        return self._config

    def run_once(self, graph_id: GraphId) -> EvolutionStats:
        """Run a single evolution pass synchronously."""
        return evolve_graph_once(self._store, graph_id, config=self._config)

    def run_forever(self, graph_id: GraphId, interval_seconds: float = 60.0) -> None:
        """
        Run evolution in a blocking loop until `stop()` is called.

        Intended for dedicated worker processes or dev setups where a
        single background loop is sufficient.
        """
        # Perform an immediate pass, then sleep between subsequent passes.
        self.run_once(graph_id)
        while not self._stop.wait(interval_seconds):
            self.run_once(graph_id)

    def start_in_background(
        self,
        graph_id: GraphId,
        interval_seconds: float = 60.0,
    ) -> threading.Thread:
        """
        Spawn a daemon thread running `run_forever`.

        This helper is mainly intended for demos and local experiments.
        Production deployments should prefer a dedicated worker process
        or service unit.
        """
        thread = threading.Thread(
            target=self.run_forever,
            args=(graph_id, interval_seconds),
            daemon=True,
        )
        thread.start()
        return thread

    def stop(self) -> None:
        """Signal the background loop (if any) to stop."""
        self._stop.set()


# ============================================================================
#  Layer C – Region-Level Evolution (Adapter-Based, P3)
# ============================================================================


@dataclass(frozen=True)
class QueryStats:
    """
    Aggregate query statistics for a region.

    This is intentionally simple: you can build richer stats on top later.

    Attributes
    ----------
    hits:
        Number of successful retrievals where this region contributed to the
        final answer (e.g. at least one node from the region was in the
        winning context bundle).

    misses:
        Number of retrievals targeting this region that failed to produce
        correct answers (e.g. QA eval miss or "no relevant node" outcome).

    per_node_hits:
        Optional map from node_id to local hit counts. Used as a proxy for
        "importance" when choosing promote / prune candidates.
    """

    hits: int = 0
    misses: int = 0
    per_node_hits: Mapping[str, int] = field(default_factory=dict)


@dataclass
class RegionStats:
    """
    Snapshot of region state needed for evolution and metrics.

    The adapter is responsible for populating this from storage and indices.

    Attributes
    ----------
    graph_id:
        Graph this region belongs to.

    region_id:
        Logical region identifier (cluster id, shard, community label, etc.).

    node_ids:
        Node ids currently belonging to the region.

    vectors:
        2D array of shape (N, d) with node vectors aligned to node_ids.

    usage_counts:
        How often each node was used for retrieval (same order as node_ids).

    merged_counts:
        How many times each node was the "sink" of a merge (same order).

    created_ats:
        Creation timestamps per node (epoch seconds); used as a tiebreaker.

    redundancy_index:
        Precomputed redundancy proxy (average similarity in the region).
        Can be recomputed here if adapter prefers, but exposing it is handy
        for tests / metrics.
    """

    graph_id: str
    region_id: str
    node_ids: List[str]
    vectors: np.ndarray
    usage_counts: np.ndarray
    merged_counts: np.ndarray
    created_ats: np.ndarray
    redundancy_index: float


@dataclass
class RegionEvolutionConfig:
    """
    Configuration for evolution decisions in a single region (adapter layer).

    All thresholds are deliberately conservative; they can be tuned via .env
    / config files without touching the algorithm.

    Attributes
    ----------
    lambda_entropy:
        λ in J = D + λ·H, trade-off between divergence vs. entropy.

    max_region_size:
        Hard cap on number of nodes considered in one evolution step.
        Large regions should be pre-clustered by the adapter.

    target_redundancy:
        Desired upper bound for redundancy_index. If redundancy is already
        below this level, merging will be more conservative.

    merge_similarity_threshold:
        Cosine similarity threshold above which two nodes are considered
        near-duplicates and eligible for merge.

    max_merges_per_step:
        Max number of merge operations in a single evolution pass.

    prune_usage_threshold:
        Nodes with usage below this AND low hits are candidates for pruning.

    max_prunes_per_step:
        Max number of prunes in a single evolution pass.

    promote_top_k:
        Number of high-usage nodes to "promote" (e.g., adjusting parent
        structure, marking as hubs) per evolution step.

    accept_worse_objective_tolerance:
        Small epsilon allowing J_after to be slightly higher than J_before
        without rollback, to avoid thrashing on noisy metrics.

    enable_logging:
        If True, emit detailed DEBUG logs about evolution actions.
    """

    lambda_entropy: float = 0.5
    max_region_size: int = 256
    target_redundancy: float = 0.25
    merge_similarity_threshold: float = 0.92
    max_merges_per_step: int = 8
    prune_usage_threshold: int = 0
    max_prunes_per_step: int = 8
    promote_top_k: int = 4
    accept_worse_objective_tolerance: float = 1e-3
    enable_logging: bool = True


@dataclass
class EvolutionAction:
    """
    Single evolution operation applied to the region.

    kind:
        'merge', 'prune', or 'promote'.

    details:
        Human-readable short description. Intended for logs / UI.
    """

    kind: str
    details: str


@dataclass
class EvolutionStepResult:
    """
    Full record of a single evolve_region() pass.

    Attributes
    ----------
    graph_id:
        Graph id.

    region_id:
        Region id.

    D_before, H_before, J_before:
        Objective components before evolution.

    D_after, H_after, J_after:
        Objective components after evolution.

    accepted:
        Whether the changes were accepted. (If you later add transactional
        rollback, you can use this flag.)

    actions:
        List of concrete evolution actions performed.

    duration_s:
        Wall-clock duration of the evolution pass (seconds).
    """

    graph_id: str
    region_id: str
    D_before: float
    H_before: float
    J_before: float
    D_after: float
    H_after: float
    J_after: float
    accepted: bool
    actions: List[EvolutionAction]
    duration_s: float


class EvolutionAdapter(Protocol):
    """
    Abstract interface that the core engine must implement or wrap.

    This keeps the adapter-based evolution independent from any concrete
    storage schema. It assumes P2 has provided:
        - persistent storage,
        - usage / recency index,
        - optional region clustering.
    """

    # -- Region / node materialization -------------------------------------

    def load_region_stats(self, graph_id: str, region_id: str) -> RegionStats:
        """
        Build a RegionStats snapshot from storage / indices.

        The implementation SHOULD:
            - respect config.max_region_size (e.g., truncate or sub-cluster),
            - order node_ids consistently across calls.
        """
        ...

    def get_query_stats(self, graph_id: str, region_id: str) -> QueryStats:
        """
        Return aggregate query statistics for this region.

        Implementations can assemble this from an EventJournal, QA harness,
        or rolling counters. For tests it can be trivial or synthetic.
        """
        ...

    # -- Evolution primitives ----------------------------------------------

    def merge_nodes(self, graph_id: str, keep_id: str, drop_id: str) -> None:
        """
        Merge `drop_id` into `keep_id` using the antisymmetric wedge operator
        defined in core/antisym.py (called indirectly via engine).

        Invariants:
            - All children of drop_id now inherit from keep_id.
            - Statistics / usage counts are consolidated.
            - drop_id is marked as inactive / tombstoned, not hard-deleted.
        """
        ...

    def prune_node(self, graph_id: str, node_id: str) -> None:
        """
        Remove a cold leaf node from the FIG.

        Invariants:
            - Only safe leaves (or nodes with low impact) should be pruned.
            - Implementations may soft-delete via a flag.
        """
        ...

    def promote_node(self, graph_id: str, node_id: str) -> None:
        """
        Promote a highly-used node.

        "Promotion" is intentionally abstract: the engine might:
            - increase its inheritance fractions as a parent in the region,
            - reduce its depth,
            - pin it in a hot cache.

        This call is where you encode that policy.
        """
        ...


# ---------------------------------------------------------------------------
# Adapter-level utility helpers: safe positives, cosine matrix, etc.
# ---------------------------------------------------------------------------


def _safe_positive(x: float, eps: float = 1e-9) -> float:
    """Clamp to a small positive value to avoid log(0) and division by zero."""
    return x if x > eps else eps


def _safe_positive_array(arr: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    """Clamp array elements to positive values to avoid log(0) and division by zero."""
    return np.maximum(arr, eps)


def _estimate_divergence_from_query_stats(stats: QueryStats) -> float:
    """
    Concrete D estimate from QueryStats.

    total = hits + misses
    p_err = misses / total
    D    = -log(1 - p_err + ε)
    """
    total = stats.hits + stats.misses
    if total <= 0:
        # No information yet; treat as neutral.
        return 0.0

    p_err = stats.misses / float(total)
    p_err = min(max(p_err, 0.0), 1.0)
    # accuracy = 1 - p_err; clamp for stability
    accuracy = 1.0 - p_err
    accuracy = _safe_positive(accuracy)
    return float(-math.log(accuracy))


def _estimate_fractal_entropy_from_region_stats(region: RegionStats) -> float:
    """
    Concrete H estimate from RegionStats.

    H = H_usage + R_penalty

    where H_usage is normalized Shannon entropy over usage weights and
    R_penalty is the redundancy_index ∈ [0, 1].
    """
    n = len(region.node_ids)
    if n == 0:
        return 0.0

    usage = np.asarray(region.usage_counts, dtype=float)
    total_usage = float(usage.sum())
    if total_usage <= 0.0:
        # uniform distribution if we have zero usage info
        p = np.full(n, 1.0 / n, dtype=float)
    else:
        p = usage / total_usage

    # Shannon entropy normalized by log(N) so that 0 <= H_usage <= 1
    H_usage = float(-(p * np.log(_safe_positive_array(p))).sum())
    H_usage /= math.log(n) if n > 1 else 1.0

    # Redundancy penalty – treat redundancy_index as already in [0, 1]
    R_penalty = float(max(region.redundancy_index, 0.0))

    return H_usage + R_penalty


def _cosine_similarity_matrix(vectors: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity matrix for a stack of vectors.

    This is used only on small regions (<= max_region_size), so a dense
    O(N^2) computation is acceptable. For larger graphs, pre-clustering is
    required at the adapter layer.
    """
    if vectors.size == 0:
        return np.zeros((0, 0), dtype=float)

    v = vectors.astype(float)
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    norms = np.where(norms == 0.0, 1.0, norms)
    v_norm = v / norms
    sim = v_norm @ v_norm.T
    # Clamp numerically noisy values into [-1, 1]
    np.clip(sim, -1.0, 1.0, out=sim)
    return sim


def _choose_merge_pairs(
    region: RegionStats,
    sim_matrix: np.ndarray,
    cfg: RegionEvolutionConfig,
) -> List[Tuple[int, int]]:
    """
    Greedily choose node index pairs (keep_idx, drop_idx) to merge.

    Strategy
    --------
    - Consider pairs with cosine similarity >= merge_similarity_threshold.
    - Prefer merging younger / lower-usage nodes into older / higher-usage
      ones to respect your "inheritance from strong parents" intuition.
    """
    n = len(region.node_ids)
    if n == 0:
        return []

    threshold = cfg.merge_similarity_threshold
    usage = np.asarray(region.usage_counts, dtype=float)
    created = np.asarray(region.created_ats, dtype=float)

    candidates: List[Tuple[float, int, int]] = []

    for i in range(n):
        for j in range(i + 1, n):
            s_ij = sim_matrix[i, j]
            if s_ij < threshold:
                continue
            # Higher similarity should be prioritized first.
            # We store negative similarity for sort ascending.
            candidates.append((-float(s_ij), i, j))

    candidates.sort()

    merged_indices: set[int] = set()
    result_pairs: List[Tuple[int, int]] = []

    for _neg_s, i, j in candidates:
        if len(result_pairs) >= cfg.max_merges_per_step:
            break
        if i in merged_indices or j in merged_indices:
            continue

        # Decide keep/drop:
        #   - keep higher usage,
        #   - if tie, keep older node (smaller created_at).
        if usage[i] > usage[j]:
            keep, drop = i, j
        elif usage[j] > usage[i]:
            keep, drop = j, i
        else:
            keep, drop = (i, j) if created[i] <= created[j] else (j, i)

        merged_indices.add(drop)
        result_pairs.append((keep, drop))

    return result_pairs


def _choose_prune_candidates(
    region: RegionStats,
    query_stats: QueryStats,
    cfg: RegionEvolutionConfig,
) -> List[int]:
    """
    Choose node indices to prune (cold, low-value leaves).

    Heuristics
    ----------
    - usage <= prune_usage_threshold
    - no (or very low) per-node hits
    - not already heavily merged sinks (we prefer to keep those as hubs)
    """
    usage = np.asarray(region.usage_counts, dtype=float)
    merged = np.asarray(region.merged_counts, dtype=float)

    per_node_hits = query_stats.per_node_hits
    indices: List[int] = []

    for idx, node_id in enumerate(region.node_ids):
        if usage[idx] > cfg.prune_usage_threshold:
            continue

        hits = per_node_hits.get(node_id, 0)
        if hits > 0:
            continue

        # Heuristic: heavily merged nodes likely act as useful hubs; skip.
        if merged[idx] > 0:
            continue

        indices.append(idx)

    if not indices:
        return []

    # Prefer pruning the youngest nodes first (created most recently).
    created = np.asarray(region.created_ats, dtype=float)
    indices.sort(key=lambda i: created[i], reverse=True)

    return indices[: cfg.max_prunes_per_step]


def _choose_promotions(
    region: RegionStats,
    query_stats: QueryStats,
    cfg: RegionEvolutionConfig,
) -> List[int]:
    """
    Choose node indices to promote (hot / central nodes).

    Heuristics
    ----------
    - Primarily sorted by per-node hits (importance for recall).
    - Ties broken by usage_count and age (older hubs first).
    """
    per_node_hits = query_stats.per_node_hits or {}
    usage = np.asarray(region.usage_counts, dtype=float)
    created = np.asarray(region.created_ats, dtype=float)

    scored: List[Tuple[int, int, float, int]] = []
    for idx, node_id in enumerate(region.node_ids):
        hits = per_node_hits.get(node_id, 0)
        if hits <= 0 and usage[idx] <= 0:
            continue
        scored.append((hits, int(usage[idx]), -created[idx], idx))

    if not scored:
        return []

    # Sort descending by hits, then usage, then older first.
    scored.sort(reverse=True)
    top = scored[: cfg.promote_top_k]
    return [entry[-1] for entry in top]


# ---------------------------------------------------------------------------
# evolve_region – single region pass using J(D, H, λ)
# ---------------------------------------------------------------------------


def evolve_region(
    graph_id: str,
    region_id: str,
    adapter: EvolutionAdapter,
    config: Optional[RegionEvolutionConfig] = None,
) -> EvolutionStepResult:
    """
    Run one evolution pass over a single region (adapter-based).

    Workflow
    --------
    1. Load RegionStats and QueryStats from the adapter.
    2. Compute D_before, H_before, J_before (using D/H helpers).
    3. Propose:
           - merge pairs,
           - prune candidates,
           - promotions.
    4. Apply actions via adapter primitives.
    5. Reload stats and recompute D_after, H_after, J_after.
    6. Mark whether J worsened beyond tolerance (no rollback yet).
    7. Return EvolutionStepResult for logging / metrics / UI.

    This function is deliberately synchronous and deterministic given:
        graph_id, region_id, adapter snapshot, config.
    """
    cfg = config or RegionEvolutionConfig()
    t0 = time.perf_counter()

    # --- Step 1: load snapshot + query stats ---------------------------------
    region_before = adapter.load_region_stats(graph_id, region_id)
    query_stats = adapter.get_query_stats(graph_id, region_id)

    # Defensive truncation: adapter SHOULD already respect this, but we
    # enforce it here to protect against accidentally huge regions.
    if len(region_before.node_ids) > cfg.max_region_size:
        logger.warning(
            "Region %s:%s has %d nodes (> %d); truncating in evolution pass.",
            graph_id,
            region_id,
            len(region_before.node_ids),
            cfg.max_region_size,
        )
        slice_idx = np.arange(cfg.max_region_size)
        region_before = RegionStats(
            graph_id=region_before.graph_id,
            region_id=region_before.region_id,
            node_ids=region_before.node_ids[: cfg.max_region_size],
            vectors=region_before.vectors[slice_idx],
            usage_counts=region_before.usage_counts[slice_idx],
            merged_counts=region_before.merged_counts[slice_idx],
            created_ats=region_before.created_ats[slice_idx],
            redundancy_index=float(region_before.redundancy_index),
        )

    # --- Step 2: compute objective before ------------------------------------
    D_before = _estimate_divergence_from_query_stats(query_stats)
    H_before = _estimate_fractal_entropy_from_region_stats(region_before)
    J_before = region_objective(D_before, H_before, cfg.lambda_entropy)

    actions: List[EvolutionAction] = []

    # Early-exit: nothing to do for empty or singleton regions.
    if len(region_before.node_ids) <= 1:
        duration = time.perf_counter() - t0
        return EvolutionStepResult(
            graph_id=graph_id,
            region_id=region_id,
            D_before=D_before,
            H_before=H_before,
            J_before=J_before,
            D_after=D_before,
            H_after=H_before,
            J_after=J_before,
            accepted=True,
            actions=actions,
            duration_s=duration,
        )

    # --- Step 3: propose merge / prune / promote -----------------------------
    sim_matrix = _cosine_similarity_matrix(region_before.vectors)

    merge_pairs = _choose_merge_pairs(region_before, sim_matrix, cfg)
    prune_indices = _choose_prune_candidates(region_before, query_stats, cfg)
    promote_indices = _choose_promotions(region_before, query_stats, cfg)

    if cfg.enable_logging:
        logger.debug(
            "Evolution candidates for %s:%s – merges=%d, prunes=%d, promotes=%d",
            graph_id,
            region_id,
            len(merge_pairs),
            len(prune_indices),
            len(promote_indices),
        )

    # --- Step 4: apply actions via adapter -----------------------------------
    # Merges
    for keep_idx, drop_idx in merge_pairs:
        keep_id = region_before.node_ids[keep_idx]
        drop_id = region_before.node_ids[drop_idx]
        adapter.merge_nodes(graph_id, keep_id=keep_id, drop_id=drop_id)
        actions.append(
            EvolutionAction(
                kind="merge",
                details=f"merge drop={drop_id} -> keep={keep_id}",
            )
        )

    # Prunes
    for idx in prune_indices:
        node_id = region_before.node_ids[idx]
        adapter.prune_node(graph_id, node_id=node_id)
        actions.append(
            EvolutionAction(
                kind="prune",
                details=f"prune node={node_id}",
            )
        )

    # Promotions
    for idx in promote_indices:
        node_id = region_before.node_ids[idx]
        adapter.promote_node(graph_id, node_id=node_id)
        actions.append(
            EvolutionAction(
                kind="promote",
                details=f"promote node={node_id}",
            )
        )

    # --- Step 5: reload and recompute objective ------------------------------
    region_after = adapter.load_region_stats(graph_id, region_id)
    D_after = _estimate_divergence_from_query_stats(query_stats)
    H_after = _estimate_fractal_entropy_from_region_stats(region_after)
    J_after = region_objective(D_after, H_after, cfg.lambda_entropy)

    # --- Step 6: accept / (future rollback hook) -----------------------------
    delta_J = J_after - J_before
    accepted = delta_J <= cfg.accept_worse_objective_tolerance

    if cfg.enable_logging:
        logger.debug(
            "Evolution result for %s:%s – "
            "D: %.4f -> %.4f, H: %.4f -> %.4f, J: %.4f -> %.4f (ΔJ=%.4g, accepted=%s)",
            graph_id,
            region_id,
            D_before,
            D_after,
            H_before,
            H_after,
            J_before,
            J_after,
            delta_J,
            accepted,
        )

    duration = time.perf_counter() - t0

    return EvolutionStepResult(
        graph_id=graph_id,
        region_id=region_id,
        D_before=D_before,
        H_before=H_before,
        J_before=J_before,
        D_after=D_after,
        H_after=H_after,
        J_after=J_after,
        accepted=accepted,
        actions=actions,
        duration_s=duration,
    )
