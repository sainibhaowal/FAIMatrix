# ======================================================================
# FAIM HyperSpeed P4.0 – Speed spec contracts
# Golden Edition test – do not silently relax without updating docs.
# ======================================================================

from typing import Iterable

from faim.speed.spec import (
    FaimSpeedProfile,
    SpeedBudget,
    adapt_speed_budget_to_system,
    get_speed_budget,
)


def _all_real_profiles() -> Iterable[FaimSpeedProfile]:
    """
    Helper: iterate over concrete profiles, ignoring DEFAULT/AUTO helper values
    if they exist in the enum.
    """
    for p in FaimSpeedProfile:
        name = p.name.upper()
        if name in {"DEFAULT", "AUTO"}:
            continue
        yield p


def test_p40_speed_budget_basics():
    """
    Every concrete speed profile must yield a sane SpeedBudget:
    - positive node limits
    - hot_ram_bytes > 0
    - dim >= 4
    """
    for profile in _all_real_profiles():
        budget = get_speed_budget(profile)
        assert isinstance(budget, SpeedBudget)
        assert budget.max_nodes_total >= budget.max_nodes_per_graph >= 1
        assert budget.hot_ram_bytes > 0
        assert budget.dim >= 4

        # latency budgets must be positive – we don't assert exact values,
        # only that the contract is coherent.
        assert budget.p95_retrieve_ms_1m > 0
        assert budget.p95_retrieve_ms_10m > 0


def test_p40_speed_budget_relative_ordering():
    """
    Sanity check relative expectations between profiles, if they exist:
    - SCALE should allow >= nodes than DEV
    - REALTIME should have tighter latency than DEV, if both exist.
    Tests are written defensively so they still pass if some profiles
    are not present.
    """
    profiles = {p.name: p for p in FaimSpeedProfile}

    if "CORE_DEV" in profiles and "CORE_SCALE" in profiles:
        dev = get_speed_budget(profiles["CORE_DEV"])
        scale = get_speed_budget(profiles["CORE_SCALE"])
        assert scale.max_nodes_total >= dev.max_nodes_total
        assert scale.max_nodes_per_graph >= dev.max_nodes_per_graph

    if "CORE_DEV" in profiles and "CORE_REALTIME" in profiles:
        dev = get_speed_budget(profiles["CORE_DEV"])
        rt = get_speed_budget(profiles["CORE_REALTIME"])
        assert rt.p95_retrieve_ms_1m <= dev.p95_retrieve_ms_1m
        assert rt.p95_retrieve_ms_10m <= dev.p95_retrieve_ms_10m


def test_p40_adapt_speed_budget_to_system_sane():
    """
    adapt_speed_budget_to_system() should always return a sane budget
    for the current machine; we don't check which profile it chose,
    only that the contract holds.
    """
    budget = adapt_speed_budget_to_system()
    assert isinstance(budget, SpeedBudget)
    assert budget.max_nodes_total >= budget.max_nodes_per_graph >= 1
    assert budget.hot_ram_bytes > 0
    assert budget.dim >= 4
