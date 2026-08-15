"""Phase 0032 tests: evolution learning (policy, repo, wiring, winner selection).

Covers:
- EvolutionPolicy UCB1 bandits + lambda calibration (pure logic)
- compute_reward determinism and bounds
- EvolutionLearningRepo persistence round-trips (fail-open writes)
- run_evolve wiring with FAIM_EVOLUTION_LEARNING_ENABLED (opt-in)
- Semantic winner selection with legacy-hash tie-break
"""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.dynamics.winner_selection import (  # noqa: E402
    select_winner_semantic,
    semantic_node_score,
)
from core.engine_native import FAIMNativeEngine  # noqa: E402
from core.learning.evolution_policy import (  # noqa: E402
    KNOB_GRIDS,
    MIN_LAMBDA_SAMPLES,
    EvolutionPolicy,
    compute_reward,
)
from encoding.text_vectorizer import vectorize_blocks  # noqa: E402
from orchestration.evolve_flow import run_evolve  # noqa: E402
from perception.router import route_extraction  # noqa: E402
from store.pg.models_faim import create_all_tables  # noqa: E402
from store.pg.repos.edge_repo import EdgeRepo  # noqa: E402
from store.pg.repos.event_repo import EventRepo  # noqa: E402
from store.pg.repos.evolution_learning_repo import (  # noqa: E402
    EvolutionLearningRepo,
    EvolutionOutcome,
    MetaMetricSnapshot,
)
from store.pg.repos.graph_version_repo import GraphVersionRepo  # noqa: E402
from store.pg.repos.node_repo import NodeRepo  # noqa: E402

# =============================================================================
# Policy: defaults and hard bounds
# =============================================================================


def test_policy_resolves_defaults_before_learning():
    policy = EvolutionPolicy(graph_id="g1", seed=1)
    knobs = policy.resolve_knobs()
    assert knobs.merge_threshold == 0.95
    assert knobs.prune_similarity_threshold == 0.98
    assert knobs.prune_min_age_days == 7.0
    assert knobs.lambda_threshold == 0.30
    assert knobs.learned is False
    assert knobs.source == "defaults"


def test_policy_selected_values_always_within_grids():
    rng = random.Random(42)
    policy = EvolutionPolicy(graph_id="g2", seed=42)
    for _ in range(200):
        policy.rng = random.Random(rng.randrange(2**32))
        knobs = policy.resolve_knobs()
        for knob, grid in KNOB_GRIDS.items():
            value = getattr(knobs, knob)
            assert min(grid) <= value <= max(grid), f"{knob}={value}"
            assert value in grid, f"{knob}={value} not in grid {grid}"


def test_policy_ucb1_favors_high_reward_arm():
    policy = EvolutionPolicy(graph_id="g3", seed=7, exploration=0.0)
    # Explore all merge_threshold values once (UCB explores untried arms).
    for _ in range(8):
        knobs = policy.resolve_knobs()
        policy.update_from_outcome(
            knobs,
            merges=1,
            prunes=1,
            r_before=0.5,
            r_after=0.1,
            n_before=0.1,
            n_after=0.2,
            e_before=0.5,
            e_after=0.3,
            lambda_after=0.31,
        )
    arm = policy.arms["merge_threshold"]
    assert arm.total_visits() >= 8

    # Feed many good outcomes at 0.90 and bad at 0.95.
    for value, reward_direction in ((0.90, 1.0), (0.95, -1.0)):
        for _ in range(10):
            knobs = policy.resolve_knobs()
            forced = SimpleNamespace(
                merge_threshold=value,
                prune_similarity_threshold=knobs.prune_similarity_threshold,
                prune_min_age_days=knobs.prune_min_age_days,
                lambda_threshold=knobs.lambda_threshold,
            )
            policy.update_from_outcome(
                forced,  # type: ignore[arg-type]
                merges=1,
                prunes=1,
                r_before=0.5,
                r_after=0.1 if reward_direction > 0 else 0.49,
                n_before=0.1,
                n_after=0.2,
                e_before=0.5,
                e_after=0.3,
                lambda_after=0.30,
            )
    assert arm.mean_reward(0.90) > arm.mean_reward(0.95)
    best = max(KNOB_GRIDS["merge_threshold"], key=lambda v: arm.mean_reward(v))
    assert best == 0.90


