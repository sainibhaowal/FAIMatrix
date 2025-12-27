# ============================================================================
#  P3 METRICS CONTRACT TESTS  –  FAIM CORE
# ----------------------------------------------------------------------------
#  What we verify here
#  -------------------
#  - compression_ratio(graph_id) returns a positive float
#  - redundancy_index(graph_id) returns a float in [0, 1]
#  - drift_score(...) returns a bounded float
#  - latency_stats(...) returns a LatencyStats dataclass with sane values
#
#  These tests are deliberately lightweight: they exercise the public API
#  without depending on real SqliteStore or heavy workloads. We use simple
#  fake objects that match the duck-typed interface expected by metrics.py
#  and evolution.discover_regions.
# ============================================================================

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, cast

import numpy as np
from faim.core import metrics
from faim.core.metrics import QAPair, RetrievalEngine
from faim.core.types import GraphId
from faim.storage.store import FAIMStore

# ---------------------------------------------------------------------------
#  Fakes for store & engine
# ---------------------------------------------------------------------------


@dataclass
class _FakeNode:
    """
    Minimal NodeRecord-like object for metrics tests.

    It only carries the attributes actually used by:
      - compression_ratio
      - redundancy_index (via evolution.discover_regions)
    """

    id: str
    graph_id: str = "TEST_GRAPH"
    vec: np.ndarray = field(default_factory=lambda: np.zeros(4, dtype=np.float32))
    parents: List[object] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    payload_ref: Optional[str] = None
    created_at: float = 0.0
    last_used_at: float = 0.0
    use_count: int = 1
    merged_count: int = 0
    # flags bit 0 == tombstone (pruned/deleted)
    flags: int = 0

    def __post_init__(self) -> None:
        if self.parents is None:
            self.parents = []
        if self.children is None:
            self.children = []


class _FakeStore:
    """
    Tiny in-memory FAIMStore-like object.

    Only the methods required by metrics.py + evolution.discover_regions are
    implemented: iter_nodes(graph_id) and get_node(graph_id, node_id).
    """

    def __init__(self, nodes: Iterable[_FakeNode]) -> None:
        self._nodes: Dict[str, _FakeNode] = {n.id: n for n in nodes}

    def iter_nodes(self, graph_id: str):
        # Ignore graph_id, this is just a unit-test stub.
        return list(self._nodes.values())

    def get_node(self, graph_id: str, node_id: str) -> Optional[_FakeNode]:
        return self._nodes.get(node_id)


class _FakeEngine:
    """
    Minimal engine stub used for latency_stats + drift_score tests.

    It implements retrieve(graph_id, query) and returns quickly so that
    latency measurement is deterministic and tiny.
    """

    def __init__(self, results_for_query: Mapping[str, List[str]]) -> None:
        self._results_for_query = dict(results_for_query)

    def retrieve(self, graph_id: str, query: str, k: int = 32):
        # We ignore graph_id and k; this is a fast, deterministic stub.
        _ = graph_id, k
        ids = self._results_for_query.get(query, [])
        return ids


# ---------------------------------------------------------------------------
#  Tests
# ---------------------------------------------------------------------------


def test_compression_ratio_is_positive_and_reasonable() -> None:
    """
    P3 contract: compression_ratio(graph_id) must return a positive float
    even on tiny synthetic graphs. We don't require a specific value here.
    """
    nodes = [
        _FakeNode("n1", merged_count=3),
        _FakeNode("n2", merged_count=0),
        _FakeNode("n3", merged_count=1, flags=0b1),  # tombstoned -> ignored
    ]
    store = _FakeStore(nodes)

    value = metrics.compression_ratio(
        cast(FAIMStore, store),
        graph_id=cast(GraphId, "TEST_GRAPH"),
    )

    assert isinstance(value, float)
    assert value > 0.0


def test_redundancy_index_in_unit_interval() -> None:
    """
    P3 contract: redundancy_index(graph_id) must be a float within [0, 1].

    The underlying implementation uses cosine similarity + thresholds, so
    the average fraction of "near-duplicate" neighbours should never exceed 1.
    """
    # Simple, slightly different vectors
    v1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([0.9, 0.1, 0.0, 0.0], dtype=np.float32)
    v3 = np.array([0.8, 0.2, 0.0, 0.0], dtype=np.float32)

    nodes = [
        _FakeNode("n1", vec=v1),
        _FakeNode("n2", vec=v2),
        _FakeNode("n3", vec=v3),
    ]
    store = _FakeStore(nodes)

    value = metrics.redundancy_index(
        cast(FAIMStore, store),
        graph_id=cast(GraphId, "TEST_GRAPH"),
    )

    assert isinstance(value, float)
    assert 0.0 <= value <= 1.0


def test_drift_score_is_bounded() -> None:
    """
    P3 contract: drift_score(engine, graph_id, qa_pairs, k) returns a finite
    float in [0, 1] for a simple synthetic scenario.
    """
    engine = _FakeEngine(
        results_for_query={
            "q_good": ["hit1", "hit2"],
            "q_bad": [],
        }
    )

    qa_pairs = [
        QAPair(query="q_good", min_results=1),
        QAPair(query="q_bad", min_results=1),
    ]

    value = metrics.drift_score(
        cast(RetrievalEngine, engine),
        cast(GraphId, "TEST_GRAPH"),
        qa_pairs=qa_pairs,
        k=4,
    )

    assert isinstance(value, float)
    assert 0.0 <= value <= 1.0


def test_latency_stats_has_expected_shape() -> None:
    """
    P3 contract: latency_stats returns a LatencyStats dataclass with the
    standard buckets used by FAIM Lab UI (p50, p95, max, count).
    """
    engine = _FakeEngine(results_for_query={"q1": ["x"], "q2": []})
    queries = ["q1", "q2", "q3"]

    stats = metrics.latency_stats(
        cast(RetrievalEngine, engine),
        cast(GraphId, "TEST_GRAPH"),
        queries=queries,
    )

    # Ensure we got the dataclass from metrics, not a plain dict.
    assert isinstance(stats, metrics.LatencyStats)
    assert stats.graph_id == "TEST_GRAPH"
    assert stats.count == len(queries)
    assert stats.p50_ms >= 0.0
    assert stats.p95_ms >= 0.0
    assert stats.max_ms >= 0.0
    # p95 and max should not be *smaller* than p50 in any sane implementation.
    assert stats.p95_ms >= stats.p50_ms
    assert stats.max_ms >= stats.p95_ms
