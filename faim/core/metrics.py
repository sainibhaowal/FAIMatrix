from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import List, Optional, Protocol, Sequence, cast

import numpy as np

from faim.data.storage.store import FAIMStore

from .evolution import (
    EvolutionConfig,
    Region,
    compute_region_redundancy,
    discover_regions,
)
from .math import GOLDEN_SCALE
from .types import GraphId, NodeRecord

# faim/core/metrics.py

# faim/core/metrics.py
"""
faim.core.metrics

Metrics & fractal-dimension diagnostics for FAIM (P1.5 + P3).

Golden Edition:
- Fractal dimension estimator D = log P / log(1 / s).
- Region-level branching estimation.
- Graph-level D summary for use in evolution diagnostics.
- P3 metrics:
    * compression_ratio(graph_id)
    * redundancy_index(graph_id)
    * drift_score(graph_id) on fixed QA list
    * latency_stats(graph_id) with p50/p95
"""

# ============================================================================
# Fractal dimension core metric (P1.5 – existing)
# ============================================================================


def estimate_fractal_dimension(
    branching_factor: float,
    *,
    scale: float = GOLDEN_SCALE,
) -> float:
    """
    Estimate fractal dimension:

        D = log(P) / log(1 / s)

    where:
      - P is an effective branching factor (average children per node),
      - s is the scaling factor (default: GOLDEN_SCALE = 1 / φ).

    Returns 0.0 for degenerate cases (P <= 1 or invalid scale).
    """
    if branching_factor <= 1.0:
        return 0.0
    if not (0.0 < scale < 1.0):
        return 0.0

    return float(math.log(branching_factor) / math.log(1.0 / scale))


# ============================================================================
# Region-level branching estimation (existing)
# ============================================================================


def estimate_region_branching(store: FAIMStore, region: Region) -> float:
    """
    Estimate average branching P for a region as:

        P = mean(children_per_non_leaf_node)

    Nodes without children are not counted in the average. If there are
    no non-leaf nodes, returns 0.0.
    """
    total_children = 0
    counted_nodes = 0

    for node_id in region.node_ids:
        node = store.get_node(region.graph_id, node_id)
        if node is None:
            continue
        if not node.children:
            continue

        total_children += len(node.children)
        counted_nodes += 1

    if counted_nodes == 0:
        return 0.0

    return float(total_children) / float(counted_nodes)


# ============================================================================
# Graph-level fractal-D summary (existing)
# ============================================================================


@dataclass(frozen=True)
class FractalDimensionDiagnostics:
    """
    Summary of fractal-dimension statistics for a graph.

    Attributes
    ----------
    graph_id:
        Identifier of the graph these diagnostics refer to.
    mean_D:
        Mean fractal dimension across regions.
    min_D:
        Minimum fractal dimension across regions.
    max_D:
        Maximum fractal dimension across regions.
    target_D:
        Design target (e.g. ~2.5 from your spec).
    """

    graph_id: GraphId
    mean_D: float
    min_D: float
    max_D: float
    target_D: float

    def is_within_target(self, *, tolerance: float = 0.5) -> bool:
        """
        Return True if the mean D is within `tolerance` of target_D.

        Higher layers (services/CLI) can use this to decide when to log
        warnings, trigger alerts, or adjust evolution parameters.
        """
        return abs(self.mean_D - self.target_D) <= tolerance


def summarize_graph_fractal_dimension(
    store: FAIMStore,
    regions: Sequence[Region],
    *,
    target_D: float = 2.5,
    scale: float = GOLDEN_SCALE,
) -> FractalDimensionDiagnostics:
    """
    Compute basic fractal-D stats for a set of regions.

    Typical usage:
    - Call discover_regions(...) to get Region objects.
    - Pass store + regions here to get a diagnostic summary.

    This function does not perform logging by itself; it is intended
    to feed metrics and logging layers.
    """
    if not regions:
        # When we have no regions, we still return a well-typed diagnostics
        # object. GraphId is unknown here, so we use an empty identifier.
        return FractalDimensionDiagnostics(
            graph_id=cast(GraphId, ""),
            mean_D=0.0,
            min_D=0.0,
            max_D=0.0,
            target_D=target_D,
        )

    Ds: list[float] = []

    for region in regions:
        P = estimate_region_branching(store, region)
        D = estimate_fractal_dimension(P, scale=scale)
        if D > 0.0:
            Ds.append(D)

    if not Ds:
        return FractalDimensionDiagnostics(
            graph_id=regions[0].graph_id,
            mean_D=0.0,
            min_D=0.0,
            max_D=0.0,
            target_D=target_D,
        )

    mean_D = float(sum(Ds) / len(Ds))
    return FractalDimensionDiagnostics(
        graph_id=regions[0].graph_id,
        mean_D=mean_D,
        min_D=min(Ds),
        max_D=max(Ds),
        target_D=target_D,
    )


# ============================================================================
# P3 Metrics – Compression, Redundancy, Drift, Latency
# ============================================================================


def compression_ratio(store: FAIMStore, graph_id: GraphId) -> float:
    """
    Estimate an effective compression ratio for a graph.

    Intuition
    ---------
    We treat each surviving node as representing:
        1 + merged_count
    "raw" memories (writes) that have been compressed into it.

    Then:

        total_raw  = Σ (1 + merged_count_i)
        live_nodes = number of non-pruned nodes
        CR         = total_raw / live_nodes

    Higher CR ⇒ more raw updates compressed into fewer nodes.
    """
    live_nodes = 0
    total_raw_units = 0

    for node in store.iter_nodes(graph_id):
        # Skip logically pruned nodes (LSB flag).
        if node.flags & 0b1:
            continue
        live_nodes += 1

        merged_count = max(0, int(node.merged_count))
        total_raw_units += 1 + merged_count

    if live_nodes == 0:
        return 0.0

    return float(total_raw_units) / float(live_nodes)