def test_policy_linucb_is_contextual():
    """The same arm must prefer different values under different contexts."""
    policy = EvolutionPolicy(graph_id="g8", seed=11, exploration=0.0, ucb_c=0.05)

    def _run(context: dict, value: float, reward_sign: float):
        knobs = policy.resolve_knobs(context=context)
        policy.update_from_outcome(
            SimpleNamespace(
                merge_threshold=value,
                prune_similarity_threshold=knobs.prune_similarity_threshold,
                prune_min_age_days=knobs.prune_min_age_days,
                lambda_threshold=knobs.lambda_threshold,
            ),  # type: ignore[arg-type]
            merges=1,
            prunes=0,
            r_before=0.5,
            r_after=0.1 if reward_sign > 0 else 0.49,
            n_before=0.1,
            n_after=0.2,
            e_before=0.5,
            e_after=0.4,
            lambda_after=0.30,
            context=context,
        )

    hi_ctx = {"R": 0.8, "N": 0.1, "D": 1.8, "H": 0.6, "node_count": 50}
    lo_ctx = {"R": 0.1, "N": 0.8, "D": 1.2, "H": 0.9, "node_count": 900}
    # Warm up: record every grid value once so no arm is "untried" (+inf).
    for value in KNOB_GRIDS["merge_threshold"]:
        _run(hi_ctx, value, +0.5)
        _run(lo_ctx, value, +0.5)
    # High-R context: aggressive merging (0.90) pays. Low-R context: it hurts.
    for _ in range(12):
        _run(hi_ctx, 0.90, +1.0)
        _run(lo_ctx, 0.90, -1.0)
    arm = policy.arms["merge_threshold"]
    best_hi = max(
        KNOB_GRIDS["merge_threshold"],
        key=lambda v: arm.ucb(v, [1.0, 0.8, 0.1, 1.8, 0.6, 0.05]),
    )
    best_lo = max(
        KNOB_GRIDS["merge_threshold"],
        key=lambda v: arm.ucb(v, [1.0, 0.1, 0.8, 1.2, 0.9, 0.9]),
    )
    assert best_hi == 0.90  # aggressive where redundancy is high
    assert best_lo != 0.90  # conservative where redundancy is low
    assert best_hi != best_lo


def test_policy_v1_state_keeps_lambda_calibration():
    v1_state = {
        "schema": "v1",
        "arms": {"merge_threshold": {"visits": {"0.95": 9}}},
        "lambda_calibration": {"n": 4, "mean": 0.31, "m2": 0.002},
    }
    policy = EvolutionPolicy.from_state(v1_state, graph_id="g9", seed=1)
    # Lambda calibration survives the migration.
    assert policy.lambda_calibration.n == 4
    # Arms reset (v1 rewards have no contexts to seed LinUCB).
    assert policy.arms["merge_threshold"].total_visits() == 0


def test_policy_does_not_learn_from_noop_cycles():
    policy = EvolutionPolicy(graph_id="g4", seed=3)
    knobs = policy.resolve_knobs()
    policy.update_from_outcome(
        knobs,
        merges=0,
        prunes=0,
        r_before=0.4,
        r_after=0.4,
        n_before=0.1,
        n_after=0.1,
        e_before=0.5,
        e_after=0.5,
        lambda_after=0.30,
    )
    assert policy.arms["merge_threshold"].total_visits() == 0
    assert policy.arms["lambda_threshold"].total_visits() == 1
    assert policy.lambda_calibration.n == 1


def test_policy_state_round_trip_and_fail_closed():
    policy = EvolutionPolicy(graph_id="g5", seed=9)
    for _ in range(6):
        knobs = policy.resolve_knobs()
        policy.update_from_outcome(
            knobs,
            merges=1,
            prunes=0,
            r_before=0.5,
            r_after=0.2,
            n_before=0.1,
            n_after=0.3,
            e_before=0.5,
            e_after=0.4,
            lambda_after=0.32,
        )
    state = policy.to_state()
    restored = EvolutionPolicy.from_state(state, graph_id="g5", seed=9)
    assert restored.version == policy.version
    assert restored.arms["merge_threshold"].visits == (
        policy.arms["merge_threshold"].visits
    )
    assert restored.lambda_calibration.n == policy.lambda_calibration.n

    # Corrupt state must fail closed to defaults, not crash.
    broken = EvolutionPolicy.from_state({"schema": "garbage", "arms": "nope"},
                                        graph_id="g5")
    assert broken.resolve_knobs().merge_threshold == 0.95
    assert EvolutionPolicy.from_state(None, graph_id="g5").version == 0
    assert EvolutionPolicy.from_state([1, 2], graph_id="g5").version == 0


