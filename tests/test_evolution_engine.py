from __future__ import annotations

import numpy as np
import pytest
from faim.core.evolution import (
    EvolutionConfig,
    compute_region_redundancy,
    discover_regions,
    evolve_graph_once,
)
from faim.core.types import GraphId, NodeId, NodeRecord, ParentRef
from faim.storage.sqlite_store import SqliteStore


def _build_synthetic_graph(store: SqliteStore, graph_id: GraphId) -> None:
    """
    Build a small synthetic FIG with:
    - one root node,
    - a cluster of highly redundant children,
    - a few unique children.
    """
    dim = 64

    # Root node
    root_id: NodeId = NodeId(f"{graph_id}:root")
    root = NodeRecord(
        id=root_id,
        graph_id=graph_id,
        vec=np.zeros(dim, dtype=np.float32),
        parents=[],
        children=[],
        payload_ref=None,
        created_at=0.0,
        last_used_at=0.0,
        use_count=1,
        merged_count=0,
        flags=0,
    )
    store.upsert_node(root)

    children_ids: list[NodeId] = []

    # Redundant cluster: identical vectors, same parent
    base_vec = np.ones(dim, dtype=np.float32)
    for i in range(8):
        nid: NodeId = NodeId(f"{graph_id}:dup-{i}")
        node = NodeRecord(
            id=nid,
            graph_id=graph_id,
            vec=base_vec.copy(),
            parents=[ParentRef(parent_id=root_id, fraction=1.0)],
            children=[],
            payload_ref=None,
            created_at=0.0,
            last_used_at=0.0,
            use_count=5,
            merged_count=0,
            flags=0,
        )
        store.upsert_node(node)
        children_ids.append(nid)

    # Unique children: near-orthogonal basis vectors
    for i in range(4):
        nid: NodeId = NodeId(f"{graph_id}:uniq-{i}")
        vec = np.zeros(dim, dtype=np.float32)
        vec[i] = 1.0
        node = NodeRecord(
            id=nid,
            graph_id=graph_id,
            vec=vec,
            parents=[ParentRef(parent_id=root_id, fraction=1.0)],
            children=[],
            payload_ref=None,
            created_at=0.0,
            last_used_at=0.0,
            use_count=3,
            merged_count=0,
            flags=0,
        )
        store.upsert_node(node)
        children_ids.append(nid)

    # Update root children list
    root = NodeRecord(
        id=root.id,
        graph_id=root.graph_id,
        vec=root.vec,
        parents=root.parents,
        children=children_ids,
        payload_ref=root.payload_ref,
        created_at=root.created_at,
        last_used_at=root.last_used_at,
        use_count=root.use_count,
        merged_count=root.merged_count,
        flags=root.flags,
    )
    store.upsert_node(root)


def _mean_redundancy(
    store: SqliteStore,
    graph_id: GraphId,
    cfg: EvolutionConfig,
) -> float:
    regions = discover_regions(store, graph_id, config=cfg)
    assert regions
    vals = [compute_region_redundancy(store, r, config=cfg) for r in regions]
    return float(np.mean(vals))


def test_evolution_reduces_redundancy(tmp_path) -> None:
    db_path = tmp_path / "evo.sqlite3"
    store = SqliteStore(db_path)
    graph_id: GraphId = GraphId("evo_graph")

    _build_synthetic_graph(store, graph_id)
    cfg = EvolutionConfig()

    R_before = _mean_redundancy(store, graph_id, cfg)
    stats = evolve_graph_once(store, graph_id, config=cfg)
    R_after = _mean_redundancy(store, graph_id, cfg)

    # Stats should be self-consistent
    assert stats.redundancy_before == pytest.approx(R_before, rel=1e-6)
    assert stats.redundancy_after == pytest.approx(R_after, rel=1e-6)

    # And redundancy should strictly decrease for this synthetic graph
    assert R_after < R_before


def test_evolution_is_monotone_over_multiple_steps(tmp_path) -> None:
    db_path = tmp_path / "evo_multi.sqlite3"
    store = SqliteStore(db_path)
    graph_id: GraphId = GraphId("evo_graph_multi")

    _build_synthetic_graph(store, graph_id)
    cfg = EvolutionConfig()

    last_R = _mean_redundancy(store, graph_id, cfg)
    for _ in range(5):
        stats = evolve_graph_once(store, graph_id, config=cfg)
        # Each step should not increase redundancy (within numeric noise).
        assert stats.redundancy_before == pytest.approx(last_R, rel=1e-6)
        assert stats.redundancy_after <= stats.redundancy_before + 1e-6
        last_R = stats.redundancy_after


def test_evolution_preserves_nearest_neighbor_quality(tmp_path) -> None:
    """
    Even after pruning/merging, every original node vector should still
    have a high-similarity representative in the evolved graph.
    """
    from faim.core.evolution import _cosine  # internal but deterministic helper

    db_path = tmp_path / "evo_recall.sqlite3"
    store = SqliteStore(db_path)
    graph_id: GraphId = GraphId("evo_graph_recall")

    _build_synthetic_graph(store, graph_id)
    cfg = EvolutionConfig()

    # Snapshot original active nodes and their vectors.
    original_nodes = [n for n in store.iter_nodes(graph_id) if (n.flags & 0b1) == 0]
    original_vecs = [n.vec for n in original_nodes]

    def _best_sim(vec, nodes) -> float:
        return max(_cosine(vec, n.vec) for n in nodes)

    baseline_best = [_best_sim(v, original_nodes) for v in original_vecs]

    evolve_graph_once(store, graph_id, config=cfg)

    evolved_nodes = [n for n in store.iter_nodes(graph_id) if (n.flags & 0b1) == 0]
    assert evolved_nodes  # sanity

    evolved_best = [_best_sim(v, evolved_nodes) for v in original_vecs]

    # Worst-case nearest-neighbor similarity should not degrade materially.
    assert min(evolved_best) >= min(baseline_best) - 1e-6
