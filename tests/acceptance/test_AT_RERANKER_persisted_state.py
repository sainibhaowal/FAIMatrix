"""AT-RERANKER: reranker activate/deactivate state persists across API restarts."""

from __future__ import annotations

import tempfile
from uuid import uuid4

from fastapi.testclient import TestClient


def _mk_client(monkeypatch) -> tuple[TestClient, dict, str]:
    tenant_id = f"tenant_rr_{uuid4().hex[:6]}"
    api_key = "rr_key"
    db_path = tempfile.gettempdir() + f"/faim_rr_{uuid4().hex}.db"
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


def _clear_memory_state() -> None:
    import api.routers.reranker as rr

    rr._RERANKER_ACTIVE_STATE.clear()


def test_reranker_state_persists_across_restart(monkeypatch):
    _clear_memory_state()
    client, headers, db_url = _mk_client(monkeypatch)

    # Default: active.
    status = client.get("/api/v1/reranker/status", headers=headers)
    assert status.status_code == 200, status.text
    assert status.json()["available"] is True

    # Deactivate -> persisted.
    deact = client.post("/api/v1/reranker/deactivate", headers=headers)
    assert deact.status_code == 200, deact.text
    assert deact.json()["active"] is False

    # Simulate a fresh process: clear memory, build a NEW app against same DB.
    _clear_memory_state()
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from runtime import context as runtime_context
    from runtime.config import reset_config
    from store.pg import session as pg_session

    monkeypatch.setattr(pg_session, "_SESSION_FACTORY_CACHE", {}, raising=False)
    monkeypatch.setattr(runtime_context, "_engine", None, raising=False)
    monkeypatch.setattr(runtime_context, "_engine_db_url", None, raising=False)
    monkeypatch.setattr(runtime_context, "_SessionLocal", None, raising=False)
    reset_config()
    reload_tenant_keys()

    client2 = TestClient(create_app())
    status2 = client2.get("/api/v1/reranker/status", headers=headers)
    assert status2.status_code == 200, status2.text
    assert status2.json()["available"] is False

    # Re-activate -> persists again.
    act = client2.post("/api/v1/reranker/activate", headers=headers)
    assert act.status_code == 200, act.text
    assert act.json()["active"] is True

    _clear_memory_state()
    client3 = TestClient(create_app())
    status3 = client3.get("/api/v1/reranker/status", headers=headers)
    assert status3.status_code == 200, status3.text
    assert status3.json()["available"] is True

    # Verify the durable row exists.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from store.pg.models_faim import ServiceSettingModel

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        row = (
            session.query(ServiceSettingModel)
            .filter_by(tenant_id=headers["X-Tenant-Id"], key="reranker_active")
            .first()
        )
        assert row is not None
        assert row.value_json == {"active": True}
    finally:
        session.close()