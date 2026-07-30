"""Phase E acceptance: storage observability + operations surface."""

from __future__ import annotations

from uuid import uuid4


def test_phase_e_storage_observability_route_present():
    from api.routers.storage import router

    paths = {route.path for route in router.routes}
    assert "/storage/ops/metrics" in paths


def test_storage_ops_metrics_returns_expected_contract(monkeypatch):
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from fastapi.testclient import TestClient
    from runtime.context import close_session, get_repos

    tenant_id = "tenant_obs"
    graph_id = f"phase-e-obs-{uuid4().hex[:8]}"

    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_obs":["obs_key"]}')
    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("FAIM_STORAGE_OBSERVABILITY_ENABLED", "true")
    reload_tenant_keys()

    app = create_app()
    client = TestClient(app)
    headers = {"X-Tenant-Id": tenant_id, "X-Api-Key": "obs_key"}

    repos = get_repos(tenant_id)
    session = repos["session"]
    try:
        payload_ok = b"phase-e-observability-ok"
        raw_ref_ok = repos["raw_store"].store(
            payload_ok,
            mime_type="text/plain",
            graph_id=graph_id,
        )
        saved_ok = repos["raw_repo"].create(session, raw_ref_ok)
        repos["storage_file_repo"].upsert_upload(
            session,
            graph_id=graph_id,
            raw_id=saved_ok.id,
            filename="ok.txt",
            mime_type="text/plain",
            size_bytes=len(payload_ok),
            sha256=str(saved_ok.sha256),
            job_id=None,
        )
        repos["storage_file_repo"].mark_ingest_result(
            session,
            raw_id=saved_ok.id,
            graph_id=graph_id,
            status="dedup_hit",
            packet_hash="packet-ok",
            node_count=0,
            vector_count=0,
            error_message=None,
            job_id=None,
        )

        payload_failed = b"phase-e-observability-failed"
        raw_ref_failed = repos["raw_store"].store(
            payload_failed,
            mime_type="text/plain",
            graph_id=graph_id,
        )
        saved_failed = repos["raw_repo"].create(session, raw_ref_failed)
        repos["storage_file_repo"].upsert_upload(
            session,
            graph_id=graph_id,
            raw_id=saved_failed.id,
            filename="failed.txt",
            mime_type="text/plain",
            size_bytes=len(payload_failed),
            sha256=str(saved_failed.sha256),
            job_id=None,
        )
        repos["storage_file_repo"].mark_ingest_result(
            session,
            raw_id=saved_failed.id,
            graph_id=graph_id,
            status="error",
            packet_hash="packet-failed",
            node_count=0,
            vector_count=0,
            error_message="extract parser failed",
            job_id=None,
        )

        repos["event_repo"].emit(
            session,
            graph_id,
            "INGEST_PHASE_LATENCY",
            {
                "raw_id": str(saved_ok.id),
                "status": "completed",
                "phase_latency_ms": {
                    "extract": 12,
                    "encode": 20,
                },
                "latency_ms": 45,
            },
        )
        session.commit()
    finally:
        close_session(session)

    response = client.get(
        f"/api/v1/storage/ops/metrics?graph_id={graph_id}&window_seconds=3600",
        headers=headers,
    )
    assert response.status_code == 200

    body = response.json()
    assert body["graph_id"] == graph_id
    assert body["upload_count"] >= 2
    assert body["upload_bytes"] > 0
    assert body["dedup_hits"] >= 1
    assert isinstance(body["dedup_ratio"], float)

    assert "failure_reasons" in body
    assert "extract_error" in body["failure_reasons"]

    assert "phase_latency_ms" in body
    assert "extract" in body["phase_latency_ms"]
    assert body["phase_latency_ms"]["extract"]["count"] >= 1
    assert body["phase_latency_ms"]["extract"]["max_ms"] >= 12

    assert "backend_states" in body
    assert "postgres" in body["backend_states"]
    assert body["backend_states"]["postgres"]["status"] in {"up", "degraded", "down"}


def test_storage_ops_metrics_flag_can_disable_endpoint(monkeypatch):
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from fastapi.testclient import TestClient

    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_obs":["obs_key"]}')
    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("FAIM_STORAGE_OBSERVABILITY_ENABLED", "false")
    reload_tenant_keys()

    app = create_app()
    client = TestClient(app)
    headers = {"X-Tenant-Id": "tenant_obs", "X-Api-Key": "obs_key"}

    response = client.get("/api/v1/storage/ops/metrics", headers=headers)
    assert response.status_code == 409
    assert "disabled" in response.json().get("detail", "").lower()
