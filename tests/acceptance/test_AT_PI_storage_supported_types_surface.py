"""Phase I acceptance: supported file coverage endpoint surface."""

from __future__ import annotations


def _mk_client(monkeypatch, tenant_id: str, api_key: str):
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from fastapi.testclient import TestClient
    from runtime.config import reset_config

    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("TENANT_KEYS_JSON", f'{{"{tenant_id}":["{api_key}"]}}')
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    reset_config()
    reload_tenant_keys()

    app = create_app()
    return TestClient(app), {"X-Tenant-Id": tenant_id, "X-Api-Key": api_key}


def test_supported_types_endpoint_returns_expected_contract(monkeypatch):
    client, headers = _mk_client(
        monkeypatch, "tenant_pi_supported_types", "pi_types_key"
    )

    response = client.get("/api/v1/storage/supported-types", headers=headers)
    assert response.status_code == 200

    body = response.json()
    assert body["total_extensions"] >= 1
    assert body["total_content_types"] >= 1
    assert body["max_upload_size_bytes"] >= 1
    assert body["max_upload_size_mb"] > 0

    assert ".pdf" in body["extensions"]
    assert "application/pdf" in body["content_types"]
    assert "documents" in body["categories"]
    assert "images" in body["categories"]

    assert "ocr_enabled" in body
    assert "ocr_engine" in body
    assert "ocr_fail_closed" in body
    assert ".pdf" in body["ocr_capable_extensions"]
    assert "docnative_enabled" in body
    assert "docnative_available" in body
