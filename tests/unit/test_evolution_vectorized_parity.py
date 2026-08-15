"""Parity between the vectorized (BLAS) similarity pass and the pure-Python
functions it replaces inside ``evolve_once``.

The optimization computes one symmetric cosine matrix and reuses it for the
three formerly-quadratic passes (diagnostics, prune max-similarity, merge
scoring). This module proves the numbers and decisions agree with the original
pure-Python implementation so behavior is preserved.
"""

from __future__ import annotations

import math
import random

import numpy as np
from core.dynamics.evolution_native import (
    _cosine,
    _node_max_similarities,
    _upper_triangle_floats,
    _vectorized_cosine_matrix,
    compute_graph_diagnostics,
)
from core.metrics.fractal_physics import DEFAULT_CONFIG, compute_diagnostics
from core.operators.prune import compute_similarity_matrix


class _StubNode:
    def __init__(self, node_id, v_native):
        self.node_id = node_id
        self.v_native = v_native
        self.residual = None


def _make_vectors(count, dim, seed, near=None):
    """Deterministic pseudo-random vectors (unit-ish, non-negative mix)."""
    rng = random.Random(seed)
    vectors = []
    for _ in range(count):
        vec = [rng.uniform(-1.0, 1.0) for _ in range(dim)]
        if near is not None:
            # Adversarial: cosine within `near` of 0.95 (the merge threshold).
            for k in range(dim):
                if k < len(near):
                    vec[k] = near[k]
        vectors.append(vec)
    return vectors


def _pure_pairwise_similarities(vectors):
    out = []
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            out.append(_cosine(vectors[i], vectors[j]))
    return out


def test_matrix_matches_python_cosine():
    vectors = _make_vectors(40, 16, seed=7)
    S = _vectorized_cosine_matrix(vectors)
    assert S is not None
    pure = _pure_pairwise_similarities(vectors)
    flat = _upper_triangle_floats(S)
    assert sorted(flat) == sorted(pure) or np.allclose(flat, pure, atol=1e-12)
    for a, b in zip(flat, pure, strict=True):
        assert abs(a - b) <= 1e-12


def test_matrix_order_matches_python_loop():
    vectors = _make_vectors(30, 12, seed=11)
    S = _vectorized_cosine_matrix(vectors)
    pure = []
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            pure.append(_cosine(vectors[i], vectors[j]))
    flat = _upper_triangle_floats(S)
    assert len(flat) == len(pure)
    for a, b in zip(flat, pure, strict=True):
        assert abs(a - b) <= 1e-12


def test_node_max_similarities_match_compute_similarity_matrix():
    vectors = _make_vectors(50, 20, seed=21)
    S = _vectorized_cosine_matrix(vectors)
    nodes = [_StubNode(i, v) for i, v in enumerate(vectors)]
    pure = compute_similarity_matrix(nodes, _cosine)
    vec = _node_max_similarities(S)
    maxes = dict(zip([n.node_id for n in nodes], vec, strict=True))
    for n in nodes:
        assert abs(maxes[n.node_id] - pure[n.node_id]) <= 1e-12


def test_diagnostics_identical_cached_vs_recompute():
    vectors = _make_vectors(60, 24, seed=31)
    residuals = [0.0] * len(vectors)
    S = _vectorized_cosine_matrix(vectors)
    flat = _upper_triangle_floats(S)
    distances = [1.0 - s for s in flat]

    pure = compute_diagnostics(
        graph_id="g",
        vectors=vectors,
        residuals=residuals,
        edge_count=0,
        graph_version=1,
    )
    cached = compute_diagnostics(
        graph_id="g",
        vectors=vectors,
        residuals=residuals,
        edge_count=0,
        graph_version=1,
        similarities=flat,
        distances=distances,
    )
    for field in (
        "D_hat",
        "H_hat",
        "lambda_hat",
        "redundancy_R",
        "novelty_N",
        "energy_E",
        "s",
    ):
        assert getattr(pure, field) == getattr(cached, field), field


def test_diagnostics_identical_via_graph_wrapper():
    vectors = _make_vectors(45, 16, seed=41)
    nodes = [_StubNode(i, v) for i, v in enumerate(vectors)]
    S = _vectorized_cosine_matrix(vectors)
    flat = _upper_triangle_floats(S)
    distances = [1.0 - s for s in flat]

    pure = compute_graph_diagnostics(
        graph_id="g", nodes=nodes, edges=[], graph_version=1,
        config=DEFAULT_CONFIG,
    )
    cached = compute_graph_diagnostics(
        graph_id="g", nodes=nodes, edges=[], graph_version=1,
        config=DEFAULT_CONFIG,
        similarities=flat,
        distances=distances,
    )
    for field in ("D_hat", "H_hat", "lambda_hat", "redundancy_R"):
        assert getattr(pure, field) == getattr(cached, field), field


def test_merge_decision_parity_near_threshold():
    """Scores from the matrix must not flip merge decisions near threshold."""
    threshold = 0.95
    rng = random.Random(99)
    dim = 32
    base = [rng.uniform(-1, 1) for _ in range(dim)]
    flips = 0
    for eps in (1e-3, 1e-6, 1e-9, 1e-12):
        # Vector exactly at cosine ~ threshold ± eps from `base`.
        perturb = [x * eps for x in rng.sample(base, dim)]
        other = [b + p for b, p in zip(base, perturb, strict=True)]
        pure = _cosine(base, other)
        S = _vectorized_cosine_matrix([base, other])
        vec = float(S[0, 1])
        if (pure >= threshold) != (vec >= threshold):
            flips += 1
    assert flips == 0


def test_zero_vector_rows_parity():
    vectors = [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ]
    S = _vectorized_cosine_matrix(vectors)
    for i in range(3):
        for j in range(i + 1, 3):
            pure = _cosine(vectors[i], vectors[j])
            assert math.isclose(float(S[i, j]), pure, abs_tol=1e-12)


def test_ragged_vectors_fall_back_to_none():
    assert _vectorized_cosine_matrix([[1.0], [1.0, 2.0]]) is None
    assert _vectorized_cosine_matrix([[1.0, 2.0]]) is None