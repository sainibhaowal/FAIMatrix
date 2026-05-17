"""Phase R7 acceptance: storage upload matrix for profile/persist semantics."""

from __future__ import annotations

import tempfile
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


def _mk_client(monkeypatch, *, compat_mode: str = "false") -> tuple[TestClient, dict]:
    tenant_id = f"tenant_r7_storage_{uuid4().hex[:6]}"
    api_key = "r7_storage_key"
    db_path = tempfile.gettempdir() + f"/faim_r7_storage_{uuid4().hex}.db"
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

    # Keep acceptance tests deterministic and independent of external vector infra.
    monkeypatch.setattr(
        "orchestration.ingest_flow._upsert_index_sync",
        lambda **kwargs: len(kwargs.get("vectors", [])),
    )

    reset_config()
    reload_tenant_keys()

    client = TestClient(create_app())
    headers = {"X-Tenant-Id": tenant_id, "X-Api-Key": api_key}
    return client, headers


@pytest.mark.parametrize(
    "profile,persist_mode,expected_durability",
    [
        ("strict", "strict", "sync_strict"),
        ("strict", "relaxed", "core_sync_secondary_async"),
        ("fast", "strict", "sync_strict"),
        ("fast", "relaxed", "core_sync_secondary_async"),
        ("relaxed", "strict", "sync_strict"),
        ("relaxed", "relaxed", "core_sync_secondary_async"),
    ],
)
def test_r7_storage_upload_matrix_requested_effective_and_events(
    monkeypatch,
    profile,
    persist_mode,
    expected_durability,
):
    client, headers = _mk_client(monkeypatch, compat_mode="false")
    graph_id = f"r7-storage-{profile}-{persist_mode}-{uuid4().hex[:8]}"
    file_bytes = f"phase-r7-storage-{profile}-{persist_mode}".encode()

    upload = client.post(
        "/api/v1/storage/uploads",
        headers=headers,
        data={
            "graph_id": graph_id,
            "profile": profile,
            "persist_mode": persist_mode,
        },
        files=[("files", (f"{profile}-{persist_mode}.txt", file_bytes, "text/plain"))],
    )
    assert upload.status_code == 200, upload.text
    body = upload.json()

    assert body["requested_profile"] == profile
    assert body["requested_persist_mode"] == persist_mode
    assert body["effective_profile"] == profile
    assert body["effective_persist_mode"] == persist_mode
    assert body["durability_path"] == expected_durability
    assert body["files"], "expected file-level results"
    first = body["files"][0]
    assert first["requested_profile"] == profile
    assert first["requested_persist_mode"] == persist_mode
    assert first["effective_profile"] == profile
    assert first["effective_persist_mode"] == persist_mode
    assert first["durability_path"] == expected_durability
    assert first["status"] in {"ingested", "dedup_hit"}

    status = client.get(f"/api/v1/storage/uploads/{body['job_id']}", headers=headers)
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["requested_profile"] == profile
    assert status_body["requested_persist_mode"] == persist_mode
    assert status_body["effective_profile"] == profile
    assert status_body["effective_persist_mode"] == persist_mode
    assert status_body["durability_path"] == expected_durability

    events = client.get(
        f"/api/v1/storage/uploads/{body['job_id']}/events", headers=headers
    )
    assert events.status_code == 200, events.text
    events_body = events.json()
    assert events_body["events"], "expected upload job events"
    enriched = next(
        (
            event
            for event in events_body["events"]
            if isinstance(event.get("payload"), dict)
            and event["payload"].get("effective_profile") == profile
            and event["payload"].get("effective_persist_mode") == persist_mode
            and event["payload"].get("durability_path") == expected_durability
        ),
        None,
    )
    assert (
        enriched is not None
    ), "expected mode metadata in at least one job event payload"
