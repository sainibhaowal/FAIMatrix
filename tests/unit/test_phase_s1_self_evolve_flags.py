"""Phase S1 tests: self-evolve contract and guardrails."""

from __future__ import annotations

import pytest


def test_feature_flags_parse_self_evolve_env(monkeypatch):
    from runtime.feature_flags import get_feature_flags

    monkeypatch.setenv("FAIM_SELF_EVOLVE_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_TRIGGER_MODE", "periodic")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MIN_INTERVAL_SECONDS", "600")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MIN_VERSION_DELTA", "2")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MAX_ACTIONS", "40")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_SCAN_INTERVAL_SECONDS", "120")

    flags = get_feature_flags()
    assert flags.self_evolve_enabled is True
    assert flags.self_evolve_trigger_mode == "periodic"
    assert flags.self_evolve_min_interval_seconds == 600
    assert flags.self_evolve_min_version_delta == 2
    assert flags.self_evolve_max_actions == 40
    assert flags.self_evolve_scan_interval_seconds == 120


def test_validate_feature_flags_rejects_invalid_trigger_mode(monkeypatch):
    from runtime.feature_flags import FeatureFlags, validate_feature_flags

    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true")
    flags = FeatureFlags(self_evolve_trigger_mode="unexpected_mode")
    errors, _warnings = validate_feature_flags(flags)
    assert any("FAIM_SELF_EVOLVE_TRIGGER_MODE must be one of" in err for err in errors)


def test_validate_feature_flags_requires_jobs_for_async_self_evolve(monkeypatch):
    from runtime.feature_flags import FeatureFlags, validate_feature_flags

    monkeypatch.setenv("FAIM_ENABLE_JOBS", "false")
    flags = FeatureFlags(self_evolve_enabled=True, self_evolve_trigger_mode="periodic")
    errors, _warnings = validate_feature_flags(flags)
    assert any("requires FAIM_ENABLE_JOBS=true" in err for err in errors)


def test_validate_feature_flags_manual_self_evolve_without_jobs_is_valid(monkeypatch):
    from runtime.feature_flags import FeatureFlags, validate_feature_flags

    monkeypatch.setenv("FAIM_ENABLE_JOBS", "false")
    flags = FeatureFlags(self_evolve_enabled=True, self_evolve_trigger_mode="manual")
    errors, _warnings = validate_feature_flags(flags)
    assert not any("FAIM_SELF_EVOLVE_ENABLED" in err for err in errors)


def test_runtime_config_parses_self_evolve_knobs(monkeypatch):
    from runtime.config import load_config, reset_config

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_s1":["k"]}')
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_TRIGGER_MODE", "hybrid")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MIN_INTERVAL_SECONDS", "450")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MIN_VERSION_DELTA", "3")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MAX_ACTIONS", "28")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_SCAN_INTERVAL_SECONDS", "90")

    reset_config()
    cfg = load_config()
    assert cfg.self_evolve_enabled is True
    assert cfg.self_evolve_trigger_mode == "hybrid"
    assert cfg.self_evolve_min_interval_seconds == 450
    assert cfg.self_evolve_min_version_delta == 3
    assert cfg.self_evolve_max_actions == 28
    assert cfg.self_evolve_scan_interval_seconds == 90
    reset_config()


def test_runtime_config_rejects_self_evolve_bounds(monkeypatch):
    from runtime.config import load_config, reset_config

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_s1":["k"]}')
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MIN_INTERVAL_SECONDS", "10")

    reset_config()
    with pytest.raises(ValueError) as exc:
        load_config()
    assert "FAIM_SELF_EVOLVE_MIN_INTERVAL_SECONDS must be >= 30" in str(exc.value)
    reset_config()


def test_runtime_config_rejects_self_evolve_scan_interval_bounds(monkeypatch):
    from runtime.config import load_config, reset_config

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_s1":["k"]}')
    monkeypatch.setenv("FAIM_SELF_EVOLVE_SCAN_INTERVAL_SECONDS", "5")

    reset_config()
    with pytest.raises(ValueError) as exc:
        load_config()
    assert "FAIM_SELF_EVOLVE_SCAN_INTERVAL_SECONDS must be >= 30" in str(exc.value)
    reset_config()


def test_runtime_config_rejects_invalid_self_evolve_trigger_mode(monkeypatch):
    from runtime.config import load_config, reset_config

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_s1":["k"]}')
    monkeypatch.setenv("FAIM_SELF_EVOLVE_TRIGGER_MODE", "unknown_mode")

    reset_config()
    with pytest.raises(ValueError) as exc:
        load_config()
    assert "FAIM_SELF_EVOLVE_TRIGGER_MODE must be one of" in str(exc.value)
    reset_config()


def test_runtime_config_requires_jobs_for_non_manual_self_evolve(monkeypatch):
    from runtime.config import load_config, reset_config

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_s1":["k"]}')
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "false")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_TRIGGER_MODE", "post_upload")

    reset_config()
    with pytest.raises(ValueError) as exc:
        load_config()
    assert "requires FAIM_ENABLE_JOBS=true" in str(exc.value)
    reset_config()


def test_guardrail_summary_reports_disabled_by_default(monkeypatch):
    from orchestration.self_evolve_scheduler import (
        build_self_evolve_guardrail_summary,
    )

    monkeypatch.delenv("FAIM_SELF_EVOLVE_ENABLED", raising=False)
    monkeypatch.delenv("FAIM_SELF_INVENT_ENABLED", raising=False)
    monkeypatch.delenv("FAIM_SELF_INVENT_AFTER_UPLOAD", raising=False)
    monkeypatch.delenv("FAIM_ENABLE_JOBS", raising=False)

    summary = build_self_evolve_guardrail_summary()
    assert summary.automation_path == "disabled"
    assert summary.automation_label == "Disabled"
    assert summary.automation_enabled is False
    assert summary.self_evolve_enabled is False


def test_guardrail_summary_reports_hybrid_worker(monkeypatch):
    from orchestration.self_evolve_scheduler import (
        build_self_evolve_guardrail_summary,
    )

    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_TRIGGER_MODE", "hybrid")
    monkeypatch.setenv("FAIM_SELF_INVENT_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_INVENT_ON_EVOLVE", "true")
    monkeypatch.setenv("FAIM_SELF_INVENT_AFTER_UPLOAD", "false")

    summary = build_self_evolve_guardrail_summary()
    assert summary.automation_path == "hybrid_worker"
    assert summary.automation_label == "Upload + periodic"
    assert summary.automation_enabled is True
    assert summary.guardrail_reason == "hybrid_worker"


def test_guardrail_summary_reports_legacy_upload_compat(monkeypatch):
    from orchestration.self_evolve_scheduler import (
        build_self_evolve_guardrail_summary,
    )

    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_ENABLED", "false")
    monkeypatch.setenv("FAIM_SELF_INVENT_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_INVENT_AFTER_UPLOAD", "true")

    summary = build_self_evolve_guardrail_summary()
    assert summary.automation_path == "legacy_post_upload_compat"
    assert summary.automation_label == "Legacy after-upload compatibility"
    assert summary.automation_enabled is True
    assert summary.guardrail_reason == "legacy_upload_compat"
