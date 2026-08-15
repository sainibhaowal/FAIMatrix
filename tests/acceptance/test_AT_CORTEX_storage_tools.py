"""AT-CORTEX-TOOLS: Cortex storage tools with human-in-the-loop approval.

Verifies:
- GET /cortex/tool-approvals lists pending approval requests (tenant-scoped).
- POST /cortex/tool-approvals/{id}/approve approves AND executes the action
  with a stored receipt.
- POST /cortex/tool-approvals/{id}/reject rejects without executing.
- Read-only storage tools (status, files, orphan scan) work directly.
- Proposed actions never execute before approval.
"""

from __future__ import annotations

import base64
import tempfile
from uuid import uuid4

from fastapi.testclient import TestClient


def _mk_client(
    monkeypatch,
) -> tuple[TestClient, dict, str]:
    tenant_id = f"tenant_cortextools_{uuid4().hex[:6]}"
    api_key = "cortextools_key"
    db_path = tempfile.gettempdir() + f"/faim_cortextools_{uuid4().hex}.db"
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


def test_tool_approval_upload_lifecycle(monkeypatch):
    client, headers, _ = _mk_client(monkeypatch)
    graph_id = f"g_{uuid4().hex[:6]}"

    # Propose an upload via the approval ledger API.
    resp = client.post(
        "/api/v1/cortex/tool-approvals/propose",
        json={
            "tool_name": "faim_storage_upload",
            "graph_id": graph_id,
            "args": {
                "filename": "hello.txt",
                "content_base64": base64.b64encode(b"hello cortex").decode("ascii"),
                "mime_type": "text/plain",
                "profile": "strict",
                "persist_mode": "relaxed",
            },
            "reason": "test upload",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    proposed = resp.json()
    approval_id = proposed["approval_id"]
    assert proposed["status"] == "pending_approval"

    # Pending list shows it.
    listing = client.get("/api/v1/cortex/tool-approvals", headers=headers)
    assert listing.status_code == 200
    assert any(item["id"] == approval_id for item in listing.json()["items"])

    # Approve -> execution should ingest the file and record a receipt.
    decision = client.post(
        f"/api/v1/cortex/tool-approvals/{approval_id}/approve",
        json={"note": "ok"},
        headers=headers,
    )
    assert decision.status_code == 200, decision.text
    payload = decision.json()
    assert payload["execution"]["execution_status"] == "executed"
    receipt = payload["execution"]["receipt"]
    assert receipt["status"] in {"ingested", "completed"}
    assert receipt["raw_id"]

    # File now listed with ingested status.
    files = client.get(
        "/api/v1/storage/files",
        params={"graph_id": graph_id},
        headers=headers,
    )
    assert files.status_code == 200, files.text
    item = next(
        (f for f in files.json()["items"] if f["raw_id"] == receipt["raw_id"]), None
    )
    assert item is not None
    assert item["ingest_status"] in {"ingested", "completed"}


def test_tool_approval_reject_does_not_execute(monkeypatch):
    client, headers, _ = _mk_client(monkeypatch)
    graph_id = f"g_{uuid4().hex[:6]}"

    proposed = client.post(
        "/api/v1/cortex/tool-approvals/propose",
        json={
            "tool_name": "faim_storage_delete",
            "graph_id": graph_id,
            "args": {"raw_id": str(uuid4())},
            "reason": "test reject",
        },
        headers=headers,
    )
    assert proposed.status_code == 200, proposed.text
    approval_id = proposed.json()["approval_id"]

    rejected = client.post(
        f"/api/v1/cortex/tool-approvals/{approval_id}/reject",
        json={"note": "not now"},
        headers=headers,
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["execution_status"] == "skipped"

    # Re-approving a rejected request must fail.
    reapprove = client.post(
        f"/api/v1/cortex/tool-approvals/{approval_id}/approve",
        headers=headers,
    )
    assert reapprove.status_code == 400


def test_storage_status_and_orphan_scan_are_tenant_scoped(monkeypatch):
    client, headers, _ = _mk_client(monkeypatch)
    graph_id = f"g_{uuid4().hex[:6]}"

    status = client.get(
        "/api/v1/cortex/storage/status",
        params={"graph_id": graph_id},
        headers=headers,
    )
    assert status.status_code == 200, status.text
    body = status.json()
    assert body["storage"]["total_files"] == 0
    assert "node_count" in body["storage"]

    scan = client.get(
        "/api/v1/cortex/storage/orphan-scan",
        params={"graph_id": graph_id},
        headers=headers,
    )
    assert scan.status_code == 200, scan.text
    assert scan.json()["healthy"] is True


def test_tool_approvals_are_tenant_scoped(monkeypatch):
    client, headers, _ = _mk_client(monkeypatch)
    graph_id = f"g_{uuid4().hex[:6]}"

    client.post(
        "/api/v1/cortex/tool-approvals/propose",
        json={
            "tool_name": "faim_storage_upload",
            "graph_id": graph_id,
            "args": {
                "filename": "x.txt",
                "content_base64": base64.b64encode(b"x").decode("ascii"),
                "mime_type": "text/plain",
            },
            "reason": "tenant scope test",
        },
        headers=headers,
    )

    # A different tenant must not see the proposal.
    other_key = "other_key"
    other_tenant = f"other_{uuid4().hex[:6]}"
    client2_headers = {"X-Tenant-Id": other_tenant, "X-Api-Key": other_key}
    # Add other tenant key via env in a fresh client; simpler: verify isolation
    # through the approval ledger helpers in-process.

    from runtime import context as runtime_context
    from runtime.config import reset_config

    # Bypass env for second tenant by direct DB call.
    import tempfile as _tf

    db_url = runtime_context.get_session().bind.engine.url.render_as_string(
        hide_password=False
    )
    del db_url  # unused; session is shared sqlite via env
    session = runtime_context.get_session()
    from core.cortex.cortex_storage_tools import list_approvals

    items = list_approvals(session, tenant_id=other_tenant)
    assert items == []

    items_self = list_approvals(session, tenant_id=headers["X-Tenant-Id"])
    assert len(items_self) >= 1
    session.close()
