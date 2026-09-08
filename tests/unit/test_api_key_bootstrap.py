"""Tests for one-time DB API-key bootstrap safety and idempotence."""

from __future__ import annotations

import pytest

BOOTSTRAP_KEY_A = "faim_bootstrap_000001_0123456789abcdef"
BOOTSTRAP_KEY_B = "faim_bootstrap_000002_fedcba9876543210"


def test_bootstrap_imports_argon2_hash_and_is_idempotent(db_session):
    from runtime.api_key_bootstrap import (
        DEFAULT_BOOTSTRAP_SCOPES,
        bootstrap_tenant_api_keys,
    )
    from runtime.secrets import verify_api_key
    from store.pg.models_auth import AuthKeyAuditLog, TenantApiKey

    payload = {"tenant_bootstrap": [BOOTSTRAP_KEY_A]}
    first = bootstrap_tenant_api_keys(db_session, payload, apply=True)
    db_session.commit()

    assert first.requested == 1
    assert first.imported == 1
    assert first.already_present == 0
    record = (
        db_session.query(TenantApiKey)
        .filter(TenantApiKey.tenant_id == "tenant_bootstrap")
        .one()
    )
    assert record.key_hash.startswith("$argon2id$")
    assert BOOTSTRAP_KEY_A not in record.key_hash
    assert BOOTSTRAP_KEY_A not in record.key_id
    assert record.key_prefix == "bootstrap"
    assert record.scopes == list(DEFAULT_BOOTSTRAP_SCOPES)
    assert verify_api_key(BOOTSTRAP_KEY_A, record.key_hash)

    audit = (
        db_session.query(AuthKeyAuditLog)
        .filter(AuthKeyAuditLog.tenant_id == "tenant_bootstrap")
        .one()
    )
    assert audit.action == "bootstrapped"
    assert audit.meta["source"] == "FAIM_TENANT_KEY_BOOTSTRAP_JSON"
    assert BOOTSTRAP_KEY_A not in str(audit.meta)

    second = bootstrap_tenant_api_keys(db_session, payload, apply=True)
    db_session.commit()
    assert second.requested == 1
    assert second.imported == 0
    assert second.already_present == 1
    assert (
        db_session.query(TenantApiKey)
        .filter(TenantApiKey.tenant_id == "tenant_bootstrap")
        .count()
        == 1
    )
    assert (
        db_session.query(AuthKeyAuditLog)
        .filter(AuthKeyAuditLog.tenant_id == "tenant_bootstrap")
        .count()
        == 1
    )


def test_bootstrap_dry_run_does_not_write(db_session):
    from runtime.api_key_bootstrap import bootstrap_tenant_api_keys
    from store.pg.models_auth import TenantApiKey

    result = bootstrap_tenant_api_keys(
        db_session,
        {"tenant_dry_run": [BOOTSTRAP_KEY_A]},
        apply=False,
    )
    db_session.rollback()

    assert result.dry_run is True
    assert result.requested == 1
    assert result.would_import == 1
    assert result.imported == 0
    assert result.already_present == 0
    assert (
        db_session.query(TenantApiKey)
        .filter(TenantApiKey.tenant_id == "tenant_dry_run")
        .count()
        == 0
    )


def test_bootstrap_does_not_reactivate_revoked_key(db_session):
    from runtime.api_key_bootstrap import bootstrap_tenant_api_keys
    from runtime.secrets import hash_api_key
    from store.pg.models_auth import TenantApiKey

    existing = TenantApiKey(
        tenant_id="tenant_revoked",
        key_id="existing_bootstrap_key",
        key_prefix="bootstrap",
        key_hash=hash_api_key(BOOTSTRAP_KEY_A),
        scopes=["keys.read"],
    )
    existing.revoke("intentional test revocation")
    db_session.add(existing)
    db_session.commit()

    result = bootstrap_tenant_api_keys(
        db_session,
        {"tenant_revoked": [BOOTSTRAP_KEY_A]},
        apply=True,
    )
    db_session.commit()

    assert result.imported == 0
    assert result.already_present == 1
    stored = db_session.query(TenantApiKey).filter_by(key_id=existing.key_id).one()
    assert stored.revoked_at is not None
    assert (
        db_session.query(TenantApiKey).filter_by(tenant_id="tenant_revoked").count()
        == 1
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"bad tenant": [BOOTSTRAP_KEY_A]},
        {"tenant_valid": ["contains whitespace key 123456"]},
        {"tenant_valid": ["too-short"]},
        {
            "tenant_a": [BOOTSTRAP_KEY_A],
            "tenant_b": [BOOTSTRAP_KEY_A],
        },
    ],
)
def test_bootstrap_rejects_invalid_input_without_echoing_key(payload):
    from runtime.api_key_bootstrap import (
        BootstrapValidationError,
        normalize_bootstrap_payload,
    )

    with pytest.raises(BootstrapValidationError) as exc:
        normalize_bootstrap_payload(payload)

    assert BOOTSTRAP_KEY_A not in str(exc.value)


