"""Phase B acceptance: raw re-encryption visibility in maintenance history."""

from __future__ import annotations

from uuid import uuid4


def _mk_client(monkeypatch, tenant_id: str, api_key: str):
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from fastapi.testclient import TestClient
    from runtime.config import reset_config

    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("TENANT_KEYS_JSON", f'{{"{tenant_id}":["{api_key}"]}}')
    reset_config()
    reload_tenant_keys()

    app = create_app()
    return TestClient(app), {"X-Tenant-Id": tenant_id, "X-Api-Key": api_key}


def test_raw_reencryption_appears_in_maintenance_history(monkeypatch):
    from runtime.context import close_session, get_repos

    tenant_id = "tenant_raw_reencryption_history"
    graph_id = f"graph-raw-reencryption-history-{uuid4().hex[:8]}"
    client, headers = _mk_client(monkeypatch, tenant_id, "raw_reencryption_history_key")

    repos = get_repos(tenant_id)
    session = repos["session"]
    try:
        repos["event_repo"].emit(
            session,
            graph_id,
            "RAW_REENCRYPTION",
            {
                "status": "completed",
                "scanned": 2,
                "already_encrypted": 1,
                "reencrypted": 1,
                "failed": 0,
            },
        )
        session.commit()
    finally:
        close_session(session)

    history = client.get(
        f"/api/v1/storage/maintenance/history?graph_id={graph_id}&limit=10",
        headers=headers,
    )
    assert history.status_code == 200, history.text
    body = history.json()
    assert body["graph_id"] == graph_id
    assert body["total"] == 1
    assert body["items"][0]["kind"] == "RAW_REENCRYPTION"
    assert "raw re-encryption" in body["items"][0]["summary"]
    assert body["items"][0]["payload"]["reencrypted"] == 1
