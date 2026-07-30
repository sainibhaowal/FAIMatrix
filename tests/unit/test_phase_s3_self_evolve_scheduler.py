"""Phase S3 tests: centralized self-evolve enqueue helper."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orchestration.self_evolve_scheduler import (
    enqueue_self_evolve_if_due,
    evaluate_self_evolve_due,
)
from sqlalchemy import and_, create_engine
from sqlalchemy.orm import sessionmaker
from store.pg.models_faim import JobModel, SelfEvolutionStateModel, create_all_tables
from store.pg.repos.graph_version_repo import GraphVersionRepo
from store.pg.repos.self_evolution_state_repo import SelfEvolutionStateRepo


def _new_session():
    engine = create_engine("sqlite:///:memory:")
    create_all_tables(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _seed_graph_version(
    session, *, tenant_id: str, graph_id: str, version: int
) -> None:
    gv_repo = GraphVersionRepo(session=session, tenant_id=tenant_id)
    gv_repo.set_version(session, graph_id, version, "seed")
    session.commit()


def _count_evolve_jobs(session, *, tenant_id: str, graph_id: str) -> int:
    return int(
        session.query(JobModel)
        .filter(
            and_(
                JobModel.tenant_id == tenant_id,
                JobModel.graph_id == graph_id,
                JobModel.kind == "evolve",
            )
        )
        .count()
    )


def _set_defaults(monkeypatch):
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_TRIGGER_MODE", "post_upload")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MIN_INTERVAL_SECONDS", "300")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MIN_VERSION_DELTA", "1")
    monkeypatch.setenv("FAIM_SELF_INVENT_ENABLED", "false")
    monkeypatch.setenv("FAIM_SELF_INVENT_AFTER_UPLOAD", "false")
    monkeypatch.setenv("FAIM_SELF_INVENT_ON_EVOLVE", "true")


def test_s3_skips_when_self_evolve_disabled(monkeypatch):
    _set_defaults(monkeypatch)
    monkeypatch.setenv("FAIM_SELF_EVOLVE_ENABLED", "false")

    session = _new_session()
    try:
        _seed_graph_version(
            session,
            tenant_id="tenant_s3",
            graph_id="graph_s3_disabled",
            version=3,
        )
        result = enqueue_self_evolve_if_due(
            session=session,
            tenant_id="tenant_s3",
            graph_id="graph_s3_disabled",
            source="memory_write",
        )
        assert result.status == "skipped"
        assert result.reason == "self_evolve_disabled"
        assert result.job_id is None
        assert (
            _count_evolve_jobs(
                session,
                tenant_id="tenant_s3",
                graph_id="graph_s3_disabled",
            )
            == 0
        )
    finally:
        session.close()


def test_s3_keeps_storage_legacy_followup_compat(monkeypatch):
    _set_defaults(monkeypatch)
    monkeypatch.setenv("FAIM_SELF_EVOLVE_ENABLED", "false")
    monkeypatch.setenv("FAIM_SELF_INVENT_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_INVENT_AFTER_UPLOAD", "true")

    session = _new_session()
    try:
        _seed_graph_version(
            session,
            tenant_id="tenant_s3",
            graph_id="graph_s3_storage_compat",
            version=2,
        )
        result = enqueue_self_evolve_if_due(
            session=session,
            tenant_id="tenant_s3",
            graph_id="graph_s3_storage_compat",
            source="storage_upload",
        )
        assert result.status == "enqueued"
        assert result.job_id is not None
        assert (
            _count_evolve_jobs(
                session,
                tenant_id="tenant_s3",
                graph_id="graph_s3_storage_compat",
            )
            == 1
        )
    finally:
        session.close()


def test_s3_rejects_manual_mode_for_write_trigger(monkeypatch):
    _set_defaults(monkeypatch)
    monkeypatch.setenv("FAIM_SELF_EVOLVE_TRIGGER_MODE", "manual")

    session = _new_session()
    try:
        _seed_graph_version(
            session,
            tenant_id="tenant_s3",
            graph_id="graph_s3_mode",
            version=5,
        )
        result = enqueue_self_evolve_if_due(
            session=session,
            tenant_id="tenant_s3",
            graph_id="graph_s3_mode",
            source="memory_write",
        )
        assert result.status == "skipped"
        assert result.reason.startswith("trigger_mode_not_write_triggered:")
    finally:
        session.close()


def test_s3_skips_when_jobs_disabled(monkeypatch):
    _set_defaults(monkeypatch)
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "false")

    session = _new_session()
    try:
        _seed_graph_version(
            session,
            tenant_id="tenant_s3",
            graph_id="graph_s3_jobs",
            version=5,
        )
        result = enqueue_self_evolve_if_due(
            session=session,
            tenant_id="tenant_s3",
            graph_id="graph_s3_jobs",
            source="memory_write",
        )
        assert result.status == "skipped"
        assert result.reason == "jobs_disabled"
    finally:
        session.close()


def test_s3_enqueue_then_reuse_existing_active_job(monkeypatch):
    _set_defaults(monkeypatch)

    session = _new_session()
    try:
        tenant_id = "tenant_s3"
        graph_id = "graph_s3_enqueue"
        _seed_graph_version(
            session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            version=7,
        )

        first = enqueue_self_evolve_if_due(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            source="memory_write",
        )
        assert first.status == "enqueued"
        assert first.job_id is not None

        second = enqueue_self_evolve_if_due(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            source="ingest_json",
        )
        assert second.status == "existing"
        assert second.job_id == first.job_id
        assert _count_evolve_jobs(session, tenant_id=tenant_id, graph_id=graph_id) == 1

        state_repo = SelfEvolutionStateRepo(session=session, tenant_id=tenant_id)
        state_row = state_repo.get(graph_id, session=session)
        assert state_row is not None
        assert int(state_row.last_seen_version) == 7
        assert str(state_row.last_enqueued_job_id) == str(first.job_id)
    finally:
        session.close()


def test_s3_respects_due_version_delta(monkeypatch):
    _set_defaults(monkeypatch)
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MIN_VERSION_DELTA", "5")

    session = _new_session()
    try:
        _seed_graph_version(
            session,
            tenant_id="tenant_s3",
            graph_id="graph_s3_delta",
            version=3,
        )
        result = enqueue_self_evolve_if_due(
            session=session,
            tenant_id="tenant_s3",
            graph_id="graph_s3_delta",
            source="memory_write",
        )
        assert result.status == "skipped"
        assert result.reason.startswith("not_due_version_delta:")
    finally:
        session.close()


def test_s3_respects_due_interval(monkeypatch):
    _set_defaults(monkeypatch)
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MIN_INTERVAL_SECONDS", "600")

    session = _new_session()
    try:
        tenant_id = "tenant_s3"
        graph_id = "graph_s3_interval"
        now = datetime(2026, 2, 17, 21, 0, 0, tzinfo=timezone.utc)

        _seed_graph_version(
            session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            version=10,
        )
        state_repo = SelfEvolutionStateRepo(session=session, tenant_id=tenant_id)
        state_repo.mark_evolved(
            graph_id=graph_id,
            evolved_version=9,
            evolved_at=now - timedelta(seconds=120),
            session=session,
        )
        session.commit()

        result = enqueue_self_evolve_if_due(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            source="memory_write",
            now=now,
        )
        assert result.status == "skipped"
        assert result.reason.startswith("not_due_interval:")
    finally:
        session.close()


def test_s3_due_evaluation_is_read_only_when_requested(monkeypatch):
    _set_defaults(monkeypatch)
    session = _new_session()
    try:
        tenant_id = "tenant_s3"
        graph_id = "graph_s3_read_only_status"
        _seed_graph_version(
            session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            version=4,
        )

        before = int(session.query(SelfEvolutionStateModel).count())
        evaluation = evaluate_self_evolve_due(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            source="memory_write",
            update_seen_version=False,
        )
        after = int(session.query(SelfEvolutionStateModel).count())

        assert evaluation.reason == "due_enqueued"
        assert evaluation.is_due is True
        assert before == after == 0
    finally:
        session.close()


def test_s3_due_evaluation_reports_active_job_reason(monkeypatch):
    _set_defaults(monkeypatch)
    session = _new_session()
    try:
        tenant_id = "tenant_s3"
        graph_id = "graph_s3_due_active"
        _seed_graph_version(
            session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            version=8,
        )
        first = enqueue_self_evolve_if_due(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            source="memory_write",
        )
        assert first.status == "enqueued"

        evaluation = evaluate_self_evolve_due(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            source="memory_write",
            update_seen_version=False,
        )
        assert evaluation.is_due is False
        assert evaluation.reason == "active_evolve_job_exists"
        assert str(evaluation.active_job_id) == str(first.job_id)
    finally:
        session.close()
