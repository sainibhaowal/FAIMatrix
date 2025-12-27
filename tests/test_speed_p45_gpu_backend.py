# ======================================================================
# FAIM HyperSpeed P4.5 – GPU backend
# Golden Edition – smoke-test GPU search when available.
# If no CUDA GPU is available, these tests are gracefully skipped.
# ======================================================================

from typing import Type

import numpy as np
import pytest
from faim.speed.spec import get_speed_budget

try:
    from faim.speed.gpu_backend import GPUBackendConfig, GPUSearchBackend
except Exception:  # pragma: no cover - GPU backend may be optional
    GPUBackendConfig = None  # type: ignore[assignment]
    GPUSearchBackend = None  # type: ignore[assignment]


def _build_cpu_matrix(n: int, dim: int) -> np.ndarray:
    rng = np.random.default_rng(2025)
    return rng.normal(size=(n, dim)).astype(np.float32)


@pytest.mark.skipif(
    GPUSearchBackend is None or GPUBackendConfig is None,
    reason="GPU backend module not importable",
)
def test_p45_gpu_backend_top_k_matches_cpu():
    """
    When a CUDA device is available, GPU top_k must match CPU ranking.
    If no GPU is present, this test is skipped.
    """
    # Narrow Optional types so type-checkers know they are not None.
    assert GPUSearchBackend is not None
    assert GPUBackendConfig is not None
    BackendCls: Type = GPUSearchBackend
    CfgCls: Type = GPUBackendConfig

    if not BackendCls.is_available():
        pytest.skip("No CUDA device available for P4.5 test")

    budget = get_speed_budget("CORE_DEV")
    dim = budget.dim
    n = 512

    cpu_mat = _build_cpu_matrix(n, dim)
    rng = np.random.default_rng(77)
    query = rng.normal(size=(dim,)).astype(np.float32)
    k = 10

    # CPU baseline
    cpu_scores = cpu_mat @ query
    cpu_top_idx = np.argsort(cpu_scores)[-k:][::-1]

    # GPU
    cfg = CfgCls()
    backend = BackendCls(cfg)
    backend.attach_cpu_matrix(cpu_mat)

    indices, scores = backend.top_k(query, k=k)
    assert indices.shape == (k,)
    assert scores.shape == (k,)

    # Indices must match CPU ordering
    assert list(indices.tolist()) == list(cpu_top_idx.tolist())


@pytest.mark.skipif(
    GPUSearchBackend is None or GPUBackendConfig is None,
    reason="GPU backend module not importable",
)
def test_p45_gpu_backend_radius_subsets_cpu():
    """
    radius_search() must return a subset consistent with CPU L2 distance
    filtering. We only check the set of indices, not ordering.
    """
    assert GPUSearchBackend is not None
    assert GPUBackendConfig is not None
    BackendCls: Type = GPUSearchBackend
    CfgCls: Type = GPUBackendConfig

    if not BackendCls.is_available():
        pytest.skip("No CUDA device available for P4.5 test")

    dim = 32
    n = 256
    cpu_mat = _build_cpu_matrix(n, dim)
    rng = np.random.default_rng(88)
    query = rng.normal(size=(dim,)).astype(np.float32)

    # CPU L2 distance baseline (same semantics as GPU radius):
    # dist^2 = ||x||^2 + ||q||^2 - 2 x·q
    x_norm_sq = np.sum(cpu_mat * cpu_mat, axis=1)
    q_norm_sq = float(np.dot(query, query))
    x_dot_q = cpu_mat @ query
    dist_sq = x_norm_sq + q_norm_sq - 2.0 * x_dot_q
    dists = np.sqrt(np.maximum(dist_sq, 0.0))

    # Choose a threshold that keeps some but not all vectors (near ones)
    thresh = float(np.percentile(dists, 30))
    expected_idx = np.where(dists <= thresh)[0]

    cfg = CfgCls()
    backend = BackendCls(cfg)
    backend.attach_cpu_matrix(cpu_mat)

    indices, dists_gpu = backend.radius_search(query, threshold=thresh)
    got_set = set(indices.tolist())
    exp_set = set(expected_idx.tolist())

    assert got_set == exp_set
