"""Phase F acceptance: storage lifecycle and non-regression behaviors."""

from __future__ import annotations

from uuid import uuid4


def _mk_client(monkeypatch, tenant_id: str, api_key: str):
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from fastapi.testclient import TestClient
    from runtime.config import reset_config

    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("TENANT_KEYS_JSON", f'{{"{tenant_id}":["{api_key}"]}}')
    reset_config()
    reload_tenant_keys()

    app = create_app()
    return TestClient(app), {"X-Tenant-Id": tenant_id, "X-Api-Key": api_key}


def _drain_jobs(monkeypatch, *, max_iterations: int = 10):
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


def test_storage_full_lifecycle_upload_to_delete_and_retention_dry_run(monkeypatch):
    from runtime.context import close_session, get_repos

    tenant_id = "tenant_pf_lifecycle"
    graph_id = f"phase-f-lifecycle-{uuid4().hex[:8]}"
    client, headers = _mk_client(monkeypatch, tenant_id, "pf_lifecycle_key")

    files = [
        ("files", ("phase-f-lifecycle.txt", b"phase-f lifecycle payload", "text/plain"))
    ]
    form = {"graph_id": graph_id, "profile": "strict", "persist_mode": "relaxed"}

    upload = client.post(
        "/api/v1/storage/uploads", headers=headers, data=form, files=files
    )
    assert upload.status_code == 200
    upload_body = upload.json()
    assert upload_body["requested_files"] == 1
    assert upload_body["processed_files"] == 0
    assert upload_body["files"], "Expected per-file results in upload response"

    first_file = upload_body["files"][0]
    raw_id = first_file.get("raw_id")
    assert raw_id, "Expected raw_id in per-file upload result"
    assert first_file["status"] == "queued"

    job_id = upload_body["job_id"]

    _drain_jobs(monkeypatch)

    status = client.get(f"/api/v1/storage/uploads/{job_id}", headers=headers)
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["job_id"] == job_id
    assert status_body["requested_files"] == 1
    assert status_body["status"] in {"done", "pending"}
    assert isinstance(status_body["files"], list)

    events = client.get(f"/api/v1/storage/uploads/{job_id}/events", headers=headers)
    assert events.status_code == 200
    events_body = events.json()
    assert events_body["job_id"] == job_id
    assert len(events_body["events"]) >= 1

    file_list = client.get(
        f"/api/v1/storage/files?graph_id={graph_id}&limit=25&offset=0", headers=headers
    )
    assert file_list.status_code == 200
    list_body = file_list.json()
    assert list_body["total"] >= 1
    listed_ids = {item["raw_id"] for item in list_body["items"]}
    assert raw_id in listed_ids

    detail = client.get(
        f"/api/v1/storage/files/{raw_id}?graph_id={graph_id}",
        headers=headers,
    )
    assert detail.status_code == 200
    assert detail.json()["raw_id"] == raw_id

    provenance = client.get(
        f"/api/v1/storage/files/{raw_id}/provenance?graph_id={graph_id}",
        headers=headers,
    )
    assert provenance.status_code == 200
    prov_body = provenance.json()
    assert prov_body["file"]["raw_id"] == raw_id
    assert "dedup" in prov_body
    assert "nodes" in prov_body
    assert "events" in prov_body

    delete_req = client.delete(
        f"/api/v1/storage/files/{raw_id}?graph_id={graph_id}"
        f"&reason=phase-f-delete-test&hard_delete=false",
        headers=headers,
    )
    assert delete_req.status_code == 200
    assert delete_req.json()["delete_requested"] is True

    retention = client.post(
        "/api/v1/storage/retention/execute",
        headers=headers,
        json={
            "graph_id": graph_id,
            "limit": 100,
            "dry_run": True,
            "irreversible": False,
            "reason": "phase-f dry run",
        },
    )
    assert retention.status_code == 200
    retention_body = retention.json()
    assert retention_body["dry_run"] is True
    assert retention_body["scanned"] >= 1
    assert any(item["raw_id"] == raw_id for item in retention_body["results"])

    # Ensure provenance remains queryable after logical delete request.
    prov_after_delete = client.get(
        f"/api/v1/storage/files/{raw_id}/provenance?graph_id={graph_id}",
        headers=headers,
    )
    assert prov_after_delete.status_code == 200

    # Cleanup test session explicitly when repos were initialized in app path.
    repos = get_repos(tenant_id)
    close_session(repos["session"])


