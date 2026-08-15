"""AT-REASON: reasoning router endpoints (traverse, plan, feedback, synthesize, stats).

Also verifies the feedback loop writes REAL turn context (query_text,
reasoning_path, answer_given) instead of placeholder values.
"""

from __future__ import annotations

import tempfile
from uuid import uuid4

from fastapi.testclient import TestClient


def _mk_client(
    monkeypatch,
) -> tuple[TestClient, dict, str]:
    tenant_id = f"tenant_reason_{uuid4().hex[:6]}"
    api_key = "reason_key"
    db_path = tempfile.gettempdir() + f"/faim_reason_{uuid4().hex}.db"
    db_url = f"sqlite:///{db_path}"

    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("TENANT_KEYS_JSON", f'{{"{tenant_id}":["{api_key}"]}}')
    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "false")

    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from runtime import context as runtime_context
    from runtime.config import reset_config
    from sqlalchemy import create_engine
    from store.pg import session as pg_session
    from store.pg.models_faim import Base
    from store.pg import models_feedback as _models_feedback  # noqa: F401

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


def _seed_turn(
    db_url: str,
    tenant_id: str,
    graph_id: str,
    turn_id: str,
    session_id: str = "sess-reason",
) -> None:
    """Insert a durable cortex_turn + reasoning nodes so feedback can hydrate."""
    from datetime import datetime, timezone

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from store.pg.models_faim import (
        CortexReasoningNodeModel,
        CortexSessionModel,
        CortexTurnModel,
    )

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        session.add(
            CortexSessionModel(
                session_id=session_id,
                tenant_id=tenant_id,
                graph_id=graph_id,
                title="Where does Atlas live?",
                turn_count=1,
                last_turn_id=turn_id,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            CortexTurnModel(
                turn_id=turn_id,
                session_id=session_id,
                tenant_id=tenant_id,
                graph_id=graph_id,
                query_text="Where does Atlas live?",
                answer_mode="direct",
                task_type="RESEARCH",
                query_hash="qh-reason",
                graph_version=1,
                graph_hash="gh-reason",
                confidence=0.9,
                narrative="Atlas lives in Berlin.",
                answer_json={"direct_answer": "Atlas lives in Berlin."},
                brain_state_json={"goal": "locate"},
                reasoning_count=2,
                open_question_count=0,
                contradiction_count=0,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            CortexReasoningNodeModel(
                node_id=f"rn-{turn_id}-1",
                turn_id=turn_id,
                session_id=session_id,
                tenant_id=tenant_id,
                graph_id=graph_id,
                branch="main",
                title="Locate residence",
                summary="Searching for residence references.",
                evidence_node_ids=["n1"],
                confidence=0.9,
                depends_on=[],
                output_json={},
                created_at=now,
            )
        )
        session.add(
            CortexReasoningNodeModel(
                node_id=f"rn-{turn_id}-2",
                turn_id=turn_id,
                session_id=session_id,
                tenant_id=tenant_id,
                graph_id=graph_id,
                branch="main",
                title="Confirm city",
                summary="Berlin confirmed as city of residence.",
                evidence_node_ids=["n2"],
                confidence=0.92,
                depends_on=[f"rn-{turn_id}-1"],
                output_json={},
                created_at=now,
            )
        )
        session.commit()
    finally:
        session.close()


def test_reasoning_plan_returns_execution_plan(monkeypatch):
    client, headers, _ = _mk_client(monkeypatch)

    resp = client.post(
        "/api/v1/reasoning/plan",
        headers=headers,
        json={
            "query_text": "Why does the economy fluctuate and how does it relate to policy?",
            "answer_mode": "direct",
            "confidence": 0.8,
            "enable_multi_hop": True,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["task_type"]
    assert body["goal"]
    assert body["complexity"]
    assert isinstance(body["sub_queries"], list)


def test_reasoning_stats_empty_then_feedback_hydrated(monkeypatch):
    client, headers, db_url = _mk_client(monkeypatch)
    graph_id = f"reason-{uuid4().hex[:8]}"
    turn_id = f"turn-{uuid4().hex[:8]}"
    _seed_turn(db_url, headers["X-Tenant-Id"], graph_id, turn_id)

    stats_before = client.get("/api/v1/reasoning/stats?days=30", headers=headers)
    assert stats_before.status_code == 200, stats_before.text

    resp = client.post(
        "/api/v1/reasoning/feedback",
        headers=headers,
        json={
            "turn_id": turn_id,
            "user_rating": 0.4,
            "user_correction": "Berlin is incorrect; it is Munich.",
            "correction_type": "factual",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["feedback_id"]
    assert body["pattern_hash"]

    # Verify feedback row has REAL context, not placeholders.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from store.pg.models_feedback import ReasoningFeedbackModel

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        row = (
            session.query(ReasoningFeedbackModel)
            .filter_by(feedback_id=body["feedback_id"])
            .first()
        )
        assert row is not None
        assert row.query_text == "Where does Atlas live?"
        assert row.answer_given == "Atlas lives in Berlin."
        import json as _json

        path = _json.loads(row.reasoning_path_json)
        assert len(path) == 2
        assert "Locate residence" in path[0]
        assert "Confirm city" in path[1]
        assert row.user_rating == 0.4
    finally:
        session.close()


def test_reasoning_feedback_missing_turn_is_404(monkeypatch):
    client, headers, _ = _mk_client(monkeypatch)

    resp = client.post(
        "/api/v1/reasoning/feedback",
        headers=headers,
        json={
            "turn_id": "turn-does-not-exist",
            "user_rating": 0.5,
        },
    )
    assert resp.status_code == 404, resp.text


def test_reasoning_traverse_and_synthesize_surface(monkeypatch):
    client, headers, _ = _mk_client(monkeypatch)

    resp = client.post(
        "/api/v1/reasoning/traverse",
        headers=headers,
        json={
            "start_node_ids": [],
            "goal": "residence",
            "max_hops": 2,
            "min_confidence": 0.1,
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_paths"] == 0

    resp = client.post(
        "/api/v1/reasoning/synthesize",
        headers=headers,
        json={"galaxy_ids": [], "max_galaxies": 3},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["insights"] == []


def _submit_feedback(client, headers, turn_id, rating, correction=None):
    payload = {
        "turn_id": turn_id,
        "user_rating": rating,
    }
    if correction is not None:
        payload["user_correction"] = correction
        payload["correction_type"] = "factual"
    return client.post(
        "/api/v1/reasoning/feedback",
        headers=headers,
        json=payload,
    )


def test_reinforcement_learning_durable_pattern_stats(monkeypatch):
    """Feedback with >=3 samples per pattern must produce durable learned stats
    written to the reinforcement_pattern_stats table and surfaced via the
    learning-state endpoint."""
    client, headers, db_url = _mk_client(monkeypatch)
    tenant_id = headers["X-Tenant-Id"]
    graph_id = f"reason-{uuid4().hex[:8]}"

    turn_ids = [f"turn-rl-{uuid4().hex[:8]}" for _ in range(3)]
    for i, tid in enumerate(turn_ids):
        _seed_turn(db_url, tenant_id, graph_id, tid, session_id=f"sess-rl-{i}")

    # All three turns share the same reasoning path → same pattern_hash.
    # Accurate feedback (rating 0.8, no correction) → high reliability.
    for tid in turn_ids:
        resp = _submit_feedback(client, headers, tid, 0.8)
        assert resp.status_code == 200, resp.text

    resp = client.get("/api/v1/reasoning/learning/state", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_patterns"] >= 1

    pattern = body["patterns"][0]
    assert pattern["pattern_hash"]
    assert pattern["total_uses"] >= 3
    assert pattern["average_rating"] >= 0.7
    assert pattern["reliability_score"] > 0.5

    # Verify the learned stats were persisted durably.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from store.pg.models_feedback import ReinforcementPatternStatsModel

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        rows = (
            session.query(ReinforcementPatternStatsModel)
            .filter_by(tenant_id=tenant_id)
            .all()
        )
        assert len(rows) >= 1
        assert rows[0].pattern_hash == pattern["pattern_hash"]
        assert rows[0].total_uses >= 3
    finally:
        session.close()


def test_reinforcement_learning_adaptive_strategy(monkeypatch):
    """Low-rated feedback surfaces conservative adaptive strategy settings."""
    client, headers, db_url = _mk_client(monkeypatch)
    tenant_id = headers["X-Tenant-Id"]
    graph_id = f"reason-{uuid4().hex[:8]}"

    turn_ids = [f"turn-rl2-{uuid4().hex[:8]}" for _ in range(3)]
    for i, tid in enumerate(turn_ids):
        _seed_turn(db_url, tenant_id, graph_id, tid, session_id=f"sess-rl2-{i}")

    for tid in turn_ids:
        resp = _submit_feedback(client, headers, tid, 0.2)
        assert resp.status_code == 200, resp.text

    resp = client.get("/api/v1/reasoning/learning/state", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    settings = body["adaptive_strategy"]["adaptive_settings"]
    # Low average rating → conservative: multi-hop disabled, high threshold.
    assert settings["multi_hop_enabled"] is False
    assert settings["auto_approve_threshold"] >= 0.9
    assert body["adaptive_strategy"]["recommendations"][0]["type"] == "critical"