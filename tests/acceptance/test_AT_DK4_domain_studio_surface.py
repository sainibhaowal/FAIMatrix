"""AT-DK4: Dedicated domain studio API surface."""

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


def test_domain_studio_surface_returns_overview_terms_and_graph(monkeypatch):
    tenant_id = "tenant_dk4_surface"
    graph_id = f"graph-dk4-{uuid4().hex[:8]}"
    client, headers = _mk_client(monkeypatch, tenant_id, "dk4_surface_key")

    payload = (
        b"Acme EBITDA margin improved. Revenue increased to 10M. "
        b"API latency fell after deployment. Incident response playbooks improved."
    )

    upload = client.post(
        "/api/v1/storage/uploads",
        headers=headers,
        data={"graph_id": graph_id, "profile": "strict", "persist_mode": "relaxed"},
        files=[("files", ("dk4-domain.txt", payload, "text/plain"))],
    )
    assert upload.status_code == 200, upload.text

    _drain_jobs(monkeypatch)

    overview = client.get(
        f"/api/v1/domain/overview?graph_id={graph_id}&limit=10",
        headers=headers,
    )
    assert overview.status_code == 200, overview.text
    overview_body = overview.json()
    assert overview_body["graph_id"] == graph_id
    assert overview_body["lexicon_total"] > 0
    assert overview_body["pack_strengths"]
    assert overview_body["top_terms"]

    terms = client.get(
        f"/api/v1/domain/terms?graph_id={graph_id}&limit=20&q=api",
        headers=headers,
    )
    assert terms.status_code == 200, terms.text
    terms_body = terms.json()
    assert terms_body["graph_id"] == graph_id
    assert terms_body["items"]

    graph = client.get(
        f"/api/v1/domain/graph?graph_id={graph_id}&limit=20",
        headers=headers,
    )
    assert graph.status_code == 200, graph.text
    graph_body = graph.json()
    assert graph_body["graph_id"] == graph_id
    assert graph_body["nodes"]
    assert graph_body["edges"]
    assert any(node["type"] == "pack" for node in graph_body["nodes"])
