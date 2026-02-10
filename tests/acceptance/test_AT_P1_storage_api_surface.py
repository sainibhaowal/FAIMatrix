"""P1 Acceptance: Storage API surface exists and is wired."""

from __future__ import annotations

import pathlib


def test_storage_router_exists():
    from api.routers.storage import router

    assert router is not None


def test_storage_routes_present():
    from api.routers.storage import router

    paths = {route.path for route in router.routes}

    assert "/storage/uploads" in paths
    assert "/storage/uploads/{job_id}" in paths
    assert "/storage/uploads/{job_id}/events" in paths
    assert "/storage/files" in paths
    assert "/storage/files/{raw_id}" in paths
    assert "/storage/files/{raw_id}/ingest" in paths
    assert "/storage/files/{raw_id}/retry" in paths
    assert "/storage/summary" in paths
    assert "/storage/backends/health" in paths


def test_app_includes_storage_router_source():
    app_path = pathlib.Path("faim_native/api/app.py")
    content = app_path.read_text()

    assert "storage_router" in content
    assert "include_router(storage_router" in content


def test_storage_migration_exists():
    migration_path = pathlib.Path("faim_native/store/pg/migrations/0005_storage_files.sql")
    assert migration_path.exists()

    content = migration_path.read_text()
    assert "CREATE TABLE IF NOT EXISTS storage_files" in content
    assert "uq_storage_files_tenant_graph_raw" in content
