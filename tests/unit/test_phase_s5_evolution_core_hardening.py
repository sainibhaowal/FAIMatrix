"""Phase S5 tests: evolve/invention core hardening."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.dynamics.evolution_native import EvolutionResult, evolve_once  # noqa: E402
from core.engine_native import FAIMNativeEngine  # noqa: E402
from core.operators.prune import PrunePolicy  # noqa: E402
from encoding.text_vectorizer import vectorize_blocks  # noqa: E402
from orchestration.evolve_flow import run_evolve  # noqa: E402
from perception.router import route_extraction  # noqa: E402
from store.pg.models_faim import create_all_tables  # noqa: E402
from store.pg.repos.edge_repo import EdgeRepo  # noqa: E402
from store.pg.repos.event_repo import EventRepo  # noqa: E402
from store.pg.repos.graph_version_repo import GraphVersionRepo  # noqa: E402
from store.pg.repos.node_repo import NodeRepo  # noqa: E402


def _build_repos(tenant_id: str = "tenant_s5"):
    engine = create_engine("sqlite:///:memory:")
    create_all_tables(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

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


def _write_text(engine_repo: FAIMNativeEngine, graph_id: str, text: str, raw_id: str):
    blocks = route_extraction(text.encode("utf-8"), f"{raw_id}.txt", raw_id)
    vectors = vectorize_blocks(blocks)
    engine_repo.write_atoms(graph_id=graph_id, vectors=vectors)


def test_s5_evolve_emits_skip_reason_for_insufficient_nodes():
    session, node_repo, edge_repo, event_repo, gv_repo, engine_repo = _build_repos()
    try:
        graph_id = "graph_s5_insufficient"
        _write_text(engine_repo, graph_id, "single node seed", "raw-insufficient")

        result = evolve_once(
            graph_id=graph_id,
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            graph_version_repo=gv_repo,
            self_invent_requested=False,
        )
        assert result.skip_reason == "insufficient_nodes"

        events = event_repo.get_all(session, graph_id=graph_id, limit=200)
        kinds = [event.kind for event in events]
        assert "DIAGNOSTICS_SNAPSHOT" in kinds
        assert "EVOLUTION_SKIPPED" in kinds
        skip_payload = [e.payload for e in events if e.kind == "EVOLUTION_SKIPPED"][-1]
        assert skip_payload.get("reason") == "insufficient_nodes"
    finally:
        session.close()


def test_s5_evolve_emits_skip_reason_when_no_actions():
    session, node_repo, edge_repo, event_repo, gv_repo, engine_repo = _build_repos()
    try:
        graph_id = "graph_s5_no_actions"
        _write_text(
            engine_repo,
            graph_id,
            "quantum gradient sparse manifold alpha",
            "raw-no-actions-a",
        )
        _write_text(
            engine_repo,
            graph_id,
            "bookkeeping invoice threshold ledger omega",
            "raw-no-actions-b",
        )

        result = evolve_once(
            graph_id=graph_id,
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            graph_version_repo=gv_repo,
            merge_threshold=0.999,
            prune_policy=PrunePolicy(
                min_age_days=365.0,
                max_touch_count=0,
                min_similarity_for_redundancy=1.0,
                protect_macros=True,
            ),
            self_invent_requested=False,
        )
        assert result.skip_reason == "no_actions_after_evaluation"

        events = event_repo.get_all(session, graph_id=graph_id, limit=300)
        skip_payload = [e.payload for e in events if e.kind == "EVOLUTION_SKIPPED"][-1]
        assert skip_payload.get("reason") == "no_actions_after_evaluation"
    finally:
        session.close()


def test_s5_run_evolve_passes_config_and_request_flags(monkeypatch):
    session, node_repo, edge_repo, event_repo, gv_repo, _ = _build_repos()
    captured = {}

    class _Cfg:
        self_evolve_max_actions = 7
        self_invent_enabled = True
        self_invent_on_evolve = True

    def _fake_get_config():
        return _Cfg()

    def _fake_evolve_once(**kwargs):
        captured.update(kwargs)
        return EvolutionResult(
            graph_version=11,
            merges=0,
            prunes=0,
            inventions=0,
            events_emitted=2,
            skip_reason="insufficient_nodes",
        )

    try:
        monkeypatch.setattr("runtime.config.get_config", _fake_get_config)
        monkeypatch.setattr("core.dynamics.evolution_native.evolve_once", _fake_evolve_once)

        result = run_evolve(
            graph_id="graph_s5_flow",
            tenant_id="tenant_s5",
            session=session,
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            gv_repo=gv_repo,
            self_invent_requested=False,
        )
        assert result.status == "completed"
        assert "EVOLUTION_SKIPPED" in result.events_emitted
        assert "EVOLUTION_COMPLETE" not in result.events_emitted
        assert captured["max_actions"] == 7
        assert captured["self_invent_requested"] is False
        assert captured["runtime_config"] is not None
    finally:
        session.close()


def test_s5_evolution_module_no_direct_env_gate_for_invention():
    import core.dynamics.evolution_native as evolution_native_mod

    source = inspect.getsource(evolution_native_mod)
    assert "_bool_env" not in source
    assert 'os.environ.get("FAIM_SELF_INVENT_ENABLED"' not in source
    assert 'os.environ.get("FAIM_SELF_INVENT_ON_EVOLVE"' not in source
