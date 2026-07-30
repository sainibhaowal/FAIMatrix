"""Acceptance: FIG interaction pulse writes to the event journal."""

from __future__ import annotations

import tempfile
from uuid import uuid4

from fastapi.testclient import TestClient


def _configure_isolated_runtime(monkeypatch, tenant_keys_json: str) -> None:
    db_path = tempfile.gettempdir() + f"/faim_fig_interaction_{uuid4().hex}.db"
    db_url = f"sqlite:///{db_path}"

    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("TENANT_KEYS_JSON", tenant_keys_json)
    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")

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


def _mk_client(monkeypatch) -> tuple[TestClient, dict, str]:
    tenant_id = f"tenant_fig_interaction_{uuid4().hex[:6]}"
    api_key = "fig_interaction_key"

    _configure_isolated_runtime(
        monkeypatch,
        f'{{"{tenant_id}":["{api_key}"]}}',
    )

    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys

    reload_tenant_keys()

    client = TestClient(create_app())
    headers = {"X-Tenant-Id": tenant_id, "X-Api-Key": api_key}
    return client, headers, tenant_id


def test_fig_interaction_pulse_is_journaled(monkeypatch):
    client, headers, tenant_id = _mk_client(monkeypatch)
    graph_id = f"graph_fig_{uuid4().hex[:8]}"

    payload = {
        "pulse": {
            "protocol": "pulse-v2",
            "trace_id": "ui-test-trace",
            "graph_id": graph_id,
            "node_id": "node-1",
            "selected_node_id": "node-1",
            "hovered_node_id": None,
            "overlay_mode": "cognitive",
            "top_mode": "analyze",
            "active_drawer": "inspector",
            "timeline_step_idx": 2,
            "active_layers": ["ui_selection", "ui_overlay"],
            "confidence": 0.92,
            "event_count": 2,
            "source_summary": {"source:fig:selected": 1},
            "why_glowing": {"ui_context": {"graph_id": graph_id}},
            "events": [],
            "ui_context": {
                "graph_id": graph_id,
                "selected_node_id": "node-1",
                "overlay_mode": "cognitive",
            },
            "ui_events": [],
        }
    }

    resp = client.post(
        f"/api/v1/events/fig-interaction?graph_id={graph_id}",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["stored"] is True
    assert body["protocol"] == "pulse-v2"
    assert body["graph_id"] == graph_id
    assert body["tenant_id"] == tenant_id
    assert body["seq"] is not None

    listed = client.get(
        f"/api/v1/events?graph_id={graph_id}&after_seq=0&limit=10",
        headers=headers,
    )
    assert listed.status_code == 200
    events = listed.json()["events"]
    assert events[-1]["kind"] == "FIG_INTERACTION"
    assert events[-1]["payload"]["protocol"] == "pulse-v2"
    assert events[-1]["payload"]["ui_context"]["graph_id"] == graph_id