def test_lambda_calibration_requires_min_samples():
    policy = EvolutionPolicy(graph_id="g6", seed=1)
    for _ in range(MIN_LAMBDA_SAMPLES - 1):
        policy.lambda_calibration.record(0.30)
    assert policy.lambda_calibration.threshold() is None
    policy.lambda_calibration.record(0.30)
    threshold = policy.lambda_calibration.threshold()
    assert threshold is not None
    assert 0.0 <= threshold <= 1.0
    # High-variance lambda history must raise the calibrated threshold.
    noisy = EvolutionPolicy(graph_id="g7", seed=1)
    for v in [0.2, 0.5, 0.2, 0.5, 0.2, 0.5, 0.2, 0.5, 0.2, 0.5]:
        noisy.lambda_calibration.record(v)
    assert noisy.lambda_calibration.threshold() > 0.3


# =============================================================================
# Reward
# =============================================================================


def test_compute_reward_rewards_redundancy_reduction():
    good = compute_reward(
        merges=3,
        prunes=2,
        r_before=0.60,
        r_after=0.10,
        n_before=0.1,
        n_after=0.2,
        e_before=0.55,
        e_after=0.35,
    )
    bad = compute_reward(
        merges=3,
        prunes=2,
        r_before=0.60,
        r_after=0.58,
        n_before=0.1,
        n_after=0.05,
        e_before=0.55,
        e_after=0.50,
    )
    assert good > bad
    assert -1.0 <= good <= 1.0
    assert -1.0 <= bad <= 1.0


def test_compute_reward_noop_penalty():
    noop = compute_reward(
        merges=5,
        prunes=5,
        r_before=0.5,
        r_after=0.5,
        n_before=0.1,
        n_after=0.1,
        e_before=0.5,
        e_after=0.5,
    )
    idle = compute_reward(
        merges=0,
        prunes=0,
        r_before=0.5,
        r_after=0.5,
        n_before=0.1,
        n_after=0.1,
        e_before=0.5,
        e_after=0.5,
    )
    assert noop < idle
    assert noop < 0.1  # actions without improvement get the mild penalty


def test_compute_reward_retrieval_delta_blend():
    base = compute_reward(
        merges=1,
        prunes=0,
        r_before=0.5,
        r_after=0.4,
        n_before=0.1,
        n_after=0.2,
        e_before=0.5,
        e_after=0.4,
        retrieval_delta=1.0,
    )
    neg = compute_reward(
        merges=1,
        prunes=0,
        r_before=0.5,
        r_after=0.4,
        n_before=0.1,
        n_after=0.2,
        e_before=0.5,
        e_after=0.4,
        retrieval_delta=-1.0,
    )
    assert base > neg


# =============================================================================
# Winner selection (semantic)
# =============================================================================


def _fake_node(
    *,
    node_id=None,
    residual=0.01,
    touch_count=0,
    last_access=None,
    anchor_json=None,
    kind="atom",
    long_term=False,
    level=0,
    vector_hash="",
):
    return SimpleNamespace(
        node_id=str(node_id or uuid4()),
        residual=residual,
        touch_count=touch_count,
        last_access=last_access or datetime.now(timezone.utc),
        anchor_json=anchor_json or {},
        kind=kind,
        long_term=long_term,
        level=level,
        vector_hash=vector_hash,
    )


def test_winner_selection_prefers_richer_node():
    now = datetime.now(timezone.utc)
    rich = _fake_node(
        residual=0.9,
        touch_count=40,
        last_access=now,
        anchor_json={"text": "full semantic content", "title": "T"},
        vector_hash="aaa",
    )
    poor = _fake_node(
        residual=0.01,
        touch_count=0,
        last_access=now - timedelta(days=60),
        anchor_json={},
        vector_hash="bbb",
    )
    decision = select_winner_semantic(rich, poor, now=now)
    assert decision.winner_id == UUID(str(rich.node_id))
    assert decision.loser_id == UUID(str(poor.node_id))
    assert decision.winner_score > decision.loser_score
    assert decision.meta["tie_break"] == "score"


