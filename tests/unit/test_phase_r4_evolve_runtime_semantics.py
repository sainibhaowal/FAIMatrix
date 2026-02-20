"""Phase R4 unit checks: evolve runtime profile/persist semantics realization."""

from __future__ import annotations

import pytest


class _DummySession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class _DummyRepo:
    def __init__(self, session):
        self.session = session
        self.tenant_id = "tenant_r4"


class _DummyEventRepo(_DummyRepo):
    def __init__(self, session):
        super().__init__(session)
        self.events = []

    def emit(self, session, graph_id, kind, payload):  # noqa: ARG002
        self.events.append((kind, payload))


class _DummyGraphVersionRepo(_DummyRepo):
    def get(self, _session, _graph_id):
        return None


@pytest.mark.parametrize(
    "profile,scale,merge,age,touch,sim,invent_mode,invent_default,cap",
    [
        ("strict", 0.6, 0.97, 14.0, 1, 0.99, "conservative", False, 1),
        ("fast", 0.8, 0.95, 7.0, 1, 0.98, "balanced", True, 2),
        ("relaxed", 1.0, 0.92, 3.0, 2, 0.95, "aggressive", True, 6),
    ],
)
def test_r4_resolver_evolve_knobs_matrix(
    profile,
    scale,
    merge,
    age,
    touch,
    sim,
    invent_mode,
    invent_default,
    cap,
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
    assert policy.evolve_action_budget_scale == pytest.approx(scale)
    assert policy.evolve_merge_threshold == pytest.approx(merge)
    assert policy.evolve_prune_min_age_days == pytest.approx(age)
    assert policy.evolve_prune_max_touch_count == touch
    assert policy.evolve_prune_similarity_threshold == pytest.approx(sim)
    assert policy.evolve_invention_mode == invent_mode
    assert policy.evolve_invention_requested_default is invent_default
    assert policy.evolve_invention_max_macros_cap == cap


def test_r4_run_evolve_applies_policy_knobs_to_core(monkeypatch):
    from core.dynamics.evolution_native import EvolutionResult
    from orchestration import evolve_flow

    monkeypatch.setenv("FAIM_PROFILE_PERSIST_COMPAT_MODE", "false")

    class _Cfg:
        self_evolve_max_actions = 10
        self_invent_lambda_threshold = 0.3
        self_invent_min_redundancy_reduction = 0.01
        self_invent_max_macros_per_cycle = 5

    captured = {}

    def _fake_evolve_once(**kwargs):
        captured.update(kwargs)
        return EvolutionResult(
            graph_version=3,
            merges=0,
            prunes=0,
            inventions=0,
            events_emitted=2,
            skip_reason="insufficient_nodes",
        )

    monkeypatch.setattr("runtime.config.get_config", lambda: _Cfg())
    monkeypatch.setattr("core.dynamics.evolution_native.evolve_once", _fake_evolve_once)
    monkeypatch.setattr(evolve_flow, "_mark_self_evolved_state", lambda **_kwargs: None)

    session = _DummySession()
    node_repo = _DummyRepo(session)
    edge_repo = _DummyRepo(session)
    event_repo = _DummyEventRepo(session)
    gv_repo = _DummyGraphVersionRepo(session)

    result = evolve_flow.run_evolve(
        graph_id="graph_r4",
        tenant_id="tenant_r4",
        session=session,
        profile="strict",
        persist_mode="strict",
        node_repo=node_repo,
        edge_repo=edge_repo,
        event_repo=event_repo,
        gv_repo=gv_repo,
    )

    assert result.status == "completed"
    assert captured["max_actions"] == 6
    assert captured["merge_threshold"] == pytest.approx(0.97)
    assert captured["prune_policy"].min_age_days == pytest.approx(14.0)
    assert captured["prune_policy"].max_touch_count == 1
    assert captured["prune_policy"].min_similarity_for_redundancy == pytest.approx(0.99)
    assert captured["self_invent_requested"] is False
    assert captured["invention_overrides"]["max_macros_per_cycle"] == 1
    assert result.completion_mode == "sync_strict"
    assert result.state_update_status == "completed_sync"


def test_r4_run_evolve_relaxed_nonfatal_when_state_update_fails(monkeypatch):
    from core.dynamics.evolution_native import EvolutionResult
    from orchestration import evolve_flow

    monkeypatch.setenv("FAIM_PROFILE_PERSIST_COMPAT_MODE", "false")

    class _Cfg:
        self_evolve_max_actions = 10
        self_invent_lambda_threshold = 0.3
        self_invent_min_redundancy_reduction = 0.01
        self_invent_max_macros_per_cycle = 5

    monkeypatch.setattr("runtime.config.get_config", lambda: _Cfg())
    monkeypatch.setattr(
        "core.dynamics.evolution_native.evolve_once",
        lambda **_kwargs: EvolutionResult(
            graph_version=5,
            merges=1,
            prunes=0,
            inventions=0,
            events_emitted=3,
            skip_reason=None,
        ),
    )

    def _raise_state(**_kwargs):
        raise RuntimeError("state_update_failed")

    monkeypatch.setattr(evolve_flow, "_mark_self_evolved_state", _raise_state)

    session = _DummySession()
    node_repo = _DummyRepo(session)
    edge_repo = _DummyRepo(session)
    event_repo = _DummyEventRepo(session)
    gv_repo = _DummyGraphVersionRepo(session)

    result = evolve_flow.run_evolve(
        graph_id="graph_r4_relaxed",
        tenant_id="tenant_r4",
        session=session,
        profile="relaxed",
        persist_mode="relaxed",
        node_repo=node_repo,
        edge_repo=edge_repo,
        event_repo=event_repo,
        gv_repo=gv_repo,
    )

    assert result.status == "completed"
    assert result.completion_mode == "core_sync_state_best_effort"
    assert result.state_update_status == "best_effort_failed_nonfatal"
    assert "state_update_failed" in (result.state_update_error or "")
    assert session.commits >= 1


def test_r4_run_evolve_strict_fails_when_state_update_fails(monkeypatch):
    from core.dynamics.evolution_native import EvolutionResult
    from orchestration import evolve_flow

    monkeypatch.setenv("FAIM_PROFILE_PERSIST_COMPAT_MODE", "false")

    class _Cfg:
        self_evolve_max_actions = 10
        self_invent_lambda_threshold = 0.3
        self_invent_min_redundancy_reduction = 0.01
        self_invent_max_macros_per_cycle = 5

    monkeypatch.setattr("runtime.config.get_config", lambda: _Cfg())
    monkeypatch.setattr(
        "core.dynamics.evolution_native.evolve_once",
        lambda **_kwargs: EvolutionResult(
            graph_version=9,
            merges=0,
            prunes=0,
            inventions=0,
            events_emitted=2,
            skip_reason="no_actions_after_evaluation",
        ),
    )

    def _raise_state(**_kwargs):
        raise RuntimeError("strict_state_error")

    monkeypatch.setattr(evolve_flow, "_mark_self_evolved_state", _raise_state)

    session = _DummySession()
    node_repo = _DummyRepo(session)
    edge_repo = _DummyRepo(session)
    event_repo = _DummyEventRepo(session)
    gv_repo = _DummyGraphVersionRepo(session)

    result = evolve_flow.run_evolve(
        graph_id="graph_r4_strict",
        tenant_id="tenant_r4",
        session=session,
        profile="strict",
        persist_mode="strict",
        node_repo=node_repo,
        edge_repo=edge_repo,
        event_repo=event_repo,
        gv_repo=gv_repo,
    )

    assert result.status == "error"
    assert result.state_update_status == "error"
    assert "strict_state_error" in (result.error or "")
