"""Phase D acceptance: storage auth and tenant isolation coverage."""

from __future__ import annotations

from uuid import uuid4

from fastapi.routing import APIRoute


def _route_path_with_ids(path: str) -> str:
    value = path.replace("{job_id}", "00000000-0000-0000-0000-000000000000")
    value = value.replace("{raw_id}", "00000000-0000-0000-0000-000000000000")
    return value


def test_all_storage_routes_require_auth_headers(monkeypatch):
    from api.app import create_app
    from api.routers.storage import router as storage_router
    from fastapi.testclient import TestClient

    monkeypatch.setenv("FAIM_ENV", "development")
    app = create_app()
    client = TestClient(app)

    for route in storage_router.routes:
        if not isinstance(route, APIRoute):
            continue
        path = "/api/v1" + _route_path_with_ids(route.path)
        for method in sorted(route.methods or []):
            if method in {"HEAD", "OPTIONS"}:
                continue
            response = client.request(method, path)
            assert response.status_code == 401, f"{method} {path} should require auth"


def test_storage_route_tenant_isolation(monkeypatch):
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from fastapi.testclient import TestClient
    from orchestration.jobs.job_store import JobStore
    from runtime.context import close_session, get_repos

    graph_id = f"phase-d-tenant-{uuid4().hex[:8]}"
    monkeypatch.setenv(
        "TENANT_KEYS_JSON",
        '{"tenant_a":["key_a"],"tenant_b":["key_b"]}',
    )
    monkeypatch.setenv("FAIM_ENV", "development")
    reload_tenant_keys()

    app = create_app()
    client = TestClient(app)

    headers_a = {"X-Tenant-Id": "tenant_a", "X-Api-Key": "key_a"}
    headers_b = {"X-Tenant-Id": "tenant_b", "X-Api-Key": "key_b"}

    repos_a = get_repos("tenant_a")
    session_a = repos_a["session"]
    try:
        raw_ref = repos_a["raw_store"].store(
            b"phase d tenant payload",
            mime_type="text/plain",
            graph_id=graph_id,
        )
        saved = repos_a["raw_repo"].create(session_a, raw_ref)
        job_id = JobStore.enqueue(
            session=session_a,
            tenant_id="tenant_a",
            graph_id=graph_id,
            kind="storage_upload",
            payload={"requested_files": 1},
        )
        repos_a["storage_file_repo"].upsert_upload(
            session_a,
            graph_id=graph_id,
            raw_id=saved.id,
            filename="tenant-a.txt",
            mime_type="text/plain",
            size_bytes=22,
            sha256=str(saved.sha256),
            job_id=job_id,
        )
        session_a.commit()
        raw_id = str(saved.id)
    finally:
        close_session(session_a)

    # Tenant B must not access tenant A job/status/event resources.
    status_b = client.get(f"/api/v1/storage/uploads/{job_id}", headers=headers_b)
    assert status_b.status_code == 404

    events_b = client.get(f"/api/v1/storage/uploads/{job_id}/events", headers=headers_b)
    assert events_b.status_code == 404

    # Tenant B list view should not leak tenant A graph files.
    list_b = client.get(f"/api/v1/storage/files?graph_id={graph_id}", headers=headers_b)
    assert list_b.status_code == 200
    assert list_b.json()["total"] == 0

    # Tenant A can access its file.
    file_a = client.get(
        f"/api/v1/storage/files/{raw_id}?graph_id={graph_id}",
        headers=headers_a,
    )
    assert file_a.status_code == 200

    # Tenant B cannot access file detail or provenance.
    file_b = client.get(
        f"/api/v1/storage/files/{raw_id}?graph_id={graph_id}",
        headers=headers_b,
    )
    assert file_b.status_code == 404

    prov_b = client.get(
        f"/api/v1/storage/files/{raw_id}/provenance?graph_id={graph_id}",
        headers=headers_b,
    )
    assert prov_b.status_code == 404
