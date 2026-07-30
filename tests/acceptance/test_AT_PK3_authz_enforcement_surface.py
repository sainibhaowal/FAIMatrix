"""Phase K3 acceptance: authz enforcement surface wiring."""

from __future__ import annotations

import inspect

from fastapi.testclient import TestClient


def test_auth_middleware_exposes_k3_decision_api():
    from api.middleware.auth import AuthDecision, authenticate_tenant_key

    assert AuthDecision is not None
    assert callable(authenticate_tenant_key)


def test_deps_exposes_require_scopes():
    from api.deps import require_scopes

    assert callable(require_scopes)


def test_rate_limit_categories_include_api_v1():
    from api.middleware.ratelimit import ENDPOINT_CATEGORIES

    assert "/api/v1/ingest" in ENDPOINT_CATEGORIES
    assert "/api/v1/query" in ENDPOINT_CATEGORIES
    assert "/api/v1/events" in ENDPOINT_CATEGORIES


def test_feature_flags_include_k3_auth_controls():
    from runtime.feature_flags import FeatureFlags

    fields = FeatureFlags.__dataclass_fields__
    assert "auth_db_primary" in fields
    assert "auth_env_fallback_enabled" in fields
    assert "auth_scope_enforcement_enabled" in fields


def test_auth_middleware_sets_auth_context_fields():
    from api.middleware.auth import TenantAuthMiddleware

    source = inspect.getsource(TenantAuthMiddleware.dispatch)
    assert "request.state.auth_method" in source
    assert "request.state.auth_key_id" in source
    assert "request.state.auth_scopes" in source


def _mk_client(monkeypatch):
    from api.app import create_app
    from runtime.config import reset_config

    monkeypatch.setenv("FAIM_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_pk6":["key_pk6"]}')
    reset_config()
    return TestClient(create_app())


def test_k6_revoked_key_rejected_with_policy_code(monkeypatch):
    from api.middleware import auth as auth_module

    monkeypatch.setattr(
        auth_module,
        "authenticate_tenant_key",
        lambda tenant_id, api_key, request_id=None: auth_module.AuthDecision(
            valid=False,
            reason="revoked",
        ),
    )
    client = _mk_client(monkeypatch)
    resp = client.get(
        "/api/v1/api-keys",
        headers={"X-Tenant-Id": "tenant_pk6", "X-Api-Key": "key_pk6"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "auth_key_revoked"


def test_k6_expired_key_rejected_with_policy_code(monkeypatch):
    from api.middleware import auth as auth_module

    monkeypatch.setattr(
        auth_module,
        "authenticate_tenant_key",
        lambda tenant_id, api_key, request_id=None: auth_module.AuthDecision(
            valid=False,
            reason="expired",
        ),
    )
    client = _mk_client(monkeypatch)
    resp = client.get(
        "/api/v1/api-keys",
        headers={"X-Tenant-Id": "tenant_pk6", "X-Api-Key": "key_pk6"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "auth_key_expired"


def test_k6_missing_scope_returns_403(monkeypatch):
    from api.deps import FAIMContext, get_faim_context
    from api.middleware import auth as auth_module

    monkeypatch.setenv("FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED", "true")
    monkeypatch.setattr(
        auth_module,
        "authenticate_tenant_key",
        lambda tenant_id, api_key, request_id=None: auth_module.AuthDecision(
            valid=True,
            auth_method="api_key_db",
            key_id="faim_k_scope",
            scopes=["memory.read"],
        ),
    )

    app_client = _mk_client(monkeypatch)
    app_client.app.dependency_overrides[get_faim_context] = lambda: FAIMContext(
        tenant_id="tenant_pk6",
        request_id="req-pk6",
        session=None,
    )
    resp = app_client.get(
        "/api/v1/api-keys",
        headers={"X-Tenant-Id": "tenant_pk6", "X-Api-Key": "key_pk6"},
    )
    assert resp.status_code == 403


def test_k7_scope_allowed_matrix_path_returns_success(monkeypatch):
    from api.app import create_app
    from api.deps import FAIMContext, get_faim_context
    from api.middleware import auth as auth_module
    from api.routers import api_keys as api_keys_module
    from runtime.config import reset_config

    class _FakeRepo:
        def __init__(self, _session):  # noqa: ANN001
            pass

        def list_tenant_keys(self, tenant_id: str, include_revoked: bool = False):
            assert tenant_id == "tenant_pk7"
            assert include_revoked is False
            return []

    monkeypatch.setenv("FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED", "true")
    monkeypatch.setattr(api_keys_module, "AuthRepo", _FakeRepo)
    monkeypatch.setattr(
        auth_module,
        "authenticate_tenant_key",
        lambda tenant_id, api_key, request_id=None: auth_module.AuthDecision(
            valid=True,
            auth_method="api_key_db",
            key_id="faim_k_scope_ok",
            scopes=["keys.read", "memory.read"],
        ),
    )

    reset_config()
    app = create_app()
    app.dependency_overrides[get_faim_context] = lambda: FAIMContext(
        tenant_id="tenant_pk7",
        request_id="req-pk7",
        session=object(),
    )
    client = TestClient(app)
    resp = client.get(
        "/api/v1/api-keys",
        headers={"X-Tenant-Id": "tenant_pk7", "X-Api-Key": "key_pk7"},
    )
    assert resp.status_code == 200
