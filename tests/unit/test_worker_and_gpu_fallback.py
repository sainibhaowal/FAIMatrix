from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import numpy as np

import pytest

from encoding import embedding_providers
from orchestration.jobs.worker import Worker


def test_worker_respects_configured_job_kinds_and_scan_flag(monkeypatch):
    monkeypatch.setenv(
        "FAIM_WORKER_JOB_KINDS",
        "storage_upload, ingest_secondary_index, unknown_kind",
    )
    monkeypatch.setenv("FAIM_WORKER_SELF_EVOLVE_SCAN_ENABLED", "false")
    monkeypatch.setenv("FAIM_BENCHMARK_MODE", "false")

    worker = Worker()
    assert worker.executable_job_kinds == ("storage_upload", "ingest_secondary_index")
    assert worker.self_evolve_scan_enabled is False


def test_worker_evolve_pool_isolation(monkeypatch):
    monkeypatch.setenv("FAIM_WORKER_JOB_KINDS", "evolve,domain_autonomy")
    monkeypatch.setenv("FAIM_WORKER_SELF_EVOLVE_SCAN_ENABLED", "true")
    monkeypatch.setenv("FAIM_BENCHMARK_MODE", "false")

    worker = Worker()
    assert worker.executable_job_kinds == ("evolve", "domain_autonomy")
    assert worker.self_evolve_scan_enabled is True


def test_resolve_embedding_device_auto_prefers_cuda_and_falls_back_to_cpu(monkeypatch):
    monkeypatch.setenv("FAIM_EMBEDDING_DEVICE", "auto")
    with patch.object(embedding_providers, "_cuda_available", return_value=True):
        assert embedding_providers._resolve_embedding_device() == "cuda"

    with patch.object(embedding_providers, "_cuda_available", return_value=False):
        assert embedding_providers._resolve_embedding_device() == "cpu"
        assert embedding_providers._resolve_embedding_device("cuda:0") == "cpu"


def test_encode_with_cpu_fallback_recovers_from_cuda_error():
    cuda_model = MagicMock()
    cuda_model.encode.side_effect = RuntimeError("CUDA out of memory")

    cpu_model = MagicMock()
    cpu_model.encode.return_value = np.array([[0.1, 0.2]], dtype=np.float32)

    with patch.object(
        embedding_providers,
        "_load_sentence_transformer_on_device",
        return_value=(cpu_model, "cpu"),
    ) as mock_load:
        emb, active_model, active_device = (
            embedding_providers._encode_sentence_transformer_with_fallback(
                cuda_model,
                "dummy-model",
                "cuda",
                ["hello world"],
            )
        )

    assert active_device == "cpu"
    assert active_model is cpu_model
    assert emb.shape == (1, 2)
    mock_load.assert_called_once_with("dummy-model", "cpu")


def test_vector_bank_top_k_and_radius_fall_back_to_cpu_on_gpu_error():
    pytest.importorskip("faim")
    from orchestration.perf.vector_bank import _GraphVectors

    gv = _GraphVectors(graph_id="g1", use_gpu=True)
    gv.add_or_update("n1", np.array([1.0, 0.0], dtype=np.float32))
    gv.add_or_update("n2", np.array([0.0, 1.0], dtype=np.float32))

    with (
        patch.object(gv, "_decide_use_gpu", return_value=True),
        patch.object(gv, "_top_k_gpu", side_effect=RuntimeError("CUDA error")),
        patch.object(gv, "_radius_gpu", side_effect=RuntimeError("CUDA error")),
    ):
        top = gv.top_k(np.array([1.0, 0.0], dtype=np.float32), k=1, use_gpu=True)
        rad = gv.radius(np.array([1.0, 0.0], dtype=np.float32), radius=0.5, use_gpu=True)

    assert top[0][0] == "n1"
    assert rad == ["n1"]


def test_native_matrix_kernels_compute_exact_cpu_fallback(monkeypatch):
    from core.engine_native import _matvec_gpu_or_cpu
    from core.query.query_engine import _native_cosine_sims_gpu_or_cpu

    monkeypatch.setenv("FAIM_USE_GPU_BACKEND", "auto")
    mat = np.array([[1.0, 0.0], [0.0, 2.0], [0.0, 0.0]], dtype=np.float32)
    q = np.array([1.0, 0.0], dtype=np.float32)

    sims = _native_cosine_sims_gpu_or_cpu(mat, q)
    assert np.allclose(sims, np.array([1.0, 0.0, 0.0], dtype=np.float32))

    dots = _matvec_gpu_or_cpu(mat, q)
    assert np.allclose(dots, np.array([1.0, 0.0, 0.0], dtype=np.float32))


def test_auth_key_cache_invalidation_and_query_meta_cache():
    from api.middleware.auth import (
        _VERIFIED_KEY_CACHE,
        _cache_digest,
        AuthDecision,
        invalidate_tenant_key_cache,
    )
    from orchestration.query_flow import _get_cached_graph_meta, _set_cached_graph_meta

    invalidate_tenant_key_cache()
    digest = _cache_digest("secret-k1")
    _VERIFIED_KEY_CACHE[("t1", digest)] = (
        AuthDecision(valid=True, auth_method="api_key_db", key_id="k1", scopes=[]),
        999999999.0,
    )
    invalidate_tenant_key_cache(tenant_id="t1", key_id="k1")
    assert ("t1", digest) not in _VERIFIED_KEY_CACHE

    _set_cached_graph_meta("t1", "g1", 3, {"metrics": {"avg_touch": 1.0}})
    assert _get_cached_graph_meta("t1", "g1", 3) == {"metrics": {"avg_touch": 1.0}}
    assert _get_cached_graph_meta("t1", "g1", 4) is None
