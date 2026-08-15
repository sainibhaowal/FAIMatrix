#!/usr/bin/env python3
"""Micro-benchmark of the evolution cycle's pairwise passes.

Compares the legacy pure-Python quadratic work (diagnostics pairwise loop,
prune max-similarity matrix, opposition merge scoring — all recomputing cosine
per pair) against the single vectorized BLAS pass now used inside evolve_once.

Run:  .venv/bin/python scripts/bench_evolve_similarity.py [n]
"""

from __future__ import annotations

import random
import sys
import time

import numpy as np
from core.dynamics.evolution_native import (
    _cosine,
    _node_max_similarities,
    _upper_triangle_floats,
    _vectorized_cosine_matrix,
)
from core.metrics.fractal_physics import (
    DEFAULT_CONFIG,
    compute_redundancy_R,
    estimate_D_fractal,
    estimate_H_entropy,
)
from core.operators.prune import compute_similarity_matrix


class _StubNode:
    def __init__(self, node_id, v_native):
        self.node_id = node_id
        self.v_native = v_native


def _vectors(count, dim):
    rng = random.Random(1234)
    return [[rng.uniform(-1, 1) for _ in range(dim)] for _ in range(count)]


def _legacy_passes(vectors):
    """The three pure-Python quadratic passes, exactly as before."""
    n = len(vectors)

    # 1. Diagnostics pairwise similarities (H + R), plus D re-uses distances.
    sims = []
    for i in range(n):
        for j in range(i + 1, n):
            sims.append(_cosine(vectors[i], vectors[j]))
    estimate_H_entropy(sims, DEFAULT_CONFIG.bins, DEFAULT_CONFIG)
    compute_redundancy_R(sims, threshold=0.9, config=DEFAULT_CONFIG)
    distances = [1.0 - s for s in sims]
    estimate_D_fractal(vectors, DEFAULT_CONFIG.epsilons, DEFAULT_CONFIG, distances=distances)

    # 2. Prune max-similarity matrix.
    nodes = [_StubNode(i, v) for i, v in enumerate(vectors)]
    compute_similarity_matrix(nodes, _cosine)


def _vectorized_passes(vectors):
    S = _vectorized_cosine_matrix(vectors)
    flat = _upper_triangle_floats(S)
    distances = [1.0 - s for s in flat]
    estimate_H_entropy(np.asarray(flat, dtype=np.float64).tolist(), DEFAULT_CONFIG.bins, DEFAULT_CONFIG)
    compute_redundancy_R(list(flat), threshold=0.9, config=DEFAULT_CONFIG)
    estimate_D_fractal(vectors, DEFAULT_CONFIG.epsilons, DEFAULT_CONFIG, distances=distances)
    _node_max_similarities(S)


def bench(n, dim=64, runs=2):
    vectors = _vectors(n, dim)

    best_legacy = float("inf")
    for _ in range(runs):
        t0 = time.perf_counter()
        _legacy_passes(vectors)
        best_legacy = min(best_legacy, time.perf_counter() - t0)

    best_vec = float("inf")
    for _ in range(runs):
        t0 = time.perf_counter()
        _vectorized_passes(vectors)
        best_vec = min(best_vec, time.perf_counter() - t0)

    speedup = best_legacy / best_vec if best_vec > 0 else float("inf")
    print(
        f"n={n:>5}  pairs={n * (n - 1) // 2:>9}  "
        f"legacy={best_legacy:7.3f}s  vectorized={best_vec:7.3f}s  "
        f"speedup={speedup:6.1f}x"
    )


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    sizes = [int(arg)] if arg else [250, 500, 1000, 2000]
    for n in sizes:
        bench(n)