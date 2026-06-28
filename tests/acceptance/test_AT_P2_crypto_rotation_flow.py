"""Phase P2 acceptance: tenant crypto rotation workflow."""

from __future__ import annotations

import tempfile
from uuid import UUID, uuid4


def _mk_client(monkeypatch, tenant_id: str, api_key: str, raw_store_path: str):
    from api.app import create_app
    from api.middleware.auth import reload_tenant_keys
    from fastapi.testclient import TestClient
    from runtime.config import reset_config

    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "false")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("FAIM_ENCRYPTION_AT_REST", "true")
    monkeypatch.setenv("FAIM_ENCRYPTION_FAIL_CLOSED", "true")
    monkeypatch.setenv("FAIM_PAYLOAD_CIPHER", "envelope")
    monkeypatch.setenv("FAIM_RAW_STORE_PATH", raw_store_path)
    monkeypatch.setenv("TENANT_KEYS_JSON", f'{{"{tenant_id}":["{api_key}"]}}')
    reset_config()
    reload_tenant_keys()

    app = create_app()
    return TestClient(app), {"X-Tenant-Id": tenant_id, "X-Api-Key": api_key}


def _drain_jobs(monkeypatch, *, max_iterations: int = 12):
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


def test_storage_crypto_rotation_rewraps_master_key_and_preserves_payload(monkeypatch):
    from store.crypto.envelope import master_key_fingerprint
    from store.pg import session as pg_session
    from store.pg.models_crypto import TenantCryptoKey
    from store.pg.repos.raw_repo import RawRepo
    from store.raw.crypto import EnvelopeCipher
    from store.raw.encrypted_payload_store import EncryptedRawStore
    from store.raw.raw_store import RawStore

    tenant_id = "tenant_crypto_rotation"
    api_key = "crypto_rotation_key"
    old_key = "55" * 32
    new_key = "66" * 32
    raw_store_path = tempfile.mkdtemp(prefix="faim-crypto-rotation-")

    monkeypatch.setenv("FAIM_MASTER_KEY", old_key)
    client, headers = _mk_client(monkeypatch, tenant_id, api_key, raw_store_path)

    graph_id = f"crypto-rotation-{uuid4().hex[:8]}"
    upload = client.post(
        "/api/v1/storage/uploads",
        headers=headers,
        data={"graph_id": graph_id, "profile": "strict", "persist_mode": "relaxed"},
        files=[("files", ("rotation.txt", b"rotation payload", "text/plain"))],
    )
    assert upload.status_code == 200, upload.text
    upload_body = upload.json()
    raw_id = upload_body["files"][0]["raw_id"]

    _drain_jobs(monkeypatch)

    with pg_session.get_session() as session:
        row_before = (
            session.query(TenantCryptoKey)
            .filter(TenantCryptoKey.tenant_id == tenant_id)
            .first()
        )
        assert row_before is not None
        assert row_before.master_key_fingerprint == master_key_fingerprint(
            bytes.fromhex(old_key)
        )

    monkeypatch.setenv("FAIM_MASTER_KEY", new_key)
    monkeypatch.setenv("FAIM_MASTER_KEY_PREVIOUS_JSON", f'["{old_key}"]')

    rotation = client.post(
        "/api/v1/storage/crypto/rotation/jobs",
        headers=headers,
        json={"tenant_id": tenant_id, "dry_run": False, "reason": "key cutover"},
    )
    assert rotation.status_code == 200, rotation.text
    rotation_body = rotation.json()
    assert rotation_body["kind"] == "crypto_rotation"
    assert rotation_body["status"] == "pending"

    _drain_jobs(monkeypatch)

    status = client.get(
        f"/api/v1/storage/uploads/{upload_body['job_id']}", headers=headers
    )
    assert status.status_code == 200, status.text
    assert status.json()["status"] == "done"

    with pg_session.get_session() as session:
        row_after = (
            session.query(TenantCryptoKey)
            .filter(TenantCryptoKey.tenant_id == tenant_id)
            .first()
        )
        assert row_after is not None
        assert row_after.master_key_fingerprint == master_key_fingerprint(
            bytes.fromhex(new_key)
        )
        raw_repo = RawRepo(tenant_id=tenant_id)
        raw_ref = raw_repo.get_by_id(session, UUID(raw_id))
        assert raw_ref is not None

    monkeypatch.delenv("FAIM_MASTER_KEY_PREVIOUS_JSON", raising=False)
    fresh_cipher = EnvelopeCipher(
        tenant_id=tenant_id, session_factory=pg_session.get_session
    )
    fresh_store = EncryptedRawStore(
        inner=RawStore(raw_store_path),
        cipher=fresh_cipher,
        graph_id=tenant_id,
    )
    assert fresh_store.load(raw_ref, verify=True) == b"rotation payload"
