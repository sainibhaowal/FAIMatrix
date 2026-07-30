"""Phase R4 acceptance: evolve/runtime profile-persist semantics."""

from __future__ import annotations

import tempfile
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


def _mk_client(monkeypatch, *, compat_mode: str = "false") -> tuple[TestClient, dict]:
    tenant_id = f"tenant_r4_{uuid4().hex[:6]}"
    api_key = "r4_key"

    db_path = tempfile.gettempdir() + f"/faim_r4_{uuid4().hex}.db"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
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


def test_r4_evolve_relaxed_exposes_effective_runtime_and_events(monkeypatch):
    client, headers = _mk_client(monkeypatch, compat_mode="false")
    graph_id = f"r4-graph-{uuid4().hex[:8]}"

    evolve = client.post(
        "/api/v1/evolve",
        headers=headers,
        json={"graph_id": graph_id, "profile": "relaxed", "persist_mode": "relaxed"},
    )
    assert evolve.status_code == 200, evolve.text

    body = evolve.json()
    assert body["status"] == "completed"
    assert body["requested_profile"] == "relaxed"
    assert body["requested_persist_mode"] == "relaxed"
    assert body["effective_profile"] == "relaxed"
    assert body["effective_persist_mode"] == "relaxed"
    assert body["durability_path"] == "core_sync_secondary_async"
    assert body["completion_mode"] == "core_sync_state_best_effort"
    assert body["state_update_status"] in {
        "completed_best_effort",
        "best_effort_failed_nonfatal",
    }

    events = client.get(
        f"/api/v1/events?graph_id={graph_id}&after_seq=0&limit=120",
        headers=headers,
    )
    assert events.status_code == 200, events.text
    payload = events.json()
    start = next((e for e in payload["events"] if e["kind"] == "EVOLUTION_START"), None)
    assert start is not None
    start_payload = start["payload"]
    assert start_payload["effective_profile"] == "relaxed"
    assert start_payload["effective_persist_mode"] == "relaxed"
    assert start_payload["evolve_action_budget_scale"] == pytest.approx(1.0)
    assert start_payload["evolve_merge_threshold"] == pytest.approx(0.92)

    persistence = next(
        (e for e in payload["events"] if e["kind"] == "EVOLUTION_PERSISTENCE_APPLIED"),
        None,
    )
    assert persistence is not None


def test_r4_evolve_strict_updates_scheduler_state(monkeypatch):
    client, headers = _mk_client(monkeypatch, compat_mode="false")
    graph_id = f"r4-graph-{uuid4().hex[:8]}"

    evolve = client.post(
        "/api/v1/evolve",
        headers=headers,
        json={"graph_id": graph_id, "profile": "strict", "persist_mode": "strict"},
    )
    assert evolve.status_code == 200, evolve.text
    body = evolve.json()

    assert body["status"] == "completed"
    assert body["requested_profile"] == "strict"
    assert body["effective_profile"] == "strict"
    assert body["requested_persist_mode"] == "strict"
    assert body["effective_persist_mode"] == "strict"
    assert body["durability_path"] == "sync_strict"
    assert body["completion_mode"] == "sync_strict"
    assert body["state_update_status"] == "completed_sync"

    status = client.get(
        f"/api/v1/evolve/status?graph_id={graph_id}&source=memory_write",
        headers=headers,
    )
    assert status.status_code == 200, status.text
    status_body = status.json()
    assert status_body["state"]["graph_id"] == graph_id
    assert status_body["state"]["last_evolved_at"] is not None
