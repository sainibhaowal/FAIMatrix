# ======================================================================
# FAIM HyperSpeed P4.1 – Hot Vector Bank (RAM, CPU/GPU)
# Golden Edition – focuses on correctness; big 1M-node benchmarks live
# in bench_faim_p4.py, not in this unit test file.
# ======================================================================

from typing import List, Tuple

import numpy as np
from faim.speed.spec import get_speed_budget
from faim.speed.vector_bank import VectorBank


def _build_bank(n: int = 1024, dim: int = 32) -> Tuple[VectorBank, str, np.ndarray]:
    """
    Build a small VectorBank with one graph and N random vectors.
    Returns (bank, graph_id, matrix) where matrix[i] belongs to node f"n{i}".
    """
    budget = get_speed_budget("CORE_DEV")
    bank = VectorBank(budget, use_gpu_default=False)

    graph_id = "graph-1"
    rng = np.random.default_rng(42)
    mat = rng.normal(size=(n, dim)).astype(np.float32)

    for i in range(n):
        node_id = f"n{i}"
        bank.add_vector(graph_id, node_id, mat[i])

    return bank, graph_id, mat


def test_p41_top_k_matches_naive_cpu():
    """
    top_k() results must match a naive NumPy dot-product ranking.
    """
    bank, gid, mat = _build_bank(n=1024, dim=32)
    rng = np.random.default_rng(123)
    q = rng.normal(size=(mat.shape[1],)).astype(np.float32)

    k = 10
    results = bank.top_k(gid, q, k=k)
    assert len(results) == k

    # naive scores
    scores = mat @ q
    topk_idx = np.argsort(scores)[-k:][::-1]
    expected_ids: List[str] = [f"n{i}" for i in topk_idx]

    got_ids: List[str] = [node_id for node_id, _ in results]
    assert got_ids == expected_ids


def test_p41_radius_matches_naive_l2():
    """
    radius() results must match naive L2-distance filtering and ordering.
    """
    bank, gid, mat = _build_bank(n=512, dim=16)
    rng = np.random.default_rng(7)
    q = rng.normal(size=(mat.shape[1],)).astype(np.float32)

    # Choose a radius that returns a non-trivial subset.
    dists = np.linalg.norm(mat - q, axis=1)
    radius = float(np.median(dists))

    results = bank.radius(gid, q, radius)
    got_ids = [node_id for node_id, _ in results]

    mask = dists <= radius
    expected_indices = np.where(mask)[0]
    # sorted by distance ascending
    expected_indices = expected_indices[np.argsort(dists[expected_indices])]
    expected_ids = [f"n{i}" for i in expected_indices]

    assert got_ids == expected_ids


def test_p41_graph_isolation():
    """
    Different graphs must be isolated: vectors from other graphs must
    not appear in top_k results.
    """
    budget = get_speed_budget("CORE_DEV")
    bank = VectorBank(budget, use_gpu_default=False)
    rng = np.random.default_rng(99)

    g1, g2 = "g1", "g2"
    dim = 16

    # Graph 1: nodes n0..n9
    for i in range(10):
        v = rng.normal(size=(dim,)).astype(np.float32)
        bank.add_vector(g1, f"g1-{i}", v)

    # Graph 2: nodes m0..m9
    for i in range(10):
        v = rng.normal(size=(dim,)).astype(np.float32)
        bank.add_vector(g2, f"g2-{i}", v)

    q = rng.normal(size=(dim,)).astype(np.float32)
    res_g1 = bank.top_k(g1, q, k=5)
    res_g2 = bank.top_k(g2, q, k=5)

    assert all(node_id.startswith("g1-") for node_id, _ in res_g1)
    assert all(node_id.startswith("g2-") for node_id, _ in res_g2)


def test_p41_update_and_remove():
    """
    update_vector() must actually change search results, and remove_vector()
    must shrink the graph.
    """
    budget = get_speed_budget("CORE_DEV")
    bank = VectorBank(budget, use_gpu_default=False)
    gid = "g-update"
    dim = 8

    # Two nodes: a (far) and b (we will make b very close later)
    a_vec = np.full((dim,), 10.0, dtype=np.float32)
    b_vec = np.full((dim,), -10.0, dtype=np.float32)
    q = np.zeros((dim,), dtype=np.float32)

    bank.add_vector(gid, "a", a_vec)
    bank.add_vector(gid, "b", b_vec)

    _ = bank.top_k(gid, q, k=1)[0][0]
    # whichever is closer initially, we flip by updating 'b'
    bank.update_vector(gid, "b", np.zeros_like(b_vec))

    second = bank.top_k(gid, q, k=1)[0][0]
    assert second == "b"

    # Now remove 'b' and ensure only 'a' remains.
    bank.remove_vector(gid, "b")
    sizes = bank.graph_sizes
    assert sizes[gid] == 1
    ids = [nid for nid, _ in bank.top_k(gid, q, k=1)]
    assert ids == ["a"]
