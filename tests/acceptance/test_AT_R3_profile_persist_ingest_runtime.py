"""Phase R3 acceptance: ingest/runtime profile-persist semantics."""

from __future__ import annotations

import base64
import tempfile
from uuid import UUID, uuid4

from fastapi.testclient import TestClient


def _mk_client(monkeypatch, *, compat_mode: str = "false") -> tuple[TestClient, dict]:
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from runtime.config import reset_config

    tenant_id = f"tenant_r3_{uuid4().hex[:6]}"
    api_key = "r3_key"

    monkeypatch.setenv("TENANT_KEYS_JSON", f'{{"{tenant_id}":["{api_key}"]}}')
    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true")
    monkeypatch.setenv("FAIM_PROFILE_PERSIST_COMPAT_MODE", compat_mode)
    
    reset_config()
    reload_tenant_keys()
    client = TestClient(create_app())
    headers = {"X-Tenant-Id": tenant_id, "X-Api-Key": api_key}
    return client, headers


def test_r3_ingest_relaxed_queues_secondary_index_job(monkeypatch, db_session):
    from runtime.context import get_session
    from store.pg.models_faim import JobModel
    from store.pg.session import SessionFactory
    from store.pg.models_faim import create_all_tables

    client, headers = _mk_client(monkeypatch, compat_mode="false")
    graph_id = f"r3-graph-{uuid4().hex[:8]}"

    resp = client.post(
        "/api/v1/ingest",
        headers=headers,
        json={
            "graph_id": graph_id,
            "filename": "r3-runtime.txt",
            "bytes_base64": base64.b64encode(b"r3 runtime ingest payload").decode(),
            "content_type": "text/plain",
            "profile": "fast",
            "persist_mode": "relaxed",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["status"] == "completed"
    assert body["requested_profile"] == "fast"
    assert body["requested_persist_mode"] == "relaxed"
    assert body["effective_profile"] == "fast"
    assert body["effective_persist_mode"] == "relaxed"
    assert body["durability_path"] == "core_sync_secondary_async"
    assert body["index_write_mode"] == "async_queued"
    assert body["secondary_task_status"] == "queued"
    assert body["secondary_task_job_id"]

    job_id = UUID(body["secondary_task_job_id"])
    session = get_session()
    try:
        job = session.query(JobModel).filter(JobModel.job_id == job_id).first()
        assert job is not None
        assert job.kind == "ingest_secondary_index"
        assert job.status == "pending"
        payload = job.payload_json or {}
        assert payload.get("effective_profile") == "fast"
        assert payload.get("effective_persist_mode") == "relaxed"
        assert payload.get("durability_path") == "core_sync_secondary_async"
    finally:
        session.close()


def test_r3_ingest_strict_profile_reports_sync_strict_path(monkeypatch, db_session):
    client, headers = _mk_client(monkeypatch, compat_mode="false")
    graph_id = f"r3-graph-{uuid4().hex[:8]}"

    resp = client.post(
        "/api/v1/ingest",
        headers=headers,
        json={
            "graph_id": graph_id,
            "filename": "r3-strict.txt",
            "bytes_base64": base64.b64encode(b"r3 strict profile payload").decode(),
            "content_type": "text/plain",
            "profile": "strict",
            "persist_mode": "strict",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["status"] == "completed"
    assert body["requested_profile"] == "strict"
    assert body["requested_persist_mode"] == "strict"
    assert body["effective_profile"] == "strict"
    assert body["effective_persist_mode"] == "strict"
    assert body["durability_path"] == "sync_strict"
    assert body["index_write_mode"] == "skipped_profile_strict"
    assert body["secondary_task_status"] == "skipped_profile_strict"
    assert body["secondary_task_job_id"] is None
