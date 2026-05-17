"""AT-CORTEX: structured Cortex turn route."""

from __future__ import annotations

import tempfile
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _mk_client(
    monkeypatch, *, compat_mode: str = "false"
) -> tuple[TestClient, dict, str]:
    tenant_id = f"tenant_cortex_{uuid4().hex[:6]}"
    api_key = "cortex_key"
    db_path = tempfile.gettempdir() + f"/faim_cortex_{uuid4().hex}.db"
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
    from sqlalchemy import create_engine
    from store.pg import session as pg_session
    from store.pg.models_faim import Base

    monkeypatch.setattr(pg_session, "DEFAULT_DATABASE_URL", db_url, raising=False)
    monkeypatch.setattr(pg_session, "_SESSION_FACTORY_CACHE", {}, raising=False)
    monkeypatch.setattr(runtime_context, "_engine", None, raising=False)
    monkeypatch.setattr(runtime_context, "_engine_db_url", None, raising=False)
    monkeypatch.setattr(runtime_context, "_SessionLocal", None, raising=False)
    monkeypatch.setattr(runtime_context, "_raw_store_plain", None, raising=False)
    monkeypatch.setattr(runtime_context, "_raw_store_by_tenant", {}, raising=False)

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    reset_config()
    reload_tenant_keys()

    client = TestClient(create_app())
    headers = {"X-Tenant-Id": tenant_id, "X-Api-Key": api_key}
    return client, headers, db_url


class _FakeQueryResult:
    tenant_id = "tenant"
    graph_id = "graph"
    graph_version = 1
    graph_hash = "gh"
    query_hash = "qh"
    profile = "RELAXED"
    duration_ms = 12.0
    results = [
        {
            "node_id": "n1",
            "vector_hash": "vh1",
            "score": 0.91,
            "score_components": {"sim": 0.9},
            "level": 0,
            "touch_count": 1,
            "temporal_status": "CURRENT",
            "evidence": {
                "raw_id": "raw-1",
                "block_id": "block-1",
                "anchor": {"filename": "atlas.txt", "page": 2},
            },
            "explain": {"node_id": "n1"},
        }
    ]
    answer = {
        "direct_answer": "Atlas lives in Berlin.",
        "supporting_spans": [
            {
                "node_id": "n1",
                "text": "Atlas lives in Berlin in 2026.",
                "score": 0.91,
                "temporal_status": "CURRENT",
            }
        ],
        "citations": [
            {
                "node_id": "n1",
                "raw_id": "raw-1",
                "block_id": "block-1",
                "anchor": {"filename": "atlas.txt", "page": 2},
                "score": 0.91,
            }
        ],
        "contradiction_notes": [],
        "confidence": 0.91,
        "provenance": {"query_hash": "qh", "graph_id": "graph", "span_count": 1},
        "quotes": ["Atlas lives in Berlin in 2026."],
    }
    metrics = {"node_count": 1, "avg_touch": 1.0}


