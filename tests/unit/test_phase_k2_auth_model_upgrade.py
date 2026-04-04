"""Phase K2 tests: auth key model upgrade and migration markers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from store.pg.models_auth import AuthKeyAuditLog, TenantApiKey
from store.pg.repos import auth_repo as auth_repo_module
from store.pg.repos.auth_repo import AuthRepo


def test_tenant_api_key_model_has_phase_k2_columns():
    cols = set(TenantApiKey.__table__.columns.keys())
    assert "scopes" in cols
    assert "expires_at" in cols
    assert "revoked_reason" in cols
    assert "created_by" in cols
    assert "last_used_at" in cols
    assert "rotated_from_key_id" in cols


def test_auth_key_audit_model_exists():
    cols = set(AuthKeyAuditLog.__table__.columns.keys())
    assert {"tenant_id", "key_id", "action", "actor", "request_id", "meta", "created_at"} <= cols


def test_tenant_key_active_state_checks_expiry_and_revocation():
    now = datetime.now(timezone.utc)

    active = TenantApiKey(
        tenant_id="t1",
        key_id="faim_a1",
        key_prefix="faim_a1",
        key_hash="hash",
        scopes=["memory.read"],
        expires_at=now + timedelta(minutes=10),
    )
    assert active.is_active() is True

    expired = TenantApiKey(
        tenant_id="t1",
        key_id="faim_a2",
        key_prefix="faim_a2",
        key_hash="hash",
        scopes=["memory.read"],
        expires_at=now - timedelta(seconds=1),
    )
    assert expired.is_active() is False

    revoked = TenantApiKey(
        tenant_id="t1",
        key_id="faim_a3",
        key_prefix="faim_a3",
        key_hash="hash",
        scopes=["memory.read"],
    )
    revoked.revoke("operator request")
    assert revoked.is_active() is False
    assert revoked.revoked_reason == "operator request"


class _DummySession:
    def __init__(self) -> None:
        self.added = []

    def add(self, obj) -> None:  # noqa: ANN001
        self.added.append(obj)

    def flush(self) -> None:
        return None


def test_auth_repo_create_tenant_key_adds_scopes_and_audit():
    session = _DummySession()
    repo = AuthRepo(session)  # type: ignore[arg-type]

    record, plaintext = repo.create_tenant_key(
        tenant_id="tenant_a",
        scopes=["memory.read", "memory.read", " keys.write ", "", "memory.write"],
        created_by="user:abc",
        audit_actor="user:abc",
        request_id="req-1",
    )

    assert plaintext.startswith(record.key_id + "_")
    assert record.scopes == ["memory.read", "keys.write", "memory.write"]
    assert record.created_by == "user:abc"

    # key record + audit record were both staged
    assert len(session.added) == 2
    assert isinstance(session.added[0], TenantApiKey)
    assert isinstance(session.added[1], AuthKeyAuditLog)
    assert session.added[1].action == "created"


def test_phase_k2_migration_and_schema_markers_present():
    migration_file = Path("faim_native/store/pg/migrations/0008_auth_key_scopes_audit.sql")
    assert migration_file.exists()

    schema = Path("faim_native/store/pg/schema.sql").read_text(encoding="utf-8")
    assert "tenant_api_keys" in schema
    assert "auth_key_audit_log" in schema
    assert "rotated_from_key_id" in schema


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return self

    def all(self):
        return list(self._rows)


class _FakeSessionVerify:
    def __init__(self, rows):
        self._rows = rows
        self.flushed = 0

    def query(self, _model):  # noqa: ANN001
        return _FakeQuery(self._rows)

    def flush(self):
        self.flushed += 1


def _mk_verify_record(
    *,
    tenant_id: str,
    key_id: str,
    key_hash: str,
    expires_at=None,  # noqa: ANN001
    revoked_at=None,  # noqa: ANN001
):
    record = TenantApiKey(
        tenant_id=tenant_id,
        key_id=key_id,
        key_prefix="faim_x",
        key_hash=key_hash,
        scopes=["memory.read"],
        expires_at=expires_at,
    )
    record.revoked_at = revoked_at
    return record


def test_k6_verify_tenant_key_with_reason_valid(monkeypatch):
    now = datetime.now(timezone.utc)
    rows = [
        _mk_verify_record(
            tenant_id="tenant_a",
            key_id="faim_k1",
            key_hash="valid_key",
            expires_at=now + timedelta(minutes=5),
        )
    ]
    session = _FakeSessionVerify(rows)
    repo = auth_repo_module.AuthRepo(session)  # type: ignore[arg-type]

    monkeypatch.setattr(auth_repo_module, "verify_api_key", lambda key, key_hash: key == key_hash)
    monkeypatch.setattr(auth_repo_module, "needs_rehash", lambda _hash: False)

    result = repo.verify_tenant_key_with_reason("tenant_a", "valid_key")
    assert result.valid is True
    assert result.reason is None
    assert result.matched_key_id == "faim_k1"
    assert result.record is not None
    assert result.record.last_used_at is not None
    assert session.flushed == 1


def test_k6_verify_tenant_key_with_reason_expired(monkeypatch):
    now = datetime.now(timezone.utc)
    rows = [
        _mk_verify_record(
            tenant_id="tenant_a",
            key_id="faim_k_exp",
            key_hash="expired_key",
            expires_at=now - timedelta(seconds=1),
        )
    ]
    session = _FakeSessionVerify(rows)
    repo = auth_repo_module.AuthRepo(session)  # type: ignore[arg-type]

    monkeypatch.setattr(auth_repo_module, "verify_api_key", lambda key, key_hash: key == key_hash)
    monkeypatch.setattr(auth_repo_module, "needs_rehash", lambda _hash: False)

    result = repo.verify_tenant_key_with_reason("tenant_a", "expired_key")
    assert result.valid is False
    assert result.reason == "expired"
    assert result.matched_key_id == "faim_k_exp"
    assert result.record is None


def test_k6_verify_tenant_key_with_reason_revoked(monkeypatch):
    now = datetime.now(timezone.utc)
    rows = [
        _mk_verify_record(
            tenant_id="tenant_a",
            key_id="faim_k_rev",
            key_hash="revoked_key",
            expires_at=now + timedelta(minutes=5),
            revoked_at=now - timedelta(minutes=1),
        )
    ]
    session = _FakeSessionVerify(rows)
    repo = auth_repo_module.AuthRepo(session)  # type: ignore[arg-type]

    monkeypatch.setattr(auth_repo_module, "verify_api_key", lambda key, key_hash: key == key_hash)
    monkeypatch.setattr(auth_repo_module, "needs_rehash", lambda _hash: False)

    result = repo.verify_tenant_key_with_reason("tenant_a", "revoked_key")
    assert result.valid is False
    assert result.reason == "revoked"
    assert result.matched_key_id == "faim_k_rev"
    assert result.record is None


def test_k6_verify_tenant_key_with_reason_invalid(monkeypatch):
    now = datetime.now(timezone.utc)
    rows = [
        _mk_verify_record(
            tenant_id="tenant_a",
            key_id="faim_k1",
            key_hash="other_key",
            expires_at=now + timedelta(minutes=5),
        )
    ]
    session = _FakeSessionVerify(rows)
    repo = auth_repo_module.AuthRepo(session)  # type: ignore[arg-type]

    monkeypatch.setattr(auth_repo_module, "verify_api_key", lambda key, key_hash: key == key_hash)
    monkeypatch.setattr(auth_repo_module, "needs_rehash", lambda _hash: False)

    result = repo.verify_tenant_key_with_reason("tenant_a", "missing")
    assert result.valid is False
    assert result.reason == "invalid_credentials"
    assert result.matched_key_id is None
