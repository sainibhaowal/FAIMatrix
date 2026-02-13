"""Phase K3 acceptance: authz enforcement surface wiring."""

from __future__ import annotations

import inspect


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

