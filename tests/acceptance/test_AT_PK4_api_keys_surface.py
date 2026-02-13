"""Phase K4 acceptance: API keys management surface wiring."""

from __future__ import annotations

import pathlib


def test_phase_k4_api_keys_routes_present():
    from api.routers.api_keys import router

    paths = {route.path for route in router.routes}
    assert "/api-keys" in paths
    assert "/api-keys/{key_id}/rotate" in paths
    assert "/api-keys/{key_id}/revoke" in paths
    assert "/api-keys/audit" in paths


def test_phase_k4_app_includes_api_keys_router():
    app_path = pathlib.Path("faim_native/api/app.py")
    content = app_path.read_text(encoding="utf-8")
    assert "api_keys_router" in content
    assert "include_router(api_keys_router" in content


def test_phase_k4_ratelimit_category_present():
    from api.middleware.ratelimit import ENDPOINT_CATEGORIES

    assert ENDPOINT_CATEGORIES.get("/api/v1/api-keys") == "api_keys"
