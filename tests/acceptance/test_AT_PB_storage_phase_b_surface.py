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


def test_phase_b_retention_worker_module_exists():
    retention_module = pathlib.Path(
        "faim_native/orchestration/jobs/storage_retention.py"
    )
    assert retention_module.exists()
    content = retention_module.read_text()
    assert "run_storage_retention_cleanup" in content


def test_phase_b_worker_supports_storage_retention_kind():
    worker_path = pathlib.Path("faim_native/orchestration/jobs/worker.py")
    content = worker_path.read_text()
    assert 'kind == "storage_retention"' in content
