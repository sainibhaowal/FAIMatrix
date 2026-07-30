from __future__ import annotations

from fastapi.testclient import TestClient


def test_admin_routes_are_not_mounted(monkeypatch):
    from api.app import create_app
    from api.middleware import auth as auth_module
    from runtime.config import reset_config

    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_a":["tenant_key"]}')
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")
    monkeypatch.setattr(
        auth_module,
        "authenticate_tenant_key",
        lambda tenant_id, api_key, request_id=None: auth_module.AuthDecision(
            valid=True,
            auth_method="api_key_db",
            key_id="faim_k_test",
            scopes=["keys.read"],
        ),
    )
    reset_config()

    app = create_app()
    client = TestClient(app)

    response = client.get(
        "/api/v1/admin/status",
        headers={"X-Tenant-Id": "tenant_a", "X-Api-Key": "tenant_key"},
    )
    assert response.status_code == 404
