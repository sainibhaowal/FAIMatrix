"""Phase K3 tests: auth middleware ordering, scopes, and rate-limit identity."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


class _DummyKeyRecord:
    def __init__(self, key_id: str, scopes: list[str]):
        self.key_id = key_id
        self.scopes = scopes


def test_authenticate_tenant_key_db_primary_success(monkeypatch):
    from api.middleware import auth as auth_module

    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "true")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "false")
    monkeypatch.setattr(
        auth_module,
        "_verify_db_tenant_key",
        lambda tenant_id, api_key: _DummyKeyRecord("faim_k1", ["memory.read"]),
    )

    decision = auth_module.authenticate_tenant_key("tenant_a", "key")
    assert decision.valid is True
    assert decision.auth_method == "api_key_db"
    assert decision.key_id == "faim_k1"
    assert decision.scopes == ["memory.read"]


def test_authenticate_tenant_key_env_fallback_only_when_enabled(monkeypatch):
    from api.middleware import auth as auth_module

    monkeypatch.setattr(auth_module, "_verify_db_tenant_key", lambda tenant_id, api_key: None)
    monkeypatch.setattr(auth_module, "_verify_env_tenant_key", lambda tenant_id, api_key: True)

    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "true")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "false")
    decision = auth_module.authenticate_tenant_key("tenant_a", "key")
    assert decision.valid is False

    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    decision = auth_module.authenticate_tenant_key("tenant_a", "key")
    assert decision.valid is True
    assert decision.auth_method == "api_key_env"


def test_validate_tenant_key_wrapper_returns_bool(monkeypatch):
    from api.middleware import auth as auth_module

    monkeypatch.setattr(auth_module, "authenticate_tenant_key", lambda tenant_id, api_key: auth_module.AuthDecision(valid=True))
    assert auth_module.validate_tenant_key("tenant_a", "key") is True


def test_require_scopes_enforced_for_api_key(monkeypatch):
    from api.deps import require_scopes

    monkeypatch.setenv("FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED", "true")

    dep = require_scopes(["memory.write"])
    request = SimpleNamespace(
        state=SimpleNamespace(auth_method="api_key_db", auth_scopes=["memory.read"])
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(dep(request))
    assert exc.value.status_code == 403


def test_require_scopes_jwt_compatibility_bypass(monkeypatch):
    from api.deps import require_scopes

    monkeypatch.setenv("FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED", "true")

    dep = require_scopes(["memory.write"])
    request = SimpleNamespace(state=SimpleNamespace(auth_method="jwt", auth_scopes=[]))
    asyncio.run(dep(request))


def test_rate_limiter_buckets_are_tenant_and_identity_scoped():
    from api.middleware.ratelimit import InMemoryRateLimiter

    limiter = InMemoryRateLimiter()
    limiter._limits["query"] = 1

    allowed_a1, _ = limiter.check_rate_limit("tenant_a", "query", identity="key:k1")
    allowed_a2, _ = limiter.check_rate_limit("tenant_a", "query", identity="key:k1")
    allowed_b1, _ = limiter.check_rate_limit("tenant_a", "query", identity="key:k2")

    assert allowed_a1 is True
    assert allowed_a2 is False
    assert allowed_b1 is True
