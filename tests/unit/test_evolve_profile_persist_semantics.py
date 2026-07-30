"""Phase R7 unit checks: evolve strict/fast/relaxed branch semantics."""

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
        self.tenant_id = "tenant_r7"


class _DummyEventRepo(_DummyRepo):
    def __init__(self, session):
        super().__init__(session)
        self.events: list[tuple[str, dict]] = []

    def emit(self, session, graph_id, kind, payload):  # noqa: ARG002
        self.events.append((kind, {"graph_id": graph_id, **dict(payload or {})}))


class _DummyGraphVersionRepo(_DummyRepo):
    def get(self, _session, _graph_id):
        return None


def _stub_runtime(monkeypatch, max_actions: int = 10):
    class _Cfg:
        self_evolve_max_actions = max_actions
        self_invent_lambda_threshold = 0.3
        self_invent_min_redundancy_reduction = 0.01
        self_invent_max_macros_per_cycle = 5

    monkeypatch.setattr("runtime.config.get_config", lambda: _Cfg())
    monkeypatch.setenv("FAIM_PROFILE_PERSIST_COMPAT_MODE", "false")


@pytest.mark.parametrize(
    "profile,expected_actions,expected_merge,expected_age,expected_touch,expected_similarity,expected_self_invent",
    [
        ("strict", 6, 0.97, 14.0, 1, 0.99, False),
        ("fast", 8, 0.95, 7.0, 1, 0.98, True),
        ("relaxed", 10, 0.92, 3.0, 2, 0.95, True),
    ],
)
def test_r7_evolve_profile_branches_apply_expected_knobs(
    monkeypatch,
    profile,
    expected_actions,
    expected_merge,
    expected_age,
    expected_touch,
    expected_similarity,
    expected_self_invent,
):
    from core.dynamics.evolution_native import EvolutionResult
    from orchestration import evolve_flow

    _stub_runtime(monkeypatch, max_actions=10)

    captured = {}

    def _fake_evolve_once(**kwargs):
        captured.update(kwargs)
        return EvolutionResult(
            graph_version=4,
            merges=0,
            prunes=0,
            inventions=0,
            events_emitted=2,
            skip_reason="insufficient_nodes",
        )

    monkeypatch.setattr("core.dynamics.evolution_native.evolve_once", _fake_evolve_once)
    monkeypatch.setattr(evolve_flow, "_mark_self_evolved_state", lambda **_kwargs: None)

    session = _DummySession()
    node_repo = _DummyRepo(session)
    edge_repo = _DummyRepo(session)
    event_repo = _DummyEventRepo(session)
    gv_repo = _DummyGraphVersionRepo(session)

    result = evolve_flow.run_evolve(
        graph_id=f"graph_r7_{profile}",
        tenant_id="tenant_r7",
        session=session,
        profile=profile,
        persist_mode="relaxed",
        node_repo=node_repo,
        edge_repo=edge_repo,
        event_repo=event_repo,
        gv_repo=gv_repo,
    )

    assert result.status == "completed"
    assert result.requested_profile == profile
    assert result.effective_profile == profile
    assert result.requested_persist_mode == "relaxed"
    assert result.effective_persist_mode == "relaxed"
    assert result.durability_path == "core_sync_secondary_async"
    assert result.completion_mode == "core_sync_state_best_effort"
    assert result.evolve_aggressiveness in {"conservative", "performance", "adaptive"}

    assert captured["max_actions"] == expected_actions
    assert captured["merge_threshold"] == pytest.approx(expected_merge)
    assert captured["prune_policy"].min_age_days == pytest.approx(expected_age)
    assert captured["prune_policy"].max_touch_count == expected_touch
    assert captured["prune_policy"].min_similarity_for_redundancy == pytest.approx(
        expected_similarity
    )
    assert captured["self_invent_requested"] is expected_self_invent
    assert "event_context" in captured
    assert captured["event_context"]["requested_profile"] == profile
    assert captured["event_context"]["requested_persist_mode"] == "relaxed"
    assert captured["event_context"]["effective_profile"] == profile
    assert captured["event_context"]["effective_persist_mode"] == "relaxed"