def test_cortex_turn_returns_structured_brain_state(monkeypatch):
    client, headers, _ = _mk_client(monkeypatch)
    graph_id = f"cortex-{uuid4().hex[:8]}"

    monkeypatch.setattr("core.cortex.runtime.run_query", lambda **_: _FakeQueryResult())

    resp = client.post(
        "/api/v1/cortex/turn",
        headers=headers,
        json={
            "graph_id": graph_id,
            "query_text": "Where does Atlas live?",
            "session_id": "session-1",
            "answer_mode": "direct",
            "profile": "relaxed",
            "k": 5,
            "return_explain": True,
            "think_enabled": True,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["graph_id"] == graph_id
    assert body["session_id"] == "session-1"
    assert body["task_type"] == "answer"
    assert body["answer_mode"] == "direct"
    assert body["answer"]["direct_answer"] == "Atlas lives in Berlin."
    assert body["brain_state"]["active_facts"]
    assert body["brain_state"]["reasoning_tree"]
    assert body["brain_state"]["session_turn_count"] == 1
    assert body["brain_state"]["next_actions"]
    assert body["narrative"]
    assert "chain_of_thought" not in body
    assert "cot" not in body


def test_cortex_turn_uses_timeline_mode_without_raw_cot(monkeypatch):
    client, headers, _ = _mk_client(monkeypatch)
    graph_id = f"cortex-{uuid4().hex[:8]}"

    monkeypatch.setattr("core.cortex.runtime.run_query", lambda **_: _FakeQueryResult())

    resp = client.post(
        "/api/v1/cortex/turn",
        headers=headers,
        json={
            "graph_id": graph_id,
            "query_text": "Give me the timeline.",
            "session_id": "session-2",
            "answer_mode": "timeline",
            "profile": "relaxed",
            "k": 5,
            "return_explain": True,
            "think_enabled": False,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["task_type"] == "timeline"
    assert body["brain_state"]["task_type"] == "timeline"
    assert body["brain_state"]["reasoning_tree"][1]["branch"] == "timeline"
    assert body["brain_state"]["session_turn_count"] == 1
    assert "chain_of_thought" not in body["brain_state"]


def test_cortex_turn_persists_structured_state(monkeypatch):
    client, headers, db_url = _mk_client(monkeypatch)
    graph_id = f"cortex-{uuid4().hex[:8]}"

    monkeypatch.setattr("core.cortex.runtime.run_query", lambda **_: _FakeQueryResult())

    resp = client.post(
        "/api/v1/cortex/turn",
        headers=headers,
        json={
            "graph_id": graph_id,
            "query_text": "Where does Atlas live?",
            "session_id": "session-3",
            "answer_mode": "direct",
            "profile": "relaxed",
            "k": 5,
            "return_explain": True,
            "think_enabled": True,
        },
    )
    assert resp.status_code == 200, resp.text

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        from store.pg.models_faim import (
            CortexReasoningNodeModel,
            CortexSessionModel,
            CortexTurnModel,
            CortexWritebackCandidateModel,
        )

        session_row = (
            session.query(CortexSessionModel)
            .filter(
                CortexSessionModel.tenant_id == headers["X-Tenant-Id"],
                CortexSessionModel.graph_id == graph_id,
                CortexSessionModel.session_id == "session-3",
            )
            .first()
        )
        assert session_row is not None
        assert session_row.turn_count == 1
        assert session_row.last_turn_id

        turn_row = (
            session.query(CortexTurnModel)
            .filter_by(turn_id=resp.json()["turn_id"])
            .first()
        )
        assert turn_row is not None
        assert turn_row.brain_state_json["goal"]

        reasoning_rows = (
            session.query(CortexReasoningNodeModel)
            .filter_by(turn_id=resp.json()["turn_id"])
            .all()
        )
        assert len(reasoning_rows) == 7

        writeback_rows = (
            session.query(CortexWritebackCandidateModel)
            .filter_by(turn_id=resp.json()["turn_id"])
            .all()
        )
        assert writeback_rows
    finally:
        session.close()


def test_cortex_session_list_and_turn_history(monkeypatch):
    client, headers, _ = _mk_client(monkeypatch)
    graph_id = f"cortex-{uuid4().hex[:8]}"

    monkeypatch.setattr("core.cortex.runtime.run_query", lambda **_: _FakeQueryResult())

    first = client.post(
        "/api/v1/cortex/turn",
        headers=headers,
        json={
            "graph_id": graph_id,
            "query_text": "Where does Atlas live?",
            "session_id": "session-history",
            "answer_mode": "direct",
            "profile": "relaxed",
            "k": 5,
            "return_explain": True,
            "think_enabled": True,
        },
    )
    assert first.status_code == 200, first.text

    second = client.post(
        "/api/v1/cortex/turn",
        headers=headers,
        json={
            "graph_id": graph_id,
            "query_text": "Give me the timeline.",
            "session_id": "session-history",
            "answer_mode": "timeline",
            "profile": "relaxed",
            "k": 5,
            "return_explain": True,
            "think_enabled": False,
        },
    )
    assert second.status_code == 200, second.text

    sessions = client.get(
        f"/api/v1/cortex/sessions?graph_id={graph_id}&limit=5",
        headers=headers,
    )
    assert sessions.status_code == 200, sessions.text
    sessions_body = sessions.json()
    assert sessions_body["total"] == 1
    assert sessions_body["items"][0]["session_id"] == "session-history"
    assert sessions_body["items"][0]["turn_count"] == 2

    turns = client.get(
        f"/api/v1/cortex/sessions/session-history/turns?graph_id={graph_id}&limit=5",
        headers=headers,
    )
    assert turns.status_code == 200, turns.text
    turns_body = turns.json()
    assert turns_body["total"] == 2
    assert turns_body["items"][0]["query_text"] == "Where does Atlas live?"
    assert turns_body["items"][1]["query_text"] == "Give me the timeline."