def test_bootstrap_environment_is_explicit_and_never_reads_legacy_key_env(monkeypatch):
    from runtime.api_key_bootstrap import (
        BootstrapValidationError,
        load_bootstrap_from_environment,
    )

    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_legacy":["legacy-secret"]}')
    monkeypatch.delenv("FAIM_TENANT_KEY_BOOTSTRAP_JSON", raising=False)

    with pytest.raises(BootstrapValidationError) as exc:
        load_bootstrap_from_environment()

    assert "FAIM_TENANT_KEY_BOOTSTRAP_JSON" in str(exc.value)
    assert "legacy-secret" not in str(exc.value)


def test_production_bootstrap_runtime_fails_closed_for_conflicting_auth_flags():
    from runtime.api_key_bootstrap import (
        BootstrapValidationError,
        validate_bootstrap_runtime,
    )

    production_env = {
        "FAIM_MODE": "development",
        "FAIM_ENV": "production",
        "FAIM_AUTH_DB_PRIMARY": "true",
        "FAIM_AUTH_ENV_FALLBACK_ENABLED": "false",
        "FAIM_ALLOW_DEV_AUTH_BYPASS": "false",
    }
    validate_bootstrap_runtime(production_env)

    production_env["FAIM_AUTH_ENV_FALLBACK_ENABLED"] = "true"
    with pytest.raises(BootstrapValidationError) as exc:
        validate_bootstrap_runtime(production_env)
    assert "FALLBACK" in str(exc.value)


def test_production_config_allows_no_legacy_tenant_keys_in_db_only_mode(monkeypatch):
    from runtime.config import load_config, reset_config

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("FAIM_MODE", "development")
    monkeypatch.setenv("FAIM_ENV", "production")
    monkeypatch.setenv("FAIM_ENCRYPTION_AT_REST", "true")
    monkeypatch.setenv("FAIM_ENCRYPTION_FAIL_CLOSED", "true")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "true")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "false")
    monkeypatch.setenv("FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED", "true")
    monkeypatch.setenv("FAIM_ALLOW_DEV_AUTH_BYPASS", "false")
    monkeypatch.delenv("TENANT_KEYS_JSON", raising=False)
    monkeypatch.delenv("FAIM_TENANT_KEY_BOOTSTRAP_JSON", raising=False)

    reset_config()
    try:
        config = load_config()
        assert config.tenant_keys == {}
    finally:
        reset_config()


def test_production_config_rejects_bootstrap_secret_in_long_running_process(
    monkeypatch,
):
    from runtime.config import load_config, reset_config

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("FAIM_MODE", "production")
    monkeypatch.setenv("FAIM_ENCRYPTION_AT_REST", "true")
    monkeypatch.setenv("FAIM_ENCRYPTION_FAIL_CLOSED", "true")
    monkeypatch.setenv("FAIM_AUTH_DB_PRIMARY", "true")
    monkeypatch.setenv("FAIM_AUTH_ENV_FALLBACK_ENABLED", "false")
    monkeypatch.setenv("FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED", "true")
    monkeypatch.setenv("FAIM_ALLOW_DEV_AUTH_BYPASS", "false")
    monkeypatch.setenv(
        "FAIM_TENANT_KEY_BOOTSTRAP_JSON",
        '{"tenant_bootstrap":["faim_bootstrap_000001_0123456789abcdef"]}',
    )
    monkeypatch.delenv("TENANT_KEYS_JSON", raising=False)

    reset_config()
    try:
        with pytest.raises(ValueError) as exc:
            load_config()
        assert "bootstrap-only" in str(exc.value)
        assert BOOTSTRAP_KEY_A not in str(exc.value)
    finally:
        reset_config()
