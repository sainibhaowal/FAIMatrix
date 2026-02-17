"""AT-S6: End-to-end self-evolve validation chain.

Validates:
write -> enqueue_self_evolve_if_due -> worker execute -> evolve events/results.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import and_, create_engine
from sqlalchemy.orm import sessionmaker

_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.engine_native import FAIMNativeEngine  # noqa: E402
from encoding.text_vectorizer import vectorize_blocks  # noqa: E402
from orchestration.jobs.worker import Worker  # noqa: E402
from orchestration.self_evolve_scheduler import enqueue_self_evolve_if_due  # noqa: E402
from perception.router import route_extraction  # noqa: E402
from runtime.config import reset_config  # noqa: E402
from store.pg.models_faim import JobModel, create_all_tables  # noqa: E402
from store.pg.repos.edge_repo import EdgeRepo  # noqa: E402
from store.pg.repos.event_repo import EventRepo  # noqa: E402
from store.pg.repos.graph_version_repo import GraphVersionRepo  # noqa: E402
from store.pg.repos.node_repo import NodeRepo  # noqa: E402


def _seed_repeated_writes(engine_repo: FAIMNativeEngine, graph_id: str) -> None:
    blocks_a = route_extraction(b"alpha memory signal", "alpha.txt", "raw-s6-a")
    blocks_b = route_extraction(b"beta memory signal", "beta.txt", "raw-s6-b")
    vectors_a = vectorize_blocks(blocks_a)
    vectors_b = vectorize_blocks(blocks_b)
    vectors = [vectors_a[0], vectors_b[0]]
    for _ in range(3):
        engine_repo.write_atoms(graph_id=graph_id, vectors=vectors)


def test_s6_end_to_end_self_evolve_chain(monkeypatch, tmp_path):
    db_path = tmp_path / "s6_e2e.db"
    database_url = f"sqlite:///{db_path}"

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_s6":["k1"]}')
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_TRIGGER_MODE", "hybrid")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MIN_INTERVAL_SECONDS", "30")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MIN_VERSION_DELTA", "1")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MAX_ACTIONS", "25")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_SCAN_INTERVAL_SECONDS", "60")
    monkeypatch.setenv("FAIM_SELF_INVENT_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_INVENT_ON_EVOLVE", "true")
    monkeypatch.setenv("FAIM_SELF_INVENT_MIN_COACTIVATION_COUNT", "2")
    monkeypatch.setenv("FAIM_SELF_INVENT_LAMBDA_THRESHOLD", "0.0")
    monkeypatch.setenv("FAIM_SELF_INVENT_MIN_REDUNDANCY_REDUCTION", "0.0")
    monkeypatch.setenv("FAIM_SELF_INVENT_MAX_MACROS_PER_CYCLE", "4")
    monkeypatch.setenv("FAIM_SELF_INVENT_EVENT_WINDOW", "5000")
    reset_config()

    engine = create_engine(database_url)
    create_all_tables(engine)
    SessionLocal = sessionmaker(bind=engine)

    tenant_id = "tenant_s6"
    graph_id = "graph_s6_e2e"

    setup_session = SessionLocal()
    try:
        node_repo = NodeRepo(setup_session, tenant_id=tenant_id)
        edge_repo = EdgeRepo(setup_session, tenant_id=tenant_id)
        event_repo = EventRepo(tenant_id=tenant_id)
        gv_repo = GraphVersionRepo(session=setup_session, tenant_id=tenant_id)
        engine_repo = FAIMNativeEngine(
            node_repo=node_repo,
            edge_repo=edge_repo,
            event_repo=event_repo,
            graph_version_repo=gv_repo,
        )

        _seed_repeated_writes(engine_repo, graph_id)
        setup_session.commit()

        enqueue = enqueue_self_evolve_if_due(
            session=setup_session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            source="memory_write",
        )
        assert enqueue.status in {"enqueued", "existing"}
        assert enqueue.job_id is not None
    finally:
        setup_session.close()

    # Force worker to use our test-local DB session factory.
    monkeypatch.setattr(
        "orchestration.jobs.worker.get_session",
        lambda: SessionLocal(),
    )

    worker = Worker(poll_interval=0.01, self_evolve_scan_interval_seconds=3600.0)
    worker._poll_and_execute()

    verify_session = SessionLocal()
    try:
        job = (
            verify_session.query(JobModel)
            .filter(
                and_(
                    JobModel.tenant_id == tenant_id,
                    JobModel.graph_id == graph_id,
                    JobModel.kind == "evolve",
                )
            )
            .order_by(JobModel.created_at.desc())
            .first()
        )
        assert job is not None
        assert job.status == "done"

        event_repo = EventRepo(tenant_id=tenant_id)
        events = event_repo.get_all(verify_session, graph_id=graph_id, limit=800)
        kinds = [event.kind for event in events]
        assert "DIAGNOSTICS_SNAPSHOT" in kinds
        assert ("EVOLUTION_COMPLETE" in kinds) or ("EVOLUTION_SKIPPED" in kinds)

        complete_events = [event for event in events if event.kind == "EVOLUTION_COMPLETE"]
        if complete_events:
            payload = complete_events[-1].payload or {}
            assert "merges" in payload
            assert "prunes" in payload
            assert "inventions" in payload
    finally:
        verify_session.close()