def test_winner_selection_protects_macros():
    now = datetime.now(timezone.utc)
    macro = _fake_node(
        kind="macro",
        long_term=True,
        residual=0.1,
        touch_count=2,
        last_access=now - timedelta(days=5),
        anchor_json={},
        vector_hash="mmm",
    )
    atom = _fake_node(
        kind="atom",
        residual=0.15,
        touch_count=5,
        last_access=now,
        anchor_json={"text": "t"},
        vector_hash="aaa",
    )
    decision = select_winner_semantic(macro, atom, now=now)
    assert decision.winner_id == UUID(str(macro.node_id))
    assert decision.meta["tie_break"] == "score"


def test_winner_selection_tie_breaks_by_legacy_hash():
    now = datetime.now(timezone.utc)
    shared = dict(
        residual=0.1,
        touch_count=2,
        last_access=now - timedelta(days=5),
        anchor_json={"text": "same"},
        kind="atom",
        long_term=False,
        level=1,
    )
    a = _fake_node(**shared, vector_hash="bbbb")
    b = _fake_node(**shared, vector_hash="aaaa")
    d1 = select_winner_semantic(a, b, now=now)
    d2 = select_winner_semantic(a, b, now=now)
    assert d1.winner_id == d2.winner_id  # deterministic
    assert d1.meta["tie_break"] == "legacy_hash"
    assert d1.winner_score == d1.loser_score
    assert str(d1.winner_id) != str(d1.loser_id)
    # b's smaller hash wins under the legacy rule.
    assert d1.winner_id == UUID(str(b.node_id))


def test_semantic_score_is_bounded():
    node = _fake_node(residual=5.0, touch_count=10**9, anchor_json={"x": "y" * 500})
    score = semantic_node_score(node)
    assert 0.0 <= score <= 1.0


# =============================================================================
# Repo persistence (sqlite)
# =============================================================================


def _build_repos(tenant_id: str = "tenant_0032"):
    engine = create_engine("sqlite:///:memory:")
    create_all_tables(engine)
    session = sessionmaker(bind=engine)()
    node_repo = NodeRepo(session, tenant_id=tenant_id)
    edge_repo = EdgeRepo(session, tenant_id=tenant_id)
    event_repo = EventRepo(tenant_id=tenant_id)
    gv_repo = GraphVersionRepo(session=session, tenant_id=tenant_id)
    engine_repo = FAIMNativeEngine(
        node_repo=node_repo,
        edge_repo=edge_repo,
        event_repo=event_repo,
        graph_version_repo=gv_repo,
    )
    return session, node_repo, edge_repo, event_repo, gv_repo, engine_repo


def test_learning_repo_outcome_round_trip():
    session, *_ = _build_repos()
    try:
        repo = EvolutionLearningRepo(session=session, tenant_id="tenant_0032")
        outcome = EvolutionOutcome(
            graph_version=3,
            merges=2,
            prunes=1,
            inventions=0,
            theories=0,
            lambda_before=0.30,
            lambda_after=0.27,
            r_before=0.6,
            r_after=0.2,
            n_before=0.1,
            n_after=0.25,
            d_before=1.4,
            d_after=1.6,
            h_before=0.8,
            h_after=0.7,
            e_before=0.55,
            e_after=0.4,
            reward=0.42,
            policy_snapshot={"merge_threshold": 0.96},
        )
        row_id = repo.record_outcome("graph_lr", outcome, session=session)
        session.commit()
        assert row_id != UUID(int=0)
        rows = repo.get_outcomes("graph_lr", limit=10, session=session)
        assert len(rows) == 1
        assert rows[0]["merges"] == 2
        assert rows[0]["reward"] == 0.42
        assert rows[0]["policy_snapshot"]["merge_threshold"] == 0.96
        assert rows[0]["lambda_after"] == 0.27
    finally:
        session.close()


