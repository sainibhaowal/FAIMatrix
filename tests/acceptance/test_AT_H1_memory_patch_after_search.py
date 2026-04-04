"""AT-H1: regression guard for memory patch after search usage updates.

Ensures query/search write-side usage tracking does not leave stale locks that
block subsequent memory patch operations in the same graph lifecycle.
"""

from __future__ import annotations

from uuid import uuid4


def _mk_client(monkeypatch, tenant_id: str, api_key: str, database_url: str):
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from fastapi.testclient import TestClient
    from runtime.config import reset_config

    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_ENABLED", "false")
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "false")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TENANT_KEYS_JSON", f'{{"{tenant_id}":["{api_key}"]}}')
    reset_config()
    reload_tenant_keys()

    app = create_app()
    return TestClient(app), {"X-Tenant-Id": tenant_id, "X-Api-Key": api_key}


def test_memory_patch_after_search_does_not_lock(monkeypatch, tmp_path):
    tenant_id = "tenant_h1"
    graph_id = f"h1-memory-{uuid4().hex[:8]}"
    db_path = tmp_path / f"h1_{uuid4().hex}.db"
    client, headers = _mk_client(
        monkeypatch,
        tenant_id,
        "h1_key",
        database_url=f"sqlite:///{db_path}",
    )

    try:
        write = client.post(
            "/api/v1/memory/write",
            headers={**headers, "Idempotency-Key": "idem-h1-1"},
            json={
                "graph_id": graph_id,
                "text": "Regression memory content for H1.",
                "filename": "h1.txt",
                "content_type": "text/plain",
                "profile": "strict",
                "persist_mode": "relaxed",
                "idempotency_key": "idem-h1-1",
            },
        )
        assert write.status_code == 200
        raw_id = write.json()["raw_id"]

        search = client.post(
            "/api/v1/memory/search",
            headers=headers,
            json={
                "graph_id": graph_id,
                "query_text": "Regression memory content",
                "k": 5,
                "profile": "strict",
                "return_explain": True,
            },
        )
        assert search.status_code == 200

        storage_prov = client.get(
            f"/api/v1/storage/files/{raw_id}/provenance?graph_id={graph_id}",
            headers=headers,
        )
        assert storage_prov.status_code == 200
        node_id = storage_prov.json()["nodes"][0]["node_id"]

        detail = client.get(
            f"/api/v1/memory/{node_id}?graph_id={graph_id}",
            headers=headers,
        )
        assert detail.status_code == 200

        patch = client.patch(
            f"/api/v1/memory/{node_id}",
            headers=headers,
            json={
                "graph_id": graph_id,
                "expected_updated_at": detail.json()["updated_at"],
                "anchor": {"source": "h1-test", "kind": "regression"},
            },
        )
        assert patch.status_code == 200
        assert patch.json()["anchor"]["source"] == "h1-test"
    finally:
        client.close()

