"""Phase K4 unit tests: API keys management router lifecycle."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.deps import FAIMContext, get_faim_context
from api.routers import api_keys as api_keys_module


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class _FakeAuditRecord:
    def __init__(self, tenant_id: str, key_id: str, action: str, actor: str | None = None) -> None:
        self.id = str(uuid4())
        self.tenant_id = tenant_id
        self.key_id = key_id
        self.action = action
        self.actor = actor
        self.request_id = "req-k4"
        self.meta = {}
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "key_id": self.key_id,
            "action": self.action,
            "actor": self.actor,
            "request_id": self.request_id,
            "meta": self.meta,
            "created_at": self.created_at.isoformat(),
        }


class _FakeKeyRecord:
    def __init__(
        self,
        *,
        tenant_id: str,
        key_id: str,
        key_prefix: str,
        scopes: list[str],
        created_by: str | None = None,
        expires_at: datetime | None = None,
        revoked_at: datetime | None = None,
        revoked_reason: str | None = None,
        rotated_from_key_id: str | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.key_id = key_id
        self.key_prefix = key_prefix
        self.scopes = scopes
        self.created_at = datetime.now(timezone.utc)
        self.created_by = created_by
        self.expires_at = expires_at
        self.revoked_at = revoked_at
        self.revoked_reason = revoked_reason
        self.rotated_from_key_id = rotated_from_key_id
        self.last_used_at = None

    def revoke(self, reason: str | None = None) -> None:
        self.revoked_at = datetime.now(timezone.utc)
        self.revoked_reason = reason

    def is_active(self) -> bool:
        if self.revoked_at:
            return False
        if self.expires_at and self.expires_at <= datetime.now(timezone.utc):
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "key_id": self.key_id,
            "key_prefix": self.key_prefix,
            "scopes": list(self.scopes),
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revoked_reason": self.revoked_reason,
            "rotated_from_key_id": self.rotated_from_key_id,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "is_active": self.is_active(),
        }


class _FakeAuthRepo:
    records: dict[str, _FakeKeyRecord] = {}
    audit: list[_FakeAuditRecord] = []
    counter: int = 0

    @classmethod
    def reset(cls) -> None:
        cls.records = {}
        cls.audit = []
        cls.counter = 0

    def __init__(self, session) -> None:  # noqa: ANN001
        self.session = session

    def _new_key_id(self) -> str:
        self.__class__.counter += 1
        return f"faim_k{self.__class__.counter:04d}"

    def append_key_audit(
        self,
        tenant_id: str,
        key_id: str,
        action: str,
        *,
        actor: str | None = None,
        request_id: str | None = None,
        meta: dict | None = None,
    ):
        record = _FakeAuditRecord(tenant_id=tenant_id, key_id=key_id, action=action, actor=actor)
        record.request_id = request_id
        record.meta = dict(meta or {})
        self.__class__.audit.append(record)
        return record

    def list_key_audit(
        self,
        tenant_id: str,
        *,
        key_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ):
        events = [event for event in self.__class__.audit if event.tenant_id == tenant_id]
        if key_id:
            events = [event for event in events if event.key_id == key_id]
        if action:
            events = [event for event in events if event.action == action]
        return list(reversed(events))[:limit]

    def create_tenant_key(
        self,
        tenant_id: str,
        prefix: str = "faim",
        *,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
        created_by: str | None = None,
        rotated_from_key_id: str | None = None,
        audit_actor: str | None = None,
        request_id: str | None = None,
    ):
        key_id = self._new_key_id()
        record = _FakeKeyRecord(
            tenant_id=tenant_id,
            key_id=key_id,
            key_prefix=f"{prefix}_{key_id[-4:]}",
            scopes=list(scopes or []),
            created_by=created_by,
            expires_at=expires_at,
            rotated_from_key_id=rotated_from_key_id,
        )
        self.__class__.records[key_id] = record
        self.append_key_audit(
            tenant_id=tenant_id,
            key_id=record.key_id,
            action="created",
            actor=audit_actor,
            request_id=request_id,
        )
        return record, f"{key_id}_plaintext"

    def list_tenant_keys(self, tenant_id: str, include_revoked: bool = False):
        values = [v for v in self.__class__.records.values() if v.tenant_id == tenant_id]
        if not include_revoked:
            values = [v for v in values if not v.revoked_at]
        return list(reversed(values))

    def get_tenant_key(self, tenant_id: str, key_id: str):
        record = self.__class__.records.get(key_id)
        if record and record.tenant_id == tenant_id:
            return record
        return None

    def revoke_tenant_key(
        self,
        tenant_id: str,
        key_id: str,
        *,
        reason: str | None = None,
        actor: str | None = None,
        request_id: str | None = None,
        meta: dict | None = None,
    ):
        record = self.get_tenant_key(tenant_id, key_id)
        if not record:
            return None
        record.revoke(reason)
        self.append_key_audit(
            tenant_id=tenant_id,
            key_id=key_id,
            action="revoked",
            actor=actor,
            request_id=request_id,
            meta=meta,
        )
        return record

    def rotate_tenant_key(
        self,
        tenant_id: str,
        key_id: str,
        *,
        prefix: str = "faim",
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
        reason: str | None = None,
        actor: str | None = None,
        request_id: str | None = None,
    ):
        old = self.get_tenant_key(tenant_id, key_id)
        if old is None or old.revoked_at is not None:
            return None

        next_scopes = list(scopes if scopes is not None else old.scopes)
        next_expiry = expires_at if expires_at is not None else old.expires_at
        new_record, plaintext = self.create_tenant_key(
            tenant_id=tenant_id,
            prefix=prefix,
            scopes=next_scopes,
            expires_at=next_expiry,
            created_by=actor,
            rotated_from_key_id=old.key_id,
            audit_actor=actor,
            request_id=request_id,
        )
        old.revoke(reason or "rotated")
        self.append_key_audit(
            tenant_id=tenant_id,
            key_id=old.key_id,
            action="rotated",
            actor=actor,
            request_id=request_id,
            meta={"new_key_id": new_record.key_id},
        )
        return old, new_record, plaintext


def _mk_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED", "false")
    _FakeAuthRepo.reset()
    monkeypatch.setattr(api_keys_module, "AuthRepo", _FakeAuthRepo)

    app = FastAPI()
    app.include_router(api_keys_module.router, prefix="/api/v1")

    async def _ctx_override():
        return FAIMContext(
            tenant_id="tenant_k4",
            request_id="req-k4",
            session=_FakeSession(),
        )

    app.dependency_overrides[get_faim_context] = _ctx_override
    return TestClient(app)


def test_k4_create_list_and_audit_flow(monkeypatch):
    client = _mk_client(monkeypatch)

    create = client.post(
        "/api/v1/api-keys",
        json={
            "label": "agent key",
            "scopes": ["keys.read", "memory.read"],
        },
    )
    assert create.status_code == 200
    created = create.json()
    assert created["plaintext_key"].endswith("_plaintext")
    assert "plaintext_key" not in created["key"]
    key_id = created["key"]["key_id"]

    listing = client.get("/api/v1/api-keys?include_revoked=true")
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 1
    assert body["items"][0]["key_id"] == key_id

    audit = client.get("/api/v1/api-keys/audit?limit=20")
    assert audit.status_code == 200
    audit_body = audit.json()
    assert audit_body["total"] >= 1
    assert any(item["action"] == "created" for item in audit_body["items"])


def test_k4_rotate_and_revoke_idempotency_guards(monkeypatch):
    client = _mk_client(monkeypatch)

    created = client.post(
        "/api/v1/api-keys",
        json={"scopes": ["keys.read", "keys.write"]},
    )
    assert created.status_code == 200
    original_key_id = created.json()["key"]["key_id"]

    rotated = client.post(
        f"/api/v1/api-keys/{original_key_id}/rotate",
        json={"reason": "rotation test"},
    )
    assert rotated.status_code == 200
    rotated_body = rotated.json()
    new_key_id = rotated_body["new_key"]["key_id"]
    assert new_key_id != original_key_id
    assert rotated_body["new_key"]["rotated_from_key_id"] == original_key_id
    assert sorted(rotated_body["new_key"]["scopes"]) == ["keys.read", "keys.write"]
    assert rotated_body["old_key"]["revoked_at"] is not None
    assert rotated_body["old_key"]["is_active"] is False

    # Old key is already revoked by rotate path.
    old_revoke = client.post(
        f"/api/v1/api-keys/{original_key_id}/revoke",
        json={"reason": "already revoked"},
    )
    assert old_revoke.status_code == 409

    revoke_new = client.post(
        f"/api/v1/api-keys/{new_key_id}/revoke",
        json={"reason": "cleanup"},
    )
    assert revoke_new.status_code == 200

    revoke_again = client.post(
        f"/api/v1/api-keys/{new_key_id}/revoke",
        json={"reason": "duplicate"},
    )
    assert revoke_again.status_code == 409


def test_k4_rejects_invalid_or_past_expiry(monkeypatch):
    client = _mk_client(monkeypatch)

    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    response = client.post(
        "/api/v1/api-keys",
        json={
            "scopes": ["keys.read"],
            "expires_at": past,
        },
    )
    assert response.status_code == 422
    assert "future" in str(response.json()).lower()


def test_k4_enforces_allowed_scope_names(monkeypatch):
    client = _mk_client(monkeypatch)

    response = client.post(
        "/api/v1/api-keys",
        json={
            "scopes": ["keys.read", "invalid.scope"],
        },
    )
    assert response.status_code == 422
    assert "invalid scope" in str(response.json()).lower()
