"""AT-PJ: Self-inventing runtime integration.

Validates that invention logic is wired into the live evolve path (flag-gated),
and remains idempotent across repeated evolve cycles.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.dynamics.evolution_native import evolve_once  # noqa: E402
from core.engine_native import FAIMNativeEngine  # noqa: E402
from encoding.text_vectorizer import vectorize_blocks  # noqa: E402
from perception.router import route_extraction  # noqa: E402
from runtime.config import reset_config  # noqa: E402
from store.pg.models_faim import create_all_tables  # noqa: E402
from store.pg.repos.edge_repo import EdgeRepo  # noqa: E402
from store.pg.repos.event_repo import EventRepo  # noqa: E402
from store.pg.repos.graph_version_repo import GraphVersionRepo  # noqa: E402
from store.pg.repos.node_repo import NodeRepo  # noqa: E402
from store.pg.repos.self_invention_state_repo import SelfInventionStateRepo  # noqa: E402


@pytest.fixture
def repos(monkeypatch):
    """Create isolated tenant repos with self-invention enabled."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_pj":["k1"]}')
    monkeypatch.setenv("FAIM_SELF_INVENT_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_INVENT_ON_EVOLVE", "true")
    monkeypatch.setenv("FAIM_SELF_INVENT_MIN_COACTIVATION_COUNT", "2")
    monkeypatch.setenv("FAIM_SELF_INVENT_LAMBDA_THRESHOLD", "0.0")
    monkeypatch.setenv("FAIM_SELF_INVENT_MIN_REDUNDANCY_REDUCTION", "0.0")
    monkeypatch.setenv("FAIM_SELF_INVENT_MAX_MACROS_PER_CYCLE", "4")
    monkeypatch.setenv("FAIM_SELF_INVENT_EVENT_WINDOW", "5000")
    reset_config()

    engine = create_engine("sqlite:///:memory:")
    create_all_tables(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    tenant_id = "tenant_pj"

    node_repo = NodeRepo(session, tenant_id=tenant_id)
    edge_repo = EdgeRepo(session, tenant_id=tenant_id)
    event_repo = EventRepo(tenant_id=tenant_id)
    gv_repo = GraphVersionRepo(session=session, tenant_id=tenant_id)
    state_repo = SelfInventionStateRepo(session=session, tenant_id=tenant_id)
    engine_repo = FAIMNativeEngine(
        node_repo=node_repo,
        edge_repo=edge_repo,
        event_repo=event_repo,
        graph_version_repo=gv_repo,
    )

    try:
        yield {
            "session": session,
            "tenant_id": tenant_id,
            "node_repo": node_repo,
            "edge_repo": edge_repo,
            "event_repo": event_repo,
            "gv_repo": gv_repo,
            "state_repo": state_repo,
            "engine": engine_repo,
        }
    finally:
        session.close()
        reset_config()


def _seed_repeated_coactivation(engine: FAIMNativeEngine, graph_id: str) -> None:
    """Write repeated two-node packets so invention has stable coactivation sets."""
    blocks_a = route_extraction(b"alpha memory signal", "alpha.txt", "raw-a")
    blocks_b = route_extraction(b"beta memory signal", "beta.txt", "raw-b")
    vectors_a = vectorize_blocks(blocks_a)
    vectors_b = vectorize_blocks(blocks_b)
    vectors = [vectors_a[0], vectors_b[0]]

    for _ in range(3):
        engine.write_atoms(graph_id=graph_id, vectors=vectors)


def test_evolve_wires_self_invention_runtime(repos):
    graph_id = "graph_self_invent_live"
    _seed_repeated_coactivation(repos["engine"], graph_id)

    result = evolve_once(
        graph_id=graph_id,
        node_repo=repos["node_repo"],
        edge_repo=repos["edge_repo"],
        event_repo=repos["event_repo"],
        graph_version_repo=repos["gv_repo"],
    )

    assert result.inventions >= 1
    events = repos["event_repo"].get_all(repos["session"], graph_id=graph_id, limit=500)
    kinds = [e.kind for e in events]
    assert "INVENT_MACRO_NODE" in kinds

    state = repos["state_repo"].get(graph_id=graph_id, session=repos["session"])
    assert state is not None
    assert int(state.last_event_seq) > 0


def test_self_invention_is_idempotent_across_repeated_evolve(repos):
    graph_id = "graph_self_invent_idempotent"
    _seed_repeated_coactivation(repos["engine"], graph_id)

    first = evolve_once(
        graph_id=graph_id,
        node_repo=repos["node_repo"],
        edge_repo=repos["edge_repo"],
        event_repo=repos["event_repo"],
        graph_version_repo=repos["gv_repo"],
    )
    macro_count_after_first = repos["node_repo"].count_macros(graph_id)

    second = evolve_once(
        graph_id=graph_id,
        node_repo=repos["node_repo"],
        edge_repo=repos["edge_repo"],
        event_repo=repos["event_repo"],
        graph_version_repo=repos["gv_repo"],
    )
    macro_count_after_second = repos["node_repo"].count_macros(graph_id)

    assert first.inventions >= 1
    assert second.inventions == 0
    assert macro_count_after_second == macro_count_after_first
