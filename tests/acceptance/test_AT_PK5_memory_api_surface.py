"""Phase K5 acceptance: memory API route surface and wiring."""

from __future__ import annotations

import pathlib


def test_phase_k5_memory_routes_present():
    from api.routers.memory import router

    paths = {route.path for route in router.routes}
    assert "/memory/search" in paths
    assert "/memory/{node_id}" in paths
    assert "/memory/{node_id}/provenance" in paths
    assert "/memory/write" in paths
    assert "/memory/{node_id}" in paths


def test_phase_k5_app_includes_memory_router():
    app_path = pathlib.Path("faim_native/api/app.py")
    content = app_path.read_text(encoding="utf-8")
    assert "memory_router" in content
    assert "include_router(memory_router" in content
