"""Phase R7 unit matrix: profile/persist policy resolution."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "operation,profile,persist,expected_index,expected_durability,expected_aggressiveness",
    [
        ("ingest", "strict", "strict", False, "sync_strict", "conservative"),
        ("ingest", "strict", "relaxed", False, "core_sync_secondary_async", "conservative"),
        ("ingest", "fast", "strict", True, "sync_strict", "performance"),
        ("ingest", "fast", "relaxed", True, "core_sync_secondary_async", "performance"),
        ("ingest", "relaxed", "strict", True, "sync_strict", "adaptive"),
        ("ingest", "relaxed", "relaxed", True, "core_sync_secondary_async", "adaptive"),
        ("evolve", "strict", "strict", False, "sync_strict", "conservative"),
        ("evolve", "strict", "relaxed", False, "core_sync_secondary_async", "conservative"),
        ("evolve", "fast", "strict", False, "sync_strict", "performance"),
        ("evolve", "fast", "relaxed", False, "core_sync_secondary_async", "performance"),
        ("evolve", "relaxed", "strict", False, "sync_strict", "adaptive"),
        ("evolve", "relaxed", "relaxed", False, "core_sync_secondary_async", "adaptive"),
    ],
)
def test_r7_policy_matrix_all_combinations(
    operation,
    profile,
    persist,
    expected_index,
    expected_durability,
    expected_aggressiveness,
):
    from orchestration.profile_persist_policy import (
        PolicyOperation,
        resolve_profile_persist_policy,
    )

    policy = resolve_profile_persist_policy(
        operation=(
            PolicyOperation.INGEST
            if operation == "ingest"
            else PolicyOperation.EVOLVE
        ),
        requested_profile=profile,
        requested_persist_mode=persist,
        compatibility_mode=False,
    )

    assert policy.operation == operation
    assert policy.requested_profile == profile
    assert policy.requested_persist_mode == persist
    assert policy.effective_profile == profile
    assert policy.effective_persist_mode == persist
    assert policy.coerced is False
    assert policy.coercion_reason is None
    assert policy.index_enabled is expected_index
    assert policy.durability_path == expected_durability
    assert policy.evolve_aggressiveness == expected_aggressiveness


@pytest.mark.parametrize(
    "profile,expected_scale,expected_merge,expected_age,expected_touch,expected_similarity,expected_invent_mode,expected_default,expected_cap",
    [
        ("strict", 0.6, 0.97, 14.0, 1, 0.99, "conservative", False, 1),
        ("fast", 0.8, 0.95, 7.0, 1, 0.98, "balanced", True, 2),
        ("relaxed", 1.0, 0.92, 3.0, 2, 0.95, "aggressive", True, 6),
    ],
)
def test_r7_policy_evolve_knob_matrix_when_compat_disabled(
    profile,
    expected_scale,
    expected_merge,
    expected_age,
    expected_touch,
    expected_similarity,
    expected_invent_mode,
    expected_default,
    expected_cap,
):
    from orchestration.profile_persist_policy import (
        PolicyOperation,
        resolve_profile_persist_policy,
    )

    policy = resolve_profile_persist_policy(
        operation=PolicyOperation.EVOLVE,
        requested_profile=profile,
        requested_persist_mode="relaxed",
        compatibility_mode=False,
    )

    assert policy.effective_profile == profile
    assert policy.evolve_action_budget_scale == pytest.approx(expected_scale)
    assert policy.evolve_merge_threshold == pytest.approx(expected_merge)
    assert policy.evolve_prune_min_age_days == pytest.approx(expected_age)
    assert policy.evolve_prune_max_touch_count == expected_touch
    assert policy.evolve_prune_similarity_threshold == pytest.approx(expected_similarity)
    assert policy.evolve_invention_mode == expected_invent_mode
    assert policy.evolve_invention_requested_default is expected_default
    assert policy.evolve_invention_max_macros_cap == expected_cap


@pytest.mark.parametrize("profile", ["strict", "fast", "relaxed"])
@pytest.mark.parametrize("persist", ["strict", "relaxed"])
def test_r7_policy_compat_mode_keeps_legacy_evolve_knob_envelope(profile, persist):
    from orchestration.profile_persist_policy import (
        PolicyOperation,
        resolve_profile_persist_policy,
    )

    policy = resolve_profile_persist_policy(
        operation=PolicyOperation.EVOLVE,
        requested_profile=profile,
        requested_persist_mode=persist,
        compatibility_mode=True,
    )

    assert policy.compatibility_mode is True
    assert policy.effective_profile == profile
    assert policy.effective_persist_mode == persist
    assert policy.evolve_action_budget_scale == pytest.approx(1.0)
    assert policy.evolve_merge_threshold == pytest.approx(0.95)
    assert policy.evolve_prune_min_age_days == pytest.approx(7.0)
    assert policy.evolve_prune_max_touch_count == 1
    assert policy.evolve_prune_similarity_threshold == pytest.approx(0.98)
    assert policy.evolve_invention_mode == "runtime_default"
    assert policy.evolve_invention_requested_default is True
    assert policy.evolve_invention_max_macros_cap == 3


@pytest.mark.parametrize(
    "requested_profile,requested_persist,expected_profile,expected_persist,expected_reason",
    [
        ("invalid", "relaxed", "strict", "relaxed", "invalid_profile"),
        ("strict", "invalid", "strict", "relaxed", "invalid_persist_mode"),
        ("INVALID", "INVALID", "strict", "relaxed", "invalid_profile,invalid_persist_mode"),
    ],
)
def test_r7_policy_coercion_requested_vs_effective(
    requested_profile,
    requested_persist,
    expected_profile,
    expected_persist,
    expected_reason,
):
    from orchestration.profile_persist_policy import (
        PolicyOperation,
        resolve_profile_persist_policy,
    )

    policy = resolve_profile_persist_policy(
        operation=PolicyOperation.INGEST,
        requested_profile=requested_profile,
        requested_persist_mode=requested_persist,
        compatibility_mode=False,
    )

    assert policy.requested_profile == requested_profile.strip().lower()
    assert policy.requested_persist_mode == requested_persist.strip().lower()
    assert policy.effective_profile == expected_profile
    assert policy.effective_persist_mode == expected_persist
    assert policy.coerced is True
    assert policy.coercion_reason == expected_reason

