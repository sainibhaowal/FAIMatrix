"""Phase K4 acceptance: API keys management surface wiring."""

from __future__ import annotations

import pathlib
from uuid import uuid4

from fastapi.testclient import TestClient


def _mk_client(monkeypatch, tenant_keys_json: str):
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from runtime.config import reset_config

    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "true")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("TENANT_KEYS_JSON", tenant_keys_json)
    reset_config()
    reload_tenant_keys()
    return TestClient(create_app())


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


def test_k7_api_key_tenant_isolation(monkeypatch):
    client = _mk_client(
        monkeypatch,
        '{"tenant_pk4_a":["pk4_key_a"],"tenant_pk4_b":["pk4_key_b"]}',
    )

    headers_a = {"X-Tenant-Id": "tenant_pk4_a", "X-Api-Key": "pk4_key_a"}
    headers_b = {"X-Tenant-Id": "tenant_pk4_b", "X-Api-Key": "pk4_key_b"}

    created = client.post(
        "/api/v1/api-keys",
        headers=headers_a,
        json={"scopes": ["keys.read", "keys.write", "memory.read"]},
    )
    assert created.status_code == 200
    key_id = created.json()["key"]["key_id"]

    list_b = client.get("/api/v1/api-keys?include_revoked=true", headers=headers_b)
    assert list_b.status_code == 200
    key_ids_b = {item["key_id"] for item in list_b.json()["items"]}
    assert key_id not in key_ids_b

    revoke_b = client.post(
        f"/api/v1/api-keys/{key_id}/revoke",
        headers=headers_b,
        json={"reason": "cross-tenant check"},
    )
    assert revoke_b.status_code == 404

    rotate_b = client.post(
        f"/api/v1/api-keys/{key_id}/rotate",
        headers=headers_b,
        json={"reason": "cross-tenant check"},
    )
    assert rotate_b.status_code == 404


def test_k7_api_key_lifecycle_e2e(monkeypatch):
    tenant_id = f"tenant_pk4_{uuid4().hex[:8]}"
    bootstrap_key = "pk4_bootstrap_key"
    client = _mk_client(
        monkeypatch,
        f'{{"{tenant_id}":["{bootstrap_key}"]}}',
    )

    admin_headers = {"X-Tenant-Id": tenant_id, "X-Api-Key": bootstrap_key}

    created = client.post(
        "/api/v1/api-keys",
        headers=admin_headers,
        json={"scopes": ["keys.read", "keys.write", "memory.read", "memory.write"]},
    )
    assert created.status_code == 200
    created_body = created.json()
    first_key_id = created_body["key"]["key_id"]

    rotated = client.post(
        f"/api/v1/api-keys/{first_key_id}/rotate",
        headers=admin_headers,
        json={"reason": "k7-rotation"},
    )
    assert rotated.status_code == 200
    rotated_body = rotated.json()
    rotated_key_id = rotated_body["new_key"]["key_id"]
    rotated_plaintext = rotated_body["plaintext_key"]
    assert rotated_key_id != first_key_id

    revoke_new = client.post(
        f"/api/v1/api-keys/{rotated_key_id}/revoke",
        headers=admin_headers,
        json={"reason": "k7-revoke"},
    )
    assert revoke_new.status_code == 200

    audit = client.get("/api/v1/api-keys/audit?limit=100", headers=admin_headers)
    assert audit.status_code == 200
    actions = [item["action"] for item in audit.json()["items"]]
    assert "created" in actions
    assert "rotated" in actions
    assert "revoked" in actions

    # Revoked key must fail auth. Depending on local test DB wiring this can
    # surface as a specific revoked code or generic invalid credentials.
    revoked_headers = {"X-Tenant-Id": tenant_id, "X-Api-Key": rotated_plaintext}
    denied = client.get("/api/v1/api-keys", headers=revoked_headers)
    assert denied.status_code == 401
    assert denied.json().get("code") in {"auth_key_revoked", "auth_invalid"}