def test_learning_repo_policy_state_round_trip():
    session, *_ = _build_repos()
    try:
        repo = EvolutionLearningRepo(session=session, tenant_id="tenant_0032")
        assert repo.load_policy_state("graph_ps", session=session) == {
            "schema": "v2",
            "arms": {},
            "lambda_calibration": {},
            "meta": {},
            "version": 0,
        }
        arms = {"merge_threshold": {"visits": {"0.95": 3}, "rewards": {"0.95": 0.6}}}
        calib = {"n": 4, "mean": 0.31, "m2": 0.002}
        ok = repo.save_policy_state(
            "graph_ps",
            arms=arms,
            lambda_calibration=calib,
            meta={"schema": "v1"},
            policy_version=4,
            session=session,
        )
        session.commit()
        assert ok is True
        state = repo.load_policy_state("graph_ps", session=session)
        assert state["version"] == 4
        assert state["arms"]["merge_threshold"]["visits"] == {"0.95": 3}
        assert state["lambda_calibration"]["n"] == 4
    finally:
        session.close()


def test_learning_repo_meta_metrics_round_trip():
    session, *_ = _build_repos()
    try:
        repo = EvolutionLearningRepo(session=session, tenant_id="tenant_0032")
        snap = MetaMetricSnapshot(
            merge_usefulness=0.8,
            invention_utilization=0.3,
            prune_regret=0.05,
            d_drift=0.02,
            h_drift=0.01,
            alerts={"note": "ok"},
            detail={"reward": 0.42},
        )
        row_id = repo.record_meta_metrics("graph_mm", snap, session=session)
        session.commit()
        assert row_id != UUID(int=0)
        rows = repo.get_latest_meta_metrics("graph_mm", session=session)
        assert len(rows) == 1
        assert rows[0]["merge_usefulness"] == 0.8
        assert rows[0]["detail"]["reward"] == 0.42
    finally:
        session.close()


def test_learning_repo_fail_open_when_no_session():
    repo = EvolutionLearningRepo(session=None, tenant_id="tenant_0032")
    assert repo.record_outcome("g", EvolutionOutcome()) == UUID(int=0)
    assert repo.load_policy_state("g") == {
        "schema": "v2",
        "arms": {},
        "lambda_calibration": {},
        "meta": {},
        "version": 0,
    }
    assert repo.save_policy_state("g", arms={}, lambda_calibration={},
                                  meta={}, policy_version=0) is False


# =============================================================================
# run_evolve wiring (opt-in via env flag)
# =============================================================================


def _write_text(engine_repo: FAIMNativeEngine, graph_id: str, text: str, raw_id: str):
    blocks = route_extraction(text.encode("utf-8"), f"{raw_id}.txt", raw_id)
    vectors = vectorize_blocks(blocks)
    engine_repo.write_atoms(graph_id=graph_id, vectors=vectors)


def test_run_evolve_learning_disabled_by_default(monkeypatch):
    session, node_repo, edge_repo, event_repo, gv_repo, engine_repo = _build_repos()
    try:
        graph_id = "graph_ld"
        _write_text(
            engine_repo,
            graph_id,
            "quantum gradient sparse manifold alpha momentum field",
            "raw-ld-a",
        )
        result = run_evolve(
            graph_id=graph_id,
            tenant_id="tenant_0032",
            session=session,
            profile="strict",
            persist_mode="relaxed",
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            gv_repo=gv_repo,
        )
        assert result.status == "completed"
        assert result.learning is None
        repo = EvolutionLearningRepo(session=session, tenant_id="tenant_0032")
        assert repo.get_outcomes(graph_id) == []
    finally:
        session.close()


