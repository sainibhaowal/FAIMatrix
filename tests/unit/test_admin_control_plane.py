from __future__ import annotations

import jwt
from fastapi.testclient import TestClient


def _mint_access_token(secret: str, *, user_id: str, graph_id: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "userId": user_id,
            "id": user_id,
            "graphId": graph_id,
            "email": "admin@example.com",
            "name": "Admin",
        },
        secret,
        algorithm="HS256",
    )


def _mk_client(monkeypatch, tmp_path):
    from api.app import create_app
    from api.deps import get_faim_context
    from runtime.config import reset_config

    secret = "test-admin-secret"
    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_admin":["tenant_key"]}')
    monkeypatch.setenv("NEXTAUTH_SECRET", secret)
    monkeypatch.setenv("FAIM_ADMIN_KEY", "super-admin-key")
    monkeypatch.setenv("RESEND_API_KEY", "resend-test-key")
    monkeypatch.setenv("FAIM_BACKUP_DIR", str(tmp_path / "backups"))
    reset_config()
    app = create_app()

    class _FakeNode:
        def __init__(self, node_id: str, graph_id: str):
            self.node_id = node_id
            self.graph_id = graph_id
            self.v_native = [0.1, 0.2, 0.3]
            self.level = 1
            self.kind = "fact"

    class _FakeIndex:
        def __init__(self):
            self.calls = []

        def add(self, **kwargs):
            self.calls.append(kwargs)

    class _FakeGVRepo:
        def __init__(self):
            self.version = 4

        def get_or_create(self, session, graph_id: str):  # noqa: ANN001
            return type("GV", (), {"version": self.version})()

    class _FakeNodeRepo:
        def list_by_graph(self, graph_id: str, limit: int = 10000):
            return [_FakeNode("node-1", graph_id)]

        def count(self, graph_id: str):
            return 1

    class _FakeSnapshotRepo:
        def __init__(self):
            self.items = []

        def create(self, session, snapshot):  # noqa: ANN001
            self.items.append(snapshot)

    class _FakeEventRepo:
        def get_by_seq(self, session, graph_id: str, after_seq: int, limit: int):  # noqa: ANN001
            return []

    class _FakeSession:
        def commit(self):
            return None

    fake_ctx = type(
        "FakeCtx",
        (),
        {
            "tenant_id": "tenant_admin",
            "request_id": "req-admin",
            "session": _FakeSession(),
            "node_repo": _FakeNodeRepo(),
            "edge_repo": None,
            "event_repo": _FakeEventRepo(),
            "gv_repo": _FakeGVRepo(),
            "snapshot_repo": _FakeSnapshotRepo(),
            "raw_repo": None,
            "storage_file_repo": None,
            "index": _FakeIndex(),
            "cache": None,
            "raw_store": None,
        },
    )()

    app.dependency_overrides[get_faim_context] = lambda: fake_ctx
    client = TestClient(app)
    token = _mint_access_token(
        secret,
        user_id="admin-user",
        graph_id="U:admin-user",
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Admin-Key": "super-admin-key",
    }
    return client, headers, fake_ctx


def test_admin_status_reports_runtime_snapshot(monkeypatch, tmp_path):
    client, headers, _ = _mk_client(monkeypatch, tmp_path)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "backup_faim_20260501_120000.sql.gz").write_bytes(b"gz")
    (backup_dir / "raw_20260501_120000.tar.gz").write_bytes(b"raw")

    resp = client.get("/api/v1/admin/status", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["runtime"]["admin_key_configured"] is True
    assert body["backups"]
    assert body["backups"][0]["name"].startswith(("backup_faim_", "raw_"))


def test_admin_snapshot_create_uses_admin_bridge(monkeypatch, tmp_path):
    client, headers, fake_ctx = _mk_client(monkeypatch, tmp_path)

    resp = client.post(
        "/api/v1/admin/snapshot/create",
        headers=headers,
        json={"graph_id": "U:admin-user"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["details"]["graph_version"] == 4
    assert fake_ctx.snapshot_repo.items


def test_admin_alerts_surface_and_email_send(monkeypatch, tmp_path):
    client, headers, _ = _mk_client(monkeypatch, tmp_path)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "backup_faim_20250430_120000.sql.gz").write_bytes(b"gz")

    alerts_resp = client.get("/api/v1/admin/alerts", headers=headers)
    assert alerts_resp.status_code == 200
    alerts_body = alerts_resp.json()
    assert "alerts" in alerts_body
    assert "delivery" in alerts_body
    assert alerts_body["delivery"]["provider"] == "resend"
    assert alerts_body["delivery"]["enabled"] is True
    assert alerts_body["alerts"]

    calls = []

    class _FakeResponse:
        status_code = 200
        text = "ok"

    def _fake_post(*args, **kwargs):  # noqa: ANN001
        calls.append((args, kwargs))
        return _FakeResponse()

    monkeypatch.setattr("api.services.admin_alerts.httpx.post", _fake_post)

    send_resp = client.post("/api/v1/admin/alerts/send", headers=headers)
    assert send_resp.status_code == 200
    send_body = send_resp.json()
    assert send_body["sent"] is True
    assert send_body["details"]["alerts"]
    assert calls
