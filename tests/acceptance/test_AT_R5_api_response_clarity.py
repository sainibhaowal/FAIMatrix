"""Phase R5 acceptance: requested/effective profile-persist API clarity."""

from __future__ import annotations

import base64
import tempfile
from uuid import uuid4

from fastapi.testclient import TestClient


def _mk_client(monkeypatch, *, compat_mode: str = "false") -> tuple[TestClient, dict]:
    tenant_id = f"tenant_r5_{uuid4().hex[:6]}"
    api_key = "r5_key"
    db_path = tempfile.gettempdir() + f"/faim_r5_{uuid4().hex}.db"
    db_url = f"sqlite:///{db_path}"

    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("TENANT_KEYS_JSON", f'{{"{tenant_id}":["{api_key}"]}}')
    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true")
    monkeypatch.setenv("FAIM_PROFILE_PERSIST_COMPAT_MODE", compat_mode)

    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from runtime import context as runtime_context
    from runtime.config import reset_config
    from store.pg import session as pg_session

    monkeypatch.setattr(pg_session, "DEFAULT_DATABASE_URL", db_url, raising=False)
    monkeypatch.setattr(pg_session, "_SESSION_FACTORY_CACHE", {}, raising=False)
    monkeypatch.setattr(runtime_context, "_engine", None, raising=False)
    monkeypatch.setattr(runtime_context, "_engine_db_url", None, raising=False)
    monkeypatch.setattr(runtime_context, "_SessionLocal", None, raising=False)
    monkeypatch.setattr(runtime_context, "_raw_store_plain", None, raising=False)
    monkeypatch.setattr(runtime_context, "_raw_store_by_tenant", {}, raising=False)

    reset_config()
    reload_tenant_keys()

    client = TestClient(create_app())
    headers = {"X-Tenant-Id": tenant_id, "X-Api-Key": api_key}
    return client, headers


def test_r5_ingest_response_includes_requested_effective_fields(monkeypatch):
    client, headers = _mk_client(monkeypatch)
    graph_id = f"r5-ingest-{uuid4().hex[:8]}"

    resp = client.post(
        "/api/v1/ingest",
        headers=headers,
        json={
            "graph_id": graph_id,
            "filename": "r5-ingest.txt",
            "bytes_base64": base64.b64encode(b"r5 ingest payload").decode(),
            "content_type": "text/plain",
            "profile": "fast",
            "persist_mode": "relaxed",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["requested_profile"] == "fast"
    assert body["requested_persist_mode"] == "relaxed"
    assert body["effective_profile"] == "fast"
    assert body["effective_persist_mode"] == "relaxed"
    assert body["durability_path"] == "core_sync_secondary_async"


def test_r5_memory_write_completed_event_includes_mode_fields(monkeypatch):
    client, headers = _mk_client(monkeypatch)
    graph_id = f"r5-memory-{uuid4().hex[:8]}"

    write = client.post(
        "/api/v1/memory/write",
        headers=headers,
        json={
            "graph_id": graph_id,
            "text": "r5 memory write payload",
            "filename": "r5-memory.txt",
            "content_type": "text/plain",
            "profile": "fast",
            "persist_mode": "relaxed",
            "idempotency_key": f"r5-memory-{uuid4().hex}",
        },
    )
    assert write.status_code == 200, write.text
    write_body = write.json()
    assert write_body["requested_profile"] == "fast"
    assert write_body["effective_profile"] == "fast"

    events = client.get(
        f"/api/v1/events?graph_id={graph_id}&after_seq=0&limit=200",
        headers=headers,
    )
    assert events.status_code == 200, events.text
    payload = events.json()
    completed = next(
        (e for e in payload["events"] if e["kind"] == "MEMORY_WRITE_COMPLETED"),
        None,
    )
    assert completed is not None
    completed_payload = completed["payload"]
    assert completed_payload["requested_profile"] == "fast"
    assert completed_payload["requested_persist_mode"] == "relaxed"
    assert completed_payload["effective_profile"] == "fast"
    assert completed_payload["effective_persist_mode"] == "relaxed"
    assert completed_payload["durability_path"] == "core_sync_secondary_async"


def test_r5_storage_upload_batch_and_status_include_mode_fields(monkeypatch):
    client, headers = _mk_client(monkeypatch)
    graph_id = f"r5-storage-{uuid4().hex[:8]}"

    form = {"graph_id": graph_id, "profile": "fast", "persist_mode": "relaxed"}
    files = [("files", ("r5-storage.txt", b"r5 storage payload", "text/plain"))]
    upload = client.post(
        "/api/v1/storage/uploads", headers=headers, data=form, files=files
    )
    assert upload.status_code == 200, upload.text
    body = upload.json()

    assert body["requested_profile"] == "fast"
    assert body["requested_persist_mode"] == "relaxed"
    assert body["effective_profile"] == "fast"
    assert body["effective_persist_mode"] == "relaxed"
    assert body["durability_path"] == "core_sync_secondary_async"
    assert body["files"], "expected per-file upload results"
    first = body["files"][0]
    assert first["requested_profile"] == "fast"
    assert first["requested_persist_mode"] == "relaxed"
    assert first["effective_profile"] == "fast"
    assert first["effective_persist_mode"] == "relaxed"
    assert first["durability_path"] == "core_sync_secondary_async"

    status = client.get(f"/api/v1/storage/uploads/{body['job_id']}", headers=headers)
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["requested_profile"] == "fast"
    assert status_body["requested_persist_mode"] == "relaxed"
    assert status_body["effective_profile"] == "fast"
    assert status_body["effective_persist_mode"] == "relaxed"
    assert status_body["durability_path"] == "core_sync_secondary_async"


def test_r5_evolve_complete_or_skipped_event_includes_mode_fields(monkeypatch):
    client, headers = _mk_client(monkeypatch)
    graph_id = f"r5-evolve-{uuid4().hex[:8]}"

    evolve = client.post(
        "/api/v1/evolve",
        headers=headers,
        json={"graph_id": graph_id, "profile": "relaxed", "persist_mode": "relaxed"},
    )
    assert evolve.status_code == 200, evolve.text
    body = evolve.json()
    assert body["requested_profile"] == "relaxed"
    assert body["requested_persist_mode"] == "relaxed"
    assert body["effective_profile"] == "relaxed"
    assert body["effective_persist_mode"] == "relaxed"
    assert body["durability_path"] == "core_sync_secondary_async"

    events = client.get(
        f"/api/v1/events?graph_id={graph_id}&after_seq=0&limit=200",
        headers=headers,
    )
    assert events.status_code == 200, events.text
    payload = events.json()
    target = next(
        (
            e
            for e in payload["events"]
            if e["kind"] in {"EVOLUTION_COMPLETE", "EVOLUTION_SKIPPED"}
        ),
        None,
    )
    assert target is not None
    event_payload = target["payload"]
    assert event_payload["requested_profile"] == "relaxed"
    assert event_payload["requested_persist_mode"] == "relaxed"
    assert event_payload["effective_profile"] == "relaxed"
    assert event_payload["effective_persist_mode"] == "relaxed"
    assert event_payload["durability_path"] == "core_sync_secondary_async"