def test_run_evolve_learning_enabled_records_outcome(monkeypatch):
    monkeypatch.setenv("FAIM_EVOLUTION_LEARNING_ENABLED", "true")
    session, node_repo, edge_repo, event_repo, gv_repo, engine_repo = _build_repos()
    try:
        graph_id = "graph_le"
        _write_text(
            engine_repo,
            graph_id,
            "quantum gradient sparse manifold alpha momentum field lattice",
            "raw-le-a",
        )
        _write_text(
            engine_repo,
            graph_id,
            "bookkeeping invoice threshold ledger omega cashflow audit",
            "raw-le-b",
        )
        result = run_evolve(
            graph_id=graph_id,
            tenant_id="tenant_0032",
            session=session,
            profile="strict",
            persist_mode="relaxed",
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            gv_repo=gv_repo,
        )
        assert result.status == "completed"
        assert result.learning is not None
        assert result.learning["enabled"] is True
        assert -1.0 <= result.learning["reward"] <= 1.0
        assert result.learning["knobs"]["merge_threshold"] == 0.95
        assert result.learning["policy_version"] >= 1

        repo = EvolutionLearningRepo(session=session, tenant_id="tenant_0032")
        rows = repo.get_outcomes(graph_id)
        assert len(rows) == 1
        assert rows[0]["policy_snapshot"]["merge_threshold"] == 0.95
        state = repo.load_policy_state(graph_id)
        assert state["version"] >= 1
        assert state["lambda_calibration"]["n"] >= 1
        assert "lambda_threshold" in state["arms"]
        # Meta-metrics are computed and persisted each cycle.
        meta_rows = repo.get_latest_meta_metrics(graph_id)
        assert len(meta_rows) == 1
        assert 0.0 <= meta_rows[0]["merge_usefulness"] <= 1.0
        assert 0.0 <= meta_rows[0]["invention_utilization"] <= 1.0
        assert 0.0 <= meta_rows[0]["prune_regret"] <= 1.0
        assert result.learning["meta_metrics"]["merge_usefulness"] == (
            meta_rows[0]["merge_usefulness"]
        )
    finally:
        session.close()


def test_run_evolve_semantic_selector_active_on_merge(monkeypatch):
    monkeypatch.setenv("FAIM_EVOLUTION_LEARNING_ENABLED", "true")
    session, node_repo, edge_repo, event_repo, gv_repo, engine_repo = _build_repos()
    try:
        graph_id = "graph_sel"
        text = "quantum gradient sparse manifold alpha momentum field lattice"
        _write_text(engine_repo, graph_id, text, "raw-sel-1")
        _write_text(engine_repo, graph_id, text, "raw-sel-2")
        result = run_evolve(
            graph_id=graph_id,
            tenant_id="tenant_0032",
            session=session,
            profile="strict",
            persist_mode="relaxed",
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            gv_repo=gv_repo,
        )
        assert result.status == "completed"
        events = event_repo.get_all(session, graph_id=graph_id, limit=300)
        merge_events = [e for e in events if e.kind == "EVOLUTION_MERGE"]
        prune_events = [e for e in events if e.kind == "PRUNE_NODE"]
        assert len(merge_events) >= 1, "duplicate texts must merge"
        for event in merge_events:
            assert event.payload.get("selector") == "semantic"
            assert event.payload["winner_id"] != event.payload["loser_id"]
        # Pruning is disabled for fresh nodes (age gate), so no prune events.
        assert len(prune_events) == 0
        # The merge edge carries the semantic selector metadata.
        edges = edge_repo.list_all_edges(graph_id)
        assert any(
            (getattr(e, "meta", None) or {}).get("selector") == "semantic"
            for e in edges
        )
    finally:
        session.close()


def test_run_evolve_learning_second_cycle_updates_state(monkeypatch):
    monkeypatch.setenv("FAIM_EVOLUTION_LEARNING_ENABLED", "true")
    session, node_repo, edge_repo, event_repo, gv_repo, engine_repo = _build_repos()
    try:
        graph_id = "graph_le2"
        for idx in range(2):
            _write_text(
                engine_repo,
                graph_id,
                f"quantum gradient sparse manifold alpha momentum field {idx}",
                f"raw-le2-{idx}",
            )
            result = run_evolve(
                graph_id=graph_id,
                tenant_id="tenant_0032",
                session=session,
                profile="strict",
                persist_mode="relaxed",
                node_repo=node_repo,
                edge_repo=edge_repo,
                event_repo=event_repo,
                gv_repo=gv_repo,
            )
            assert result.status == "completed"

        repo = EvolutionLearningRepo(session=session, tenant_id="tenant_0032")
        assert len(repo.get_outcomes(graph_id)) == 2
        state = repo.load_policy_state(graph_id)
        assert state["version"] >= 2
    finally:
        session.close()
