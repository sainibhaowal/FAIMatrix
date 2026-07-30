"""Phase K5 acceptance: memory API lifecycle behavior."""

from __future__ import annotations

from uuid import uuid4


def _mk_client(
    monkeypatch, tenant_id: str, api_key: str, database_url: str | None = None
):
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from fastapi.testclient import TestClient
    from runtime.config import reset_config

    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    if database_url:
        monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TENANT_KEYS_JSON", f'{{"{tenant_id}":["{api_key}"]}}')
    reset_config()
    reload_tenant_keys()

    app = create_app()
    return TestClient(app), {"X-Tenant-Id": tenant_id, "X-Api-Key": api_key}


def test_phase_k5_memory_write_search_get_provenance_patch(
    monkeypatch, tmp_path, db_session
):
    tenant_id = "tenant_pk5"
    graph_id = f"pk5-memory-{uuid4().hex[:8]}"
    db_path = tmp_path / f"pk5_{uuid4().hex}.db"
    client, headers = _mk_client(
        monkeypatch,
        tenant_id,
        "pk5_key",
        database_url=f"sqlite:///{db_path}",
    )

    try:
        write = client.post(
            "/api/v1/memory/write",
            headers={**headers, "Idempotency-Key": "idem-k5-1"},
            json={
                "graph_id": graph_id,
                "text": "FAIM memory lifecycle test content.",
                "filename": "memory.txt",
                "content_type": "text/plain",
                "profile": "strict",
                "persist_mode": "relaxed",
                "idempotency_key": "idem-k5-1",
            },
        )
        assert write.status_code == 200
        write_body = write.json()
        assert write_body["raw_id"]
        assert write_body["packet_hash"]
        assert write_body["idempotency_key"] == "idem-k5-1"
        assert write_body["replayed"] is False

        replay = client.post(
            "/api/v1/memory/write",
            headers={**headers, "Idempotency-Key": "idem-k5-1"},
            json={
                "graph_id": graph_id,
                "text": "FAIM memory lifecycle test content.",
                "filename": "memory.txt",
                "content_type": "text/plain",
                "profile": "strict",
                "persist_mode": "relaxed",
                "idempotency_key": "idem-k5-1",
            },
        )
        assert replay.status_code == 200
        replay_body = replay.json()
        assert replay_body["replayed"] is True
        assert replay_body["packet_hash"] == write_body["packet_hash"]

        search = client.post(
            "/api/v1/memory/search",
            headers=headers,
            json={
                "graph_id": graph_id,
                "query_text": "lifecycle test content",
                "k": 5,
                "profile": "strict",
                "return_explain": True,
            },
        )
        assert search.status_code == 200
        search_body = search.json()
        assert isinstance(search_body.get("results"), list)
        assert len(search_body["results"]) >= 1

        conflict = client.post(
            "/api/v1/memory/write",
            headers={**headers, "Idempotency-Key": "idem-k5-1"},
            json={
                "graph_id": graph_id,
                "text": "DIFFERENT CONTENT",
                "filename": "memory.txt",
                "content_type": "text/plain",
                "profile": "strict",
                "persist_mode": "relaxed",
                "idempotency_key": "idem-k5-1",
            },
        )
        assert conflict.status_code == 409

        storage_prov = client.get(
            f"/api/v1/storage/files/{write_body['raw_id']}/provenance?graph_id={graph_id}",
            headers=headers,
        )
        assert storage_prov.status_code == 200
        storage_prov_body = storage_prov.json()
        assert storage_prov_body["nodes"]
        node_id = storage_prov_body["nodes"][0]["node_id"]

        detail = client.get(
            f"/api/v1/memory/{node_id}?graph_id={graph_id}",
            headers=headers,
        )
        assert detail.status_code == 200
        detail_body = detail.json()
        assert detail_body["node_id"] == node_id

        provenance = client.get(
            f"/api/v1/memory/{node_id}/provenance?graph_id={graph_id}",
            headers=headers,
        )
        assert provenance.status_code == 200
        prov_body = provenance.json()
        assert prov_body["node"]["node_id"] == node_id
        assert "events" in prov_body

        patch = client.patch(
            f"/api/v1/memory/{node_id}",
            headers=headers,
            json={
                "graph_id": graph_id,
                "expected_updated_at": detail_body["updated_at"],
                "anchor": {"source": "pk5-test", "kind": "acceptance"},
            },
        )
        assert patch.status_code == 200
        patch_body = patch.json()
        assert patch_body["node_id"] == node_id
        assert patch_body["anchor"]["source"] == "pk5-test"
    finally:
        client.close()
