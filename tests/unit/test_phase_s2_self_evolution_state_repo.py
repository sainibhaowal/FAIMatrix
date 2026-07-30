"""Phase S2 tests: durable self-evolution scheduler state repository."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from store.pg.models_faim import JobModel, create_all_tables
from store.pg.repos.graph_version_repo import GraphVersionRepo
from store.pg.repos.self_evolution_state_repo import SelfEvolutionStateRepo


def _new_session():
    engine = create_engine("sqlite:///:memory:")
    create_all_tables(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_get_or_create_self_evolution_state_defaults():
    session = _new_session()
    try:
        repo = SelfEvolutionStateRepo(session=session, tenant_id="tenant_s2")
        row = repo.get_or_create(graph_id="graph_s2_a")

        assert row.tenant_id == "tenant_s2"
        assert row.graph_id == "graph_s2_a"
        assert int(row.last_seen_version) == 0
        assert int(row.last_evolved_version) == 0
        assert row.last_evolved_at is None
        assert row.last_enqueued_job_id is None
    finally:
        session.close()


def test_mark_seen_version_is_monotonic():
    session = _new_session()
    try:
        repo = SelfEvolutionStateRepo(session=session, tenant_id="tenant_s2")

        row = repo.mark_seen_version("graph_s2_seen", 5)
        assert int(row.last_seen_version) == 5

        row = repo.mark_seen_version("graph_s2_seen", 3)
        assert int(row.last_seen_version) == 5
    finally:
        session.close()


def test_mark_enqueued_updates_job_and_seen_version():
    session = _new_session()
    try:
        repo = SelfEvolutionStateRepo(session=session, tenant_id="tenant_s2")
        job_id = uuid4()

        row = repo.mark_enqueued(
            graph_id="graph_s2_enqueue",
            job_id=job_id,
            seen_version=11,
        )
        assert int(row.last_seen_version) == 11
        assert str(row.last_enqueued_job_id) == str(job_id)
    finally:
        session.close()


def test_mark_evolved_updates_versions_and_timestamp():
    session = _new_session()
    try:
        repo = SelfEvolutionStateRepo(session=session, tenant_id="tenant_s2")
        evolved_at = datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc)

        row = repo.mark_evolved(
            graph_id="graph_s2_evolved",
            evolved_version=8,
            evolved_at=evolved_at,
        )
        assert int(row.last_evolved_version) == 8
        assert int(row.last_seen_version) == 8
        assert row.last_evolved_at == evolved_at

        # Monotonic evolve version: lower value should not move backwards.
        row = repo.mark_evolved(
            graph_id="graph_s2_evolved",
            evolved_version=5,
            evolved_at=evolved_at + timedelta(minutes=5),
        )
        assert int(row.last_evolved_version) == 8
        assert int(row.last_seen_version) == 8
    finally:
        session.close()


def test_select_due_graphs_applies_delta_interval_and_active_job_filters():
    session = _new_session()
    try:
        tenant_id = "tenant_s2"
        gv_repo = GraphVersionRepo(session=session, tenant_id=tenant_id)
        repo = SelfEvolutionStateRepo(session=session, tenant_id=tenant_id)
        now = datetime(2026, 2, 17, 20, 0, 0, tzinfo=timezone.utc)

        # Graph versions
        gv_repo.set_version(session, "g_never", 10, "seed")
        gv_repo.set_version(session, "g_old", 6, "seed")
        gv_repo.set_version(session, "g_recent", 9, "seed")
        gv_repo.set_version(session, "g_small_delta", 4, "seed")
        gv_repo.set_version(session, "g_active_job", 8, "seed")

        repo.mark_evolved("g_old", 3, evolved_at=now - timedelta(hours=2))
        repo.mark_evolved("g_recent", 5, evolved_at=now - timedelta(minutes=2))
        repo.mark_evolved("g_small_delta", 4, evolved_at=now - timedelta(hours=3))
        repo.mark_evolved("g_active_job", 2, evolved_at=now - timedelta(hours=4))

        session.add(
            JobModel(
                job_id=uuid4(),
                tenant_id=tenant_id,
                graph_id="g_active_job",
                kind="evolve",
                payload_json={"source": "test"},
                status="pending",
            )
        )
        session.flush()

        due = repo.select_due_graphs(
            min_version_delta=2,
            min_interval_seconds=300,
            limit=10,
            now=now,
        )

        due_ids = [item.graph_id for item in due]
        assert due_ids == ["g_never", "g_old"]
        assert due[0].version_delta == 10
        assert due[1].version_delta == 3
    finally:
        session.close()


def test_select_due_graphs_is_tenant_isolated():
    session = _new_session()
    try:
        repo_tenant_a = SelfEvolutionStateRepo(session=session, tenant_id="tenant_s2_a")
        gv_repo_a = GraphVersionRepo(session=session, tenant_id="tenant_s2_a")
        gv_repo_b = GraphVersionRepo(session=session, tenant_id="tenant_s2_b")

        gv_repo_a.set_version(session, "graph_a", 5, "seed")
        gv_repo_b.set_version(session, "graph_b", 7, "seed")

        due_a = repo_tenant_a.select_due_graphs(
            min_version_delta=1,
            min_interval_seconds=30,
            limit=10,
            now=datetime(2026, 2, 17, 20, 0, 0, tzinfo=timezone.utc),
        )
        due_a_ids = [item.graph_id for item in due_a]

        assert due_a_ids == ["graph_a"]
    finally:
        session.close()
