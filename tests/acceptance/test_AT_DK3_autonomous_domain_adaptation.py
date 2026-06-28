"""AT-DK3: Autonomous domain adaptation after upload."""

from __future__ import annotations

from uuid import uuid4


def _mk_client(monkeypatch, tenant_id: str, api_key: str):
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from fastapi.testclient import TestClient
    from runtime.config import reset_config

    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true")
    monkeypatch.setenv("FAIM_DOMAIN_AUTONOMY_ENABLED", "true")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("TENANT_KEYS_JSON", f'{{"{tenant_id}":["{api_key}"]}}')
    reset_config()
    reload_tenant_keys()

    app = create_app()
    return TestClient(app), {"X-Tenant-Id": tenant_id, "X-Api-Key": api_key}


def _drain_jobs(monkeypatch, *, max_iterations: int = 20):
    from orchestration.jobs.worker import Worker
    from store.pg import session as pg_session
    from store.pg.models_faim import JobModel

    monkeypatch.setattr(
        "orchestration.jobs.worker.get_session",
        lambda: pg_session.get_session(),
    )

    worker = Worker(poll_interval=0.01, self_evolve_scan_interval_seconds=3600.0)
    for _ in range(max_iterations):
        check_session = pg_session.get_session()
        try:
            pending = (
                check_session.query(JobModel)
                .filter(
                    JobModel.status.in_(["pending", "running"]),
                    JobModel.kind.in_(list(worker.executable_job_kinds)),
                )
                .count()
            )
        finally:
            check_session.close()
        if pending <= 0:
            break
        worker._poll_and_execute()


def test_autonomous_domain_adaptation_grows_graph_local_lexicon_and_sources(monkeypatch):
    from runtime.context import close_session, get_repos
    from store.pg.models_faim import GraphDomainLexiconModel, GraphKBSourceModel

    tenant_id = "tenant_dk3_auto"
    graph_id = f"graph-dk3-{uuid4().hex[:8]}"
    client, headers = _mk_client(monkeypatch, tenant_id, "dk3_auto_key")

    payload = (
        b"Acme revenue reached 10M in 2026. EBITDA margin improved. "
        b"Application Programming Interface (API) latency also improved."
    )

    upload = client.post(
        "/api/v1/storage/uploads",
        headers=headers,
        data={"graph_id": graph_id, "profile": "strict", "persist_mode": "relaxed"},
        files=[("files", ("dk3-auto.txt", payload, "text/plain"))],
    )
    assert upload.status_code == 200, upload.text
    body = upload.json()
    assert body["job_id"]

    _drain_jobs(monkeypatch)

    memory_response = client.get(
        f"/api/v1/storage/domain-memory?graph_id={graph_id}&limit=8",
        headers=headers,
    )
    assert memory_response.status_code == 200, memory_response.text
    memory_body = memory_response.json()
    assert memory_body["graph_id"] == graph_id
    assert memory_body["jobs_enabled"] is True
    assert memory_body["domain_autonomy_enabled"] is True

    repos = get_repos(tenant_id)
    session = repos["session"]
    try:
        lexicon_rows = (
            session.query(GraphDomainLexiconModel)
            .filter_by(tenant_id=tenant_id, graph_id=graph_id)
            .all()
        )
        source_rows = (
            session.query(GraphKBSourceModel)
            .filter_by(tenant_id=tenant_id, graph_id=graph_id)
            .all()
        )
        assert lexicon_rows, "expected autonomous domain lexicon rows"
        assert source_rows, "expected autonomous domain source rows"
        assert any(row.domain_pack in {"finance", "software"} for row in lexicon_rows)
        assert any((row.meta or {}).get("node_id") for row in lexicon_rows)
        assert memory_body["lexicon_total"] >= len(lexicon_rows)
        assert memory_body["source_total"] >= len(source_rows)
        assert memory_body["top_terms"], "expected top domain terms in memory view"
    finally:
        close_session(session)
