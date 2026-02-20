"""Phase R2 tests: central profile/persist policy resolver."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "profile,persist,index_enabled,durability_path",
    [
        ("strict", "strict", False, "sync_strict"),
        ("strict", "relaxed", False, "core_sync_secondary_async"),
        ("fast", "strict", True, "sync_strict"),
        ("fast", "relaxed", True, "core_sync_secondary_async"),
        ("relaxed", "strict", True, "sync_strict"),
        ("relaxed", "relaxed", True, "core_sync_secondary_async"),
    ],
)
def test_r2_resolver_ingest_matrix(profile, persist, index_enabled, durability_path):
    from orchestration.profile_persist_policy import (
        PolicyOperation,
        resolve_profile_persist_policy,
    )

    policy = resolve_profile_persist_policy(
        operation=PolicyOperation.INGEST,
        requested_profile=profile,
        requested_persist_mode=persist,
        compatibility_mode=False,
    )
    assert policy.operation == "ingest"
    assert policy.effective_profile == profile
    assert policy.effective_persist_mode == persist
    assert policy.index_enabled is index_enabled
    assert policy.durability_path == durability_path


@pytest.mark.parametrize(
    "profile,persist,expected_aggressiveness",
    [
        ("strict", "strict", "conservative"),
        ("strict", "relaxed", "conservative"),
        ("fast", "strict", "performance"),
        ("fast", "relaxed", "performance"),
        ("relaxed", "strict", "adaptive"),
        ("relaxed", "relaxed", "adaptive"),
    ],
)
def test_r2_resolver_evolve_matrix(profile, persist, expected_aggressiveness):
    from orchestration.profile_persist_policy import (
        PolicyOperation,
        resolve_profile_persist_policy,
    )

    policy = resolve_profile_persist_policy(
        operation=PolicyOperation.EVOLVE,
        requested_profile=profile,
        requested_persist_mode=persist,
        compatibility_mode=False,
    )
    assert policy.operation == "evolve"
    assert policy.effective_profile == profile
    assert policy.effective_persist_mode == persist
    assert policy.index_enabled is False
    assert policy.evolve_aggressiveness == expected_aggressiveness


def test_r2_resolver_coerces_invalid_values():
    from orchestration.profile_persist_policy import resolve_profile_persist_policy

    policy = resolve_profile_persist_policy(
        operation="ingest",
        requested_profile="invalid-profile",
        requested_persist_mode="invalid-persist",
        compatibility_mode=False,
    )
    assert policy.effective_profile == "strict"
    assert policy.effective_persist_mode == "relaxed"
    assert policy.coerced is True
    assert policy.coercion_reason == "invalid_profile,invalid_persist_mode"


def test_r2_resolver_reads_compat_mode_from_flags(monkeypatch):
    from orchestration.profile_persist_policy import resolve_profile_persist_policy

    monkeypatch.setenv("FAIM_PROFILE_PERSIST_COMPAT_MODE", "false")
    policy = resolve_profile_persist_policy(
        operation="evolve",
        requested_profile="strict",
        requested_persist_mode="relaxed",
    )
    assert policy.compatibility_mode is False


def test_r2_feature_flags_parse_profile_persist_compat(monkeypatch):
    from runtime.feature_flags import get_feature_flags

    monkeypatch.setenv("FAIM_PROFILE_PERSIST_COMPAT_MODE", "false")
    flags = get_feature_flags()
    assert flags.profile_persist_compat_mode is False


def test_r2_runtime_config_parses_profile_persist_compat(monkeypatch):
    from runtime.config import load_config, reset_config

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_r2":["k"]}')
    monkeypatch.setenv("FAIM_PROFILE_PERSIST_COMPAT_MODE", "false")

    reset_config()
    cfg = load_config()
    assert cfg.profile_persist_compat_mode is False
    reset_config()
