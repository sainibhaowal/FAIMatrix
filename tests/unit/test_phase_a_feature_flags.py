"""Phase A: feature-flag guardrail tests."""

from __future__ import annotations

import os


def test_feature_flags_default_values(monkeypatch):
    from runtime.feature_flags import get_feature_flags

    monkeypatch.delenv("FAIM_ENCRYPTION_FAIL_CLOSED", raising=False)
    monkeypatch.delenv("FAIM_STORAGE_HARD_DELETE_ENABLED", raising=False)
    monkeypatch.delenv("FAIM_STORAGE_LIVE_JOB_STREAM_ENABLED", raising=False)
    monkeypatch.delenv("FAIM_STORAGE_CONTRACT_STRICT", raising=False)

    flags = get_feature_flags()
    assert flags.encryption_fail_closed is False
    assert flags.storage_hard_delete_enabled is False
    assert flags.storage_live_job_stream_enabled is False
    assert flags.storage_contract_strict is True


def test_validate_feature_flags_requires_jobs_for_hard_delete(monkeypatch):
    from runtime.feature_flags import FeatureFlags, validate_feature_flags

    monkeypatch.setenv("FAIM_ENABLE_JOBS", "false")
    flags = FeatureFlags(storage_hard_delete_enabled=True)
    errors, warnings = validate_feature_flags(flags)

    assert any("FAIM_STORAGE_HARD_DELETE_ENABLED requires FAIM_ENABLE_JOBS=true" in e for e in errors)
    assert isinstance(warnings, list)


def test_validate_feature_flags_requires_fail_closed_in_prod(monkeypatch):
    from runtime.feature_flags import FeatureFlags, validate_feature_flags

    monkeypatch.setenv("FAIM_ENV", "production")
    monkeypatch.setenv("FAIM_ENCRYPTION_AT_REST", "true")
    flags = FeatureFlags(encryption_fail_closed=False)
    errors, _warnings = validate_feature_flags(flags)

    assert any("requires FAIM_ENCRYPTION_FAIL_CLOSED=true" in e for e in errors)


def test_validate_feature_flags_requires_encryption_in_prod(monkeypatch):
    from runtime.feature_flags import FeatureFlags, validate_feature_flags

    monkeypatch.setenv("FAIM_ENV", "production")
    monkeypatch.setenv("FAIM_ENCRYPTION_AT_REST", "false")
    flags = FeatureFlags(encryption_fail_closed=True)
    errors, _warnings = validate_feature_flags(flags)

    assert any("requires FAIM_ENCRYPTION_AT_REST=true" in e for e in errors)


def test_runtime_config_parses_phase_a_flags(monkeypatch):
    from runtime.config import load_config, reset_config

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_a": ["key_a"]}')
    monkeypatch.setenv("FAIM_ENCRYPTION_FAIL_CLOSED", "true")
    monkeypatch.setenv("FAIM_STORAGE_HARD_DELETE_ENABLED", "false")
    monkeypatch.setenv("FAIM_STORAGE_LIVE_JOB_STREAM_ENABLED", "true")
    monkeypatch.setenv("FAIM_STORAGE_CONTRACT_STRICT", "true")

    reset_config()
    cfg = load_config()
    assert cfg.encryption_fail_closed is True
    assert cfg.storage_hard_delete_enabled is False
    assert cfg.storage_live_job_stream_enabled is True
    assert cfg.storage_contract_strict is True

    reset_config()
    for key in (
        "DATABASE_URL",
        "TENANT_KEYS_JSON",
        "FAIM_ENCRYPTION_FAIL_CLOSED",
        "FAIM_STORAGE_HARD_DELETE_ENABLED",
        "FAIM_STORAGE_LIVE_JOB_STREAM_ENABLED",
        "FAIM_STORAGE_CONTRACT_STRICT",
    ):
        os.environ.pop(key, None)
