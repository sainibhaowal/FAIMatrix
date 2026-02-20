"""Phase R7 acceptance: evolve matrix and memory idempotency consistency."""

from __future__ import annotations

import tempfile
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


def _mk_client(monkeypatch, *, compat_mode: str = "false") -> tuple[TestClient, dict]:
    tenant_id = f"tenant_r7_evolve_{uuid4().hex[:6]}"
    api_key = "r7_evolve_key"
    db_path = tempfile.gettempdir() + f"/faim_r7_evolve_{uuid4().hex}.db"
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
def test_r7_evolve_matrix_actions_timeline_and_scheduler_state(
    monkeypatch,
    profile,
    persist_mode,
    expected_durability,
):
    client, headers = _mk_client(monkeypatch, compat_mode="false")
    graph_id = f"r7-evolve-{profile}-{persist_mode}-{uuid4().hex[:8]}"

    evolve = client.post(
        "/api/v1/evolve",
        headers=headers,
        json={
            "graph_id": graph_id,
            "profile": profile,
            "persist_mode": persist_mode,
        },
    )
    assert evolve.status_code == 200, evolve.text
    body = evolve.json()

    assert body["status"] == "completed"
    assert body["requested_profile"] == profile
    assert body["requested_persist_mode"] == persist_mode
    assert body["effective_profile"] == profile
    assert body["effective_persist_mode"] == persist_mode
    assert body["durability_path"] == expected_durability
    assert body["completion_mode"] in {"sync_strict", "core_sync_state_best_effort"}
    assert body["state_update_status"] in {
        "completed_sync",
        "core_committed",
        "completed_best_effort",
        "best_effort_failed_nonfatal",
    }

    events = client.get(
        f"/api/v1/events?graph_id={graph_id}&after_seq=0&limit=250",
        headers=headers,
    )
    assert events.status_code == 200, events.text
    payload = events.json()
    target = next(
        (
            event
            for event in payload["events"]
            if event["kind"] in {"EVOLUTION_COMPLETE", "EVOLUTION_SKIPPED"}
        ),
        None,
    )
    assert target is not None
    event_payload = target["payload"]
    assert event_payload["requested_profile"] == profile
    assert event_payload["requested_persist_mode"] == persist_mode
    assert event_payload["effective_profile"] == profile
    assert event_payload["effective_persist_mode"] == persist_mode
    assert event_payload["durability_path"] == expected_durability

    status = client.get(
        f"/api/v1/evolve/status?graph_id={graph_id}&source=memory_write",
        headers=headers,
    )
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["graph_id"] == graph_id
    assert status_body["state"]["graph_id"] == graph_id
    assert status_body["state"]["last_evolved_at"] is not None
    assert status_body["runtime"]["jobs_enabled"] is True


def test_r7_memory_write_idempotency_consistency_unaffected(monkeypatch):
    client, headers = _mk_client(monkeypatch, compat_mode="false")
    graph_id = f"r7-memory-idem-{uuid4().hex[:8]}"
    idem_key = f"r7-idem-{uuid4().hex}"
    payload = {
        "graph_id": graph_id,
        "text": "phase-r7 memory idempotency payload",
        "filename": "r7-memory.txt",
        "content_type": "text/plain",
        "profile": "strict",
        "persist_mode": "relaxed",
        "idempotency_key": idem_key,
    }

    first = client.post("/api/v1/memory/write", headers=headers, json=payload)
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["status"] == "completed"
    assert first_body["idempotency_key"] == idem_key
    assert first_body["replayed"] is False
    assert first_body["requested_profile"] == "strict"
    assert first_body["requested_persist_mode"] == "relaxed"
    assert first_body["effective_profile"] == "strict"
    assert first_body["effective_persist_mode"] == "relaxed"
    assert first_body["durability_path"] == "core_sync_secondary_async"

    second = client.post("/api/v1/memory/write", headers=headers, json=payload)
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["status"] == "completed"
    assert second_body["idempotency_key"] == idem_key
    assert second_body["replayed"] is True
    assert second_body["raw_id"] == first_body["raw_id"]
    assert second_body["packet_hash"] == first_body["packet_hash"]
    assert second_body["requested_profile"] == first_body["requested_profile"]
    assert second_body["requested_persist_mode"] == first_body["requested_persist_mode"]
    assert second_body["effective_profile"] == first_body["effective_profile"]
    assert second_body["effective_persist_mode"] == first_body["effective_persist_mode"]
    assert second_body["durability_path"] == first_body["durability_path"]

