"""AT-HEALTH: /pipeline/stats returns real values (not hardcoded placeholders)."""

from __future__ import annotations

import tempfile
from uuid import uuid4

from fastapi.testclient import TestClient


def _mk_client(monkeypatch) -> tuple[TestClient, dict, str]:
    tenant_id = f"tenant_health_{uuid4().hex[:6]}"
    api_key = "health_key"
    db_path = tempfile.gettempdir() + f"/faim_health_{uuid4().hex}.db"
    db_url = f"sqlite:///{db_path}"

    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("TENANT_KEYS_JSON", f'{{"{tenant_id}":["{api_key}"]}}')
    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true")

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


def test_pipeline_stats_returns_live_queue_depth(monkeypatch):
    client, headers, db_url = _mk_client(monkeypatch)

    # Seed two pending jobs so queue depth reflects real DB state.
    from uuid import UUID as _UUID
    from datetime import datetime, timezone

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        for i in range(2):
            session.execute(
                text(
                    "INSERT INTO jobs (job_id, tenant_id, graph_id, kind, "
                    "payload_json, status, created_at, updated_at) "
                    "VALUES (:id, :t, :g, 'evolve', '{}', 'pending', :now, :now)"
                ),
                {
                    "id": str(_UUID(int=i + 1)),
                    "t": headers["X-Tenant-Id"],
                    "g": "graph-health",
                    "now": now,
                },
            )
        session.commit()
    finally:
        session.close()

    resp = client.get("/api/v1/pipeline/stats", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["queue_depth"] == 2
    assert body["hot_cache_size"] >= 0
    assert body["throughput"] >= 0.0
    assert "system_health" in body
    assert "redis" in body["system_health"]
    assert "qdrant" in body["system_health"]