@pytest.mark.parametrize(
    "profile,persist_mode,expected_durability",
    [
        ("strict", "strict", "sync_strict"),
        ("strict", "relaxed", "core_sync_secondary_async"),
        ("fast", "strict", "sync_strict"),
        ("fast", "relaxed", "core_sync_secondary_async"),
        ("relaxed", "strict", "sync_strict"),
        ("relaxed", "relaxed", "core_sync_secondary_async"),
    ],
)
def test_r7_evolve_requested_vs_effective_mode_fields_and_start_event_payload(
    monkeypatch,
    profile,
    persist_mode,
    expected_durability,
):
    from core.dynamics.evolution_native import EvolutionResult
    from orchestration import evolve_flow

    _stub_runtime(monkeypatch, max_actions=10)
    monkeypatch.setattr(
        "core.dynamics.evolution_native.evolve_once",
        lambda **_kwargs: EvolutionResult(
            graph_version=3,
            merges=1,
            prunes=0,
            inventions=0,
            events_emitted=2,
            skip_reason=None,
        ),
    )
    monkeypatch.setattr(evolve_flow, "_mark_self_evolved_state", lambda **_kwargs: None)

    session = _DummySession()
    node_repo = _DummyRepo(session)
    edge_repo = _DummyRepo(session)
    event_repo = _DummyEventRepo(session)
    gv_repo = _DummyGraphVersionRepo(session)

    result = evolve_flow.run_evolve(
        graph_id=f"graph_r7_fields_{profile}_{persist_mode}",
        tenant_id="tenant_r7",
        session=session,
        profile=profile,
        persist_mode=persist_mode,
        node_repo=node_repo,
        edge_repo=edge_repo,
        event_repo=event_repo,
        gv_repo=gv_repo,
    )

    assert result.status == "completed"
    assert result.requested_profile == profile
    assert result.effective_profile == profile
    assert result.requested_persist_mode == persist_mode
    assert result.effective_persist_mode == persist_mode
    assert result.durability_path == expected_durability

    start = next(
        (payload for kind, payload in event_repo.events if kind == "EVOLUTION_START"),
        None,
    )
    assert start is not None
    assert start["requested_profile"] == profile
    assert start["requested_persist_mode"] == persist_mode
    assert start["effective_profile"] == profile
    assert start["effective_persist_mode"] == persist_mode
    assert start["durability_path"] == expected_durability


def test_r7_evolve_strict_persist_fails_when_state_update_fails(monkeypatch):
    from core.dynamics.evolution_native import EvolutionResult
    from orchestration import evolve_flow

    _stub_runtime(monkeypatch, max_actions=10)
    monkeypatch.setattr(
        "core.dynamics.evolution_native.evolve_once",
        lambda **_kwargs: EvolutionResult(
            graph_version=6,
            merges=0,
            prunes=0,
            inventions=0,
            events_emitted=2,
            skip_reason="no_actions_after_evaluation",
        ),
    )
    monkeypatch.setattr(
        evolve_flow,
        "_mark_self_evolved_state",
        lambda **_kwargs: (_ for _ in ()).throw(
            RuntimeError("state_update_failure_r7")
        ),
    )

    session = _DummySession()
    node_repo = _DummyRepo(session)
    edge_repo = _DummyRepo(session)
    event_repo = _DummyEventRepo(session)
    gv_repo = _DummyGraphVersionRepo(session)

    result = evolve_flow.run_evolve(
        graph_id="graph_r7_strict_error",
        tenant_id="tenant_r7",
        session=session,
        profile="strict",
        persist_mode="strict",
        node_repo=node_repo,
        edge_repo=edge_repo,
        event_repo=event_repo,
        gv_repo=gv_repo,
    )

    assert result.status == "error"
    assert result.requested_profile == "strict"
    assert result.effective_profile == "strict"
    assert result.requested_persist_mode == "strict"
    assert result.effective_persist_mode == "strict"
    assert result.durability_path == "sync_strict"
    assert result.completion_mode == "sync_strict"
    assert result.state_update_status == "error"
    assert "state_update_failure_r7" in (result.error or "")
