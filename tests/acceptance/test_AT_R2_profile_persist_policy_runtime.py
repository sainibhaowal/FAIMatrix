"""Phase R2 acceptance: centralized profile/persist policy runtime wiring."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def _mk_client(monkeypatch, *, compat_mode: str = "true") -> tuple[TestClient, dict]:
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from runtime.config import reset_config

    tenant_id = f"tenant_r2_{uuid4().hex[:6]}"
    api_key = "r2_key"

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
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


def test_r2_evolve_emits_requested_and_effective_modes(monkeypatch):
    from orchestration import evolve_flow

    captured: list[tuple[str, dict]] = []

    def _capture(
        event_type, _graph_id, payload, event_repo=None, session=None
    ):  # noqa: ARG001
        captured.append((event_type, payload))

    monkeypatch.setattr(evolve_flow, "_emit_event", _capture)

    client, headers = _mk_client(monkeypatch, compat_mode="true")
    graph_id = f"r2-graph-{uuid4().hex[:8]}"

    evolve = client.post(
        "/api/v1/evolve",
        headers=headers,
        json={"graph_id": graph_id, "profile": "fast", "persist_mode": "strict"},
    )
    assert evolve.status_code == 200, evolve.text

    start = next((item for item in captured if item[0] == "EVOLUTION_START"), None)
    assert start is not None
    payload = start[1]
    assert payload["requested_profile"] == "fast"
    assert payload["requested_persist_mode"] == "strict"
    assert payload["effective_profile"] == "fast"
    assert payload["effective_persist_mode"] == "strict"
    assert payload["profile_persist_compat_mode"] is True


def test_r2_evolve_reports_compat_mode_off(monkeypatch):
    from orchestration import evolve_flow

    captured: list[tuple[str, dict]] = []

    def _capture(
        event_type, _graph_id, payload, event_repo=None, session=None
    ):  # noqa: ARG001
        captured.append((event_type, payload))

    monkeypatch.setattr(evolve_flow, "_emit_event", _capture)

    client, headers = _mk_client(monkeypatch, compat_mode="false")
    graph_id = f"r2-graph-{uuid4().hex[:8]}"

    evolve = client.post(
        "/api/v1/evolve",
        headers=headers,
        json={"graph_id": graph_id, "profile": "strict", "persist_mode": "relaxed"},
    )
    assert evolve.status_code == 200, evolve.text

    start = next((item for item in captured if item[0] == "EVOLUTION_START"), None)
    assert start is not None
    assert start[1]["profile_persist_compat_mode"] is False