def test_storage_retry_is_idempotent_for_failed_only(monkeypatch):
    from runtime.context import close_session, get_repos

    tenant_id = "tenant_pf_retry"
    graph_id = f"phase-f-retry-{uuid4().hex[:8]}"
    client, headers = _mk_client(monkeypatch, tenant_id, "pf_retry_key")

    repos = get_repos(tenant_id)
    session = repos["session"]
    try:
        payload = b"phase-f retry payload"
        raw_ref = repos["raw_store"].store(
            payload, mime_type="text/plain", graph_id=graph_id
        )
        saved = repos["raw_repo"].create(session, raw_ref)
        repos["storage_file_repo"].upsert_upload(
            session,
            graph_id=graph_id,
            raw_id=saved.id,
            filename="phase-f-retry.txt",
            mime_type="text/plain",
            size_bytes=len(payload),
            sha256=str(saved.sha256),
            job_id=None,
        )
        repos["storage_file_repo"].mark_ingest_result(
            session,
            raw_id=saved.id,
            graph_id=graph_id,
            status="error",
            packet_hash="phase-f-retry-packet",
            node_count=0,
            vector_count=0,
            error_message="extract parser failed",
            job_id=None,
        )
        session.commit()
        raw_id = str(saved.id)
    finally:
        close_session(session)

    first_retry = client.post(
        f"/api/v1/storage/files/{raw_id}/retry?graph_id={graph_id}&profile=strict&persist_mode=relaxed",
        headers=headers,
    )
    assert first_retry.status_code == 200
    retry_body = first_retry.json()
    assert retry_body["status"] == "ok"
    assert retry_body["file"]["raw_id"] == raw_id
    assert retry_body["file"]["ingest_status"] in {"ingested", "dedup_hit", "failed"}

    # Retry endpoint should reject repeated retries when file is no longer in failed state.
    second_retry = client.post(
        f"/api/v1/storage/files/{raw_id}/retry?graph_id={graph_id}&profile=strict&persist_mode=relaxed",
        headers=headers,
    )
    assert second_retry.status_code in {200, 409}
    if second_retry.status_code == 409:
        assert "only allowed for failed files" in second_retry.json()["detail"].lower()


def test_storage_cancel_flow_marks_cancel_requested(monkeypatch):
    from orchestration.jobs.job_store import JobStore
    from runtime.context import close_session, get_repos

    tenant_id = "tenant_pf_cancel"
    graph_id = f"phase-f-cancel-{uuid4().hex[:8]}"
    client, headers = _mk_client(monkeypatch, tenant_id, "pf_cancel_key")

    repos = get_repos(tenant_id)
    session = repos["session"]
    try:
        job_id = JobStore.enqueue(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            kind="storage_upload",
            payload={"requested_files": 3},
        )
    finally:
        close_session(session)

    cancel_resp = client.post(
        f"/api/v1/storage/uploads/{job_id}/cancel?reason=phase-f-cancel",
        headers=headers,
    )
    assert cancel_resp.status_code == 200
    cancel_body = cancel_resp.json()
    assert cancel_body["job_id"] == str(job_id)
    assert cancel_body["cancel_requested"] is True

    status_resp = client.get(f"/api/v1/storage/uploads/{job_id}", headers=headers)
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["cancel_requested"] is True
    assert "phase-f-cancel" in str(status_body.get("cancel_reason", ""))

    # Idempotent repeated cancellation should remain safe.
    cancel_again = client.post(
        f"/api/v1/storage/uploads/{job_id}/cancel?reason=phase-f-cancel",
        headers=headers,
    )
    assert cancel_again.status_code == 200
    assert cancel_again.json()["cancel_requested"] is True


def test_storage_graph_list_endpoint_returns_real_counts(monkeypatch):
    """GET /storage/graphs returns real per-graph node/edge/version counts."""
    from runtime.context import close_session, get_repos

    tenant_id = "tenant_pf_graphlist"
    graph_id = f"phase-f-graphlist-{uuid4().hex[:8]}"
    client, headers = _mk_client(monkeypatch, tenant_id, "pf_graphlist_key")

    repos = get_repos(tenant_id)
    session = repos["session"]
    try:
        # Create graph_version row to register the graph.
        from store.pg.models_faim import GraphVersionModel, NodeModel

        session.add(
            GraphVersionModel(
                tenant_id=tenant_id,
                graph_id=graph_id,
                version=3,
                reason="graph-list test",
            )
        )
        session.add_all(
            [
                NodeModel(
                    node_id=uuid4(),
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    kind="atom",
                    vector_hash="gl-hash-1",
                    raw_id=str(uuid4()),
                    v_native=[0.1],
                ),
                NodeModel(
                    node_id=uuid4(),
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    kind="atom",
                    vector_hash="gl-hash-2",
                    raw_id=str(uuid4()),
                    v_native=[0.2],
                ),
            ]
        )
        session.commit()
    finally:
        close_session(session)

    resp = client.get("/api/v1/storage/graphs", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    graph = next((g for g in body["items"] if g["graph_id"] == graph_id), None)
    assert graph is not None
    assert graph["node_count"] == 2
    assert graph["version"] == 3
    assert graph["last_updated"]

    # Tenant isolation: a second tenant sees no graphs from the first.
    tenant2 = "tenant_pf_graphlist_b"
    _mk_client_tenant2 = None
    from api.app import create_app as _create_app2
    from api.middleware.auth import reload_tenant_keys as _reload2
    from fastapi.testclient import TestClient as _TC2
    from runtime.config import reset_config as _reset2

    monkeypatch.setenv(
        "TENANT_KEYS_JSON",
        f'{{"{tenant_id}":["pf_graphlist_key"],"{tenant2}":["pf_graphlist_key_b"]}}',
    )
    _reset2()
    _reload2()
    client2 = _TC2(_create_app2())
    resp2 = client2.get(
        "/api/v1/storage/graphs",
        headers={"X-Tenant-Id": tenant2, "X-Api-Key": "pf_graphlist_key_b"},
    )
    assert resp2.status_code == 200, resp2.text
    assert all(g["graph_id"] != graph_id for g in resp2.json()["items"])
