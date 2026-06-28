"""Phase EV-B acceptance: evolve status surface and tenant isolation."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def _mk_client(monkeypatch, *, tenant_keys_json: str, database_url: str) -> TestClient:
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from runtime import context as runtime_context
    from runtime.config import reset_config
    from store.pg import session as pg_session

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TENANT_KEYS_JSON", tenant_keys_json)
    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_TRIGGER_MODE", "hybrid")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MIN_INTERVAL_SECONDS", "30")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MIN_VERSION_DELTA", "1")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MAX_ACTIONS", "25")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_SCAN_INTERVAL_SECONDS", "60")
    monkeypatch.setenv("FAIM_SELF_INVENT_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_INVENT_ON_EVOLVE", "true")
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true")
    monkeypatch.setattr(pg_session, "_SESSION_FACTORY_CACHE", {}, raising=False)
    monkeypatch.setattr(runtime_context, "_engine", None, raising=False)
    monkeypatch.setattr(runtime_context, "_engine_db_url", None, raising=False)
    monkeypatch.setattr(runtime_context, "_SessionLocal", None, raising=False)
    reset_config()
    reload_tenant_keys()
    return TestClient(create_app())


def test_phase_ev_b_evolve_status_route_present():
    from api.routers.evolve import router

    paths = {route.path for route in router.routes}
    assert "/evolve" in paths
    assert "/evolve/status" in paths


def test_phase_ev_b_evolve_status_ratelimit_mapping():
    from api.middleware.ratelimit import classify_endpoint_category

    assert classify_endpoint_category("GET", "/api/v1/evolve/status") == "query_read"
    assert classify_endpoint_category("POST", "/api/v1/evolve") == "ingest_write"


def test_phase_ev_b_evolve_status_tenant_isolation(monkeypatch, tmp_path):
    from orchestration.self_evolve_scheduler import enqueue_self_evolve_if_due
    from runtime.context import close_session, get_repos
    from store.pg.repos.self_evolution_state_repo import SelfEvolutionStateRepo

    tenant_a = f"tenant_evb_a_{uuid4().hex[:6]}"
    tenant_b = f"tenant_evb_b_{uuid4().hex[:6]}"
    key_a = "key_evb_a"
    key_b = "key_evb_b"
    graph_id = f"graph_evb_{uuid4().hex[:8]}"
    database_url = f"sqlite:///{tmp_path / 'evb_status.db'}"

    client = _mk_client(
        monkeypatch,
        tenant_keys_json=f'{{"{tenant_a}":["{key_a}"],"{tenant_b}":["{key_b}"]}}',
        database_url=database_url,
    )

    repos_a = get_repos(tenant_a)
    session_a = repos_a["session"]
    try:
        repos_a["gv_repo"].set_version(session_a, graph_id, 4, "seed-status")
        session_a.commit()
        enqueue_result = enqueue_self_evolve_if_due(
            session=session_a,
            tenant_id=tenant_a,
            graph_id=graph_id,
            source="memory_write",
        )
        assert enqueue_result.status in {"enqueued", "existing"}
    finally:
        close_session(session_a)

    headers_a = {"X-Tenant-Id": tenant_a, "X-Api-Key": key_a}
    headers_b = {"X-Tenant-Id": tenant_b, "X-Api-Key": key_b}

    status_a = client.get(
        f"/api/v1/evolve/status?graph_id={graph_id}&source=memory_write",
        headers=headers_a,
    )
    assert status_a.status_code == 200
    body_a = status_a.json()
    assert body_a["tenant_id"] == tenant_a
    assert body_a["guardrails"]["automation_path"] == "hybrid_worker"
    assert body_a["guardrails"]["automation_enabled"] is True
    assert body_a["guardrails"]["self_evolve_enabled"] is True
    assert body_a["guardrails"]["self_invent_enabled"] is True
    assert body_a["state"]["graph_version"] == 4
    assert body_a["due"]["reason"] == "active_evolve_job_exists"
    assert body_a["active_job"] is not None
    assert body_a["last_enqueued_job"] is not None

    status_b = client.get(
        f"/api/v1/evolve/status?graph_id={graph_id}&source=memory_write",
        headers=headers_b,
    )
    assert status_b.status_code == 200
    body_b = status_b.json()
    assert body_b["tenant_id"] == tenant_b
    assert body_b["guardrails"]["automation_path"] == "hybrid_worker"
    assert body_b["state"]["graph_version"] == 0
    assert body_b["active_job"] is None
    assert body_b["last_enqueued_job"] is None

    repos_b = get_repos(tenant_b)
    session_b = repos_b["session"]
    try:
        state_repo = SelfEvolutionStateRepo(session=session_b, tenant_id=tenant_b)
        assert state_repo.get(graph_id=graph_id, session=session_b) is None
    finally:
        close_session(session_b)