def redundancy_index(
    store: FAIMStore,
    graph_id: GraphId,
    *,
    config: Optional[EvolutionConfig] = None,
) -> float:
    """
    Compute a graph-level redundancy index R.

    Definition
    ----------
    - Discover regions via discover_regions(...).
    - For each region, compute region redundancy R_i using the same proxy
      as evolution (fraction of near-duplicate pairs).
    - Aggregate with a node-weighted mean:

        R = Σ (R_i * |region_i|) / Σ |region_i|

    This makes larger regions contribute proportionally more.
    """
    cfg = config or EvolutionConfig()
    regions = discover_regions(store, graph_id, config=cfg)
    if not regions:
        return 0.0

    weighted_sum = 0.0
    total_nodes = 0

    for region in regions:
        R_i = compute_region_redundancy(store, region, config=cfg)
        n_i = len(region.node_ids)
        weighted_sum += R_i * float(n_i)
        total_nodes += n_i

    if total_nodes == 0:
        return 0.0

    return float(weighted_sum) / float(total_nodes)


# ---------------------------------------------------------------------------
# Drift score over a fixed QA list
# ---------------------------------------------------------------------------


class RetrievalEngine(Protocol):
    """
    Minimal retrieval engine protocol for drift/latency metrics.

    Any engine with a compatible `retrieve(graph_id, query, k)` method
    (e.g. faim.core.engine.FAIMEngine) satisfies this.
    """

    def retrieve(
        self,
        graph_id: str,
        query: str,
        k: int = 32,
    ) -> Sequence[NodeRecord]: ...


@dataclass(frozen=True)
class QAPair:
    """
    Simple QA pair used for drift and latency benchmarks.

    Attributes
    ----------
    query:
        Query string to send to the engine.
    min_results:
        Minimum number of retrieved nodes needed for the QA to be
        considered a "hit". Defaults to 1 (any non-empty result).
    """

    query: str
    min_results: int = 1


def drift_score(
    engine: RetrievalEngine,
    graph_id: GraphId,
    qa_pairs: Sequence[QAPair],
    *,
    k: int = 8,
) -> float:
    """
    Compute a drift score on a fixed QA list.

    Definition
    ----------
    For each QAPair:
        - Run engine.retrieve(graph_id, query, k).
        - Count it as a "hit" if len(results) >= min_results.

    Let:
        accuracy = hits / len(qa_pairs)

    Then:
        drift_score = 1 - accuracy

    Interpretation
    --------------
    - drift_score ≈ 0.0 ⇒ good; QA set still mostly passes.
    - drift_score ↑   ⇒ deterioration / drift in retrieval behaviour.

    P3 target: keep drift_score stable or small while evolution reduces
    redundancy R over time.
    """
    if not qa_pairs:
        return 0.0

    hits = 0
    total = len(qa_pairs)

    for qa in qa_pairs:
        results = engine.retrieve(str(graph_id), qa.query, k=k)
        if len(results) >= qa.min_results:
            hits += 1

    accuracy = float(hits) / float(total)
    return float(1.0 - accuracy)


# ---------------------------------------------------------------------------
# Latency statistics (p50 / p95)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LatencyStats:
    """
    Latency statistics for a batch of retrievals.

    Attributes
    ----------
    graph_id:
        Graph identifier.
    p50_ms:
        50th percentile (median) latency in milliseconds.
    p95_ms:
        95th percentile latency in milliseconds.
    max_ms:
        Maximum observed latency in milliseconds.
    count:
        Number of retrievals measured.
    """

    graph_id: GraphId
    p50_ms: float
    p95_ms: float
    max_ms: float
    count: int


def latency_stats(
    engine: RetrievalEngine,
    graph_id: GraphId,
    queries: Sequence[str],
    *,
    k: int = 8,
) -> LatencyStats:
    """
    Measure retrieval latency over a list of queries.

    Implementation
    --------------
    - For each query, call engine.retrieve(graph_id, query, k) and measure
      wall-clock latency.
    - Returns p50, p95, max in milliseconds.

    This is intended for synthetic benchmarks (scripts/benchmarks.py),
    not on every request in production.
    """
    if not queries:
        return LatencyStats(
            graph_id=graph_id,
            p50_ms=0.0,
            p95_ms=0.0,
            max_ms=0.0,
            count=0,
        )

    durations_ms: List[float] = []

    for q in queries:
        t0 = time.perf_counter()
        _ = engine.retrieve(str(graph_id), q, k=k)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        durations_ms.append(float(dt_ms))

    arr = np.asarray(durations_ms, dtype=float)
    p50 = float(np.percentile(arr, 50.0))
    p95 = float(np.percentile(arr, 95.0))
    max_ms = float(arr.max())

    return LatencyStats(
        graph_id=graph_id,
        p50_ms=p50,
        p95_ms=p95,
        max_ms=max_ms,
        count=len(durations_ms),
    )


__all__ = (
    # Fractal-D (existing)
    "estimate_fractal_dimension",
    "estimate_region_branching",
    "FractalDimensionDiagnostics",
    "summarize_graph_fractal_dimension",
    # P3 metrics
    "compression_ratio",
    "redundancy_index",
    "RetrievalEngine",
    "QAPair",
    "drift_score",
    "LatencyStats",
    "latency_stats",
)
