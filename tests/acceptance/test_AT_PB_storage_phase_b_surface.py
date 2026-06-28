"""Phase B acceptance: storage backend completion API surface."""

from __future__ import annotations

import pathlib


def test_phase_b_storage_routes_present():
    from api.routers.storage import router

    paths = {route.path for route in router.routes}
    assert "/storage/uploads/{job_id}/cancel" in paths
    assert "/storage/files/{raw_id}/provenance" in paths
    assert "/storage/retention/execute" in paths
    assert "/storage/retention/jobs" in paths
    assert "/storage/reencryption/execute" in paths
    assert "/storage/reencryption/jobs" in paths
    assert "/storage/crypto/rotation/execute" in paths
    assert "/storage/crypto/rotation/jobs" in paths


def test_phase_b_retention_worker_module_exists():
    retention_module = pathlib.Path(
        "faim_native/orchestration/jobs/storage_retention.py"
    )
    assert retention_module.exists()
    content = retention_module.read_text()
    assert "run_storage_retention_cleanup" in content


def test_phase_b_worker_supports_storage_retention_and_reencryption_kinds():
    worker_path = pathlib.Path("faim_native/orchestration/jobs/worker.py")
    content = worker_path.read_text()
    assert 'kind == "storage_retention"' in content
    assert 'kind == "raw_reencryption"' in content
    assert 'kind == "crypto_rotation"' in content


def test_phase_b_raw_reencryption_module_exists():
    reencryption_module = pathlib.Path(
        "faim_native/orchestration/jobs/raw_reencryption.py"
    )
    assert reencryption_module.exists()
    content = reencryption_module.read_text()
    assert "run_raw_reencryption_backfill" in content
