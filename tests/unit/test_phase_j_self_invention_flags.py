"""Phase J tests: self-invention feature flags and config wiring."""

from __future__ import annotations


def test_self_invention_feature_flags_env(monkeypatch):
    from runtime.feature_flags import get_feature_flags

    monkeypatch.setenv("FAIM_SELF_INVENT_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_INVENT_ON_EVOLVE", "false")
    monkeypatch.setenv("FAIM_SELF_INVENT_AFTER_UPLOAD", "true")

    flags = get_feature_flags()
    assert flags.self_invent_enabled is True
    assert flags.self_invent_on_evolve is False
    assert flags.self_invent_after_upload is True


def test_self_invention_config_knobs(monkeypatch):
    from runtime.config import load_config, reset_config

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_j":["k"]}')
    monkeypatch.setenv("FAIM_SELF_INVENT_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_INVENT_ON_EVOLVE", "true")
    monkeypatch.setenv("FAIM_SELF_INVENT_AFTER_UPLOAD", "false")
    monkeypatch.setenv("FAIM_SELF_INVENT_MAX_MACROS_PER_CYCLE", "7")
    monkeypatch.setenv("FAIM_SELF_INVENT_EVENT_WINDOW", "900")
    monkeypatch.setenv("FAIM_SELF_INVENT_MIN_COACTIVATION_COUNT", "4")
    monkeypatch.setenv("FAIM_SELF_INVENT_LAMBDA_THRESHOLD", "0.15")
    monkeypatch.setenv("FAIM_SELF_INVENT_MIN_REDUNDANCY_REDUCTION", "0.05")
    reset_config()

    cfg = load_config()
    assert cfg.self_invent_enabled is True
    assert cfg.self_invent_on_evolve is True
    assert cfg.self_invent_after_upload is False
    assert cfg.self_invent_max_macros_per_cycle == 7
    assert cfg.self_invent_event_window == 900
    assert cfg.self_invent_min_coactivation_count == 4
    assert abs(cfg.self_invent_lambda_threshold - 0.15) < 1e-9
    assert abs(cfg.self_invent_min_redundancy_reduction - 0.05) < 1e-9

