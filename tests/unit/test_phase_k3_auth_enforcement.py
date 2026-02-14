"""Phase K3 tests: auth middleware ordering, scopes, and rate-limit identity."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Request


def test_authenticate_tenant_key_db_primary_success(monkeypatch):
    from api.middleware import auth as auth_module

    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "true")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "false")
    monkeypatch.setattr(
        auth_module,
        "_verify_db_tenant_key",
        lambda tenant_id, api_key, request_id=None: auth_module.AuthDecision(
            valid=True,
            auth_method="api_key_db",
            key_id="faim_k1",
            scopes=["memory.read"],
        ),
    )

    decision = auth_module.authenticate_tenant_key("tenant_a", "key")
    assert decision.valid is True
    assert decision.auth_method == "api_key_db"
    assert decision.key_id == "faim_k1"
    assert decision.scopes == ["memory.read"]


def test_authenticate_tenant_key_env_fallback_only_when_enabled(monkeypatch):
    from api.middleware import auth as auth_module

    monkeypatch.setattr(
        auth_module,
        "_verify_db_tenant_key",
        lambda tenant_id, api_key, request_id=None: auth_module.AuthDecision(
            valid=False,
            reason="invalid_credentials",
        ),
    )
    monkeypatch.setattr(auth_module, "_verify_env_tenant_key", lambda tenant_id, api_key: True)

    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "true")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "false")
    decision = auth_module.authenticate_tenant_key("tenant_a", "key")
    assert decision.valid is False

    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")
    decision = auth_module.authenticate_tenant_key("tenant_a", "key")
    assert decision.valid is True
    assert decision.auth_method == "api_key_env"


def test_authenticate_tenant_key_does_not_env_fallback_for_revoked(monkeypatch):
    from api.middleware import auth as auth_module

    monkeypatch.setattr(
        auth_module,
        "_verify_db_tenant_key",
        lambda tenant_id, api_key, request_id=None: auth_module.AuthDecision(
            valid=False,
            auth_method="api_key_db",
            key_id="faim_k_revoked",
            reason="revoked",
        ),
    )
    monkeypatch.setattr(auth_module, "_verify_env_tenant_key", lambda tenant_id, api_key: True)
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "true")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "true")

    decision = auth_module.authenticate_tenant_key("tenant_a", "key")
    assert decision.valid is False
    assert decision.reason == "revoked"


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


def test_require_scopes_allows_when_scope_present(monkeypatch):
    from api.deps import require_scopes

    monkeypatch.setenv("FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED", "true")

    dep = require_scopes(["memory.read"])
    request = SimpleNamespace(
        state=SimpleNamespace(auth_method="api_key_db", auth_scopes=["memory.read", "keys.read"])
    )
    asyncio.run(dep(request))


def test_require_scopes_emits_scope_denied_audit(monkeypatch):
    from api.deps import require_scopes
    from api.middleware import auth as auth_module

    monkeypatch.setenv("FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED", "true")
    captured = {}

    def _capture(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(auth_module, "append_key_audit_best_effort", _capture)

    dep = require_scopes(["memory.write"])
    request = SimpleNamespace(
        state=SimpleNamespace(
            auth_method="api_key_db",
            auth_scopes=["memory.read"],
            tenant_id="tenant_a",
            auth_key_id="faim_k1",
            request_id="req-k6-1",
        ),
        headers={},
        method="POST",
        url=SimpleNamespace(path="/api/v1/memory/write"),
        scope={},
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(dep(request))

    assert exc.value.status_code == 403
    assert captured["action"] == auth_module.AUDIT_ACTION_DENIED_SCOPE
    assert captured["tenant_id"] == "tenant_a"
    assert captured["key_id"] == "faim_k1"


def test_tenant_auth_middleware_propagates_context(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.middleware import auth as auth_module
    from api.middleware.auth import TenantAuthMiddleware

    monkeypatch.setattr(
        auth_module,
        "authenticate_tenant_key",
        lambda tenant_id, api_key, request_id=None: auth_module.AuthDecision(
            valid=True,
            auth_method="api_key_db",
            key_id="faim_ctx_1",
            scopes=["memory.read", "memory.write"],
        ),
    )

    app = FastAPI()
    app.add_middleware(TenantAuthMiddleware)

    @app.get("/ctx")
    async def get_ctx(request: Request):
        return {
            "tenant_id": getattr(request.state, "tenant_id", None),
            "auth_method": getattr(request.state, "auth_method", None),
            "auth_key_id": getattr(request.state, "auth_key_id", None),
            "auth_scopes": getattr(request.state, "auth_scopes", []),
        }

    client = TestClient(app)
    response = client.get(
        "/ctx",
        headers={"X-Tenant-Id": "tenant_ctx", "X-Api-Key": "key_ctx"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == "tenant_ctx"
    assert payload["auth_method"] == "api_key_db"
    assert payload["auth_key_id"] == "faim_ctx_1"
    assert "memory.read" in payload["auth_scopes"]


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


def test_rate_limit_category_classification_is_method_aware():
    from api.middleware.ratelimit import classify_endpoint_category

    assert classify_endpoint_category("POST", "/api/v1/api-keys") == "api_keys_write"
    assert classify_endpoint_category("GET", "/api/v1/api-keys") == "api_keys_read"
    assert classify_endpoint_category("POST", "/api/v1/memory/search") == "memory_search"
    assert classify_endpoint_category("PATCH", "/api/v1/memory/123") == "memory_write"
