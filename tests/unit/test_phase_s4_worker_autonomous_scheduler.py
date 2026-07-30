"""Phase S4 tests: worker autonomous self-evolve scheduling fallback."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from orchestration.jobs.worker import Worker
from orchestration.self_evolve_scheduler import (
    SelfEvolveScanSummary,
    scan_and_enqueue_due_self_evolve_jobs,
)
from sqlalchemy import and_, create_engine
from sqlalchemy.orm import sessionmaker
from store.pg.models_faim import JobModel, create_all_tables
from store.pg.repos.graph_version_repo import GraphVersionRepo


def _new_session():
    engine = create_engine("sqlite:///:memory:")
    create_all_tables(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _set_periodic_defaults(monkeypatch):
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_ENABLED", "true")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_TRIGGER_MODE", "periodic")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MIN_INTERVAL_SECONDS", "30")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MIN_VERSION_DELTA", "1")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MAX_ACTIONS", "25")
    monkeypatch.setenv("FAIM_SELF_EVOLVE_SCAN_INTERVAL_SECONDS", "60")
    monkeypatch.setenv("FAIM_SELF_INVENT_ENABLED", "false")
    monkeypatch.setenv("FAIM_SELF_INVENT_AFTER_UPLOAD", "false")
    monkeypatch.setenv("FAIM_SELF_INVENT_ON_EVOLVE", "true")


def _seed_graph(session, *, tenant_id: str, graph_id: str, version: int):
    gv_repo = GraphVersionRepo(session=session, tenant_id=tenant_id)
    gv_repo.set_version(session, graph_id, version, "seed")
    session.commit()


def _count_evolve_jobs(session, *, tenant_id: str) -> int:
    return int(
        session.query(JobModel)
        .filter(
            and_(
                JobModel.tenant_id == tenant_id,
                JobModel.kind == "evolve",
            )
        )
        .count()
    )


def test_s4_periodic_scan_enqueues_due_graph(monkeypatch):
    _set_periodic_defaults(monkeypatch)
    session = _new_session()
    try:
        _seed_graph(
            session,
            tenant_id="tenant_s4",
            graph_id="graph_s4_due",
            version=4,
        )

        summary = scan_and_enqueue_due_self_evolve_jobs(
            session=session,
            tenant_id="tenant_s4",
            source="periodic_worker",
            now=datetime(2026, 2, 17, 22, 0, 0, tzinfo=timezone.utc),
        )
        assert summary.reason is None
        assert summary.scanned_graphs == 1
        assert summary.enqueued == 1
        assert _count_evolve_jobs(session, tenant_id="tenant_s4") == 1

        row = (
            session.query(JobModel)
            .filter(
                and_(
                    JobModel.tenant_id == "tenant_s4",
                    JobModel.kind == "evolve",
                )
            )
            .first()
        )
        assert row is not None
        payload = dict(row.payload_json or {})
        assert payload.get("source") == "periodic_worker"
    finally:
        session.close()


def test_s4_periodic_scan_skips_for_non_periodic_mode(monkeypatch):
    _set_periodic_defaults(monkeypatch)
    monkeypatch.setenv("FAIM_SELF_EVOLVE_TRIGGER_MODE", "post_upload")

    session = _new_session()
    try:
        _seed_graph(
            session,
            tenant_id="tenant_s4",
            graph_id="graph_s4_mode_skip",
            version=3,
        )
        summary = scan_and_enqueue_due_self_evolve_jobs(
            session=session,
            tenant_id="tenant_s4",
            source="periodic_worker",
        )
        assert summary.scanned_graphs == 0
        assert summary.enqueued == 0
        assert summary.reason is not None
        assert summary.reason.startswith("trigger_mode_not_periodic:")
    finally:
        session.close()


def test_s4_periodic_scan_respects_max_actions(monkeypatch):
    _set_periodic_defaults(monkeypatch)
    monkeypatch.setenv("FAIM_SELF_EVOLVE_MAX_ACTIONS", "1")

    session = _new_session()
    try:
        for idx in range(1, 4):
            _seed_graph(
                session,
                tenant_id="tenant_s4",
                graph_id=f"graph_s4_limit_{idx}",
                version=idx + 1,
            )

        summary = scan_and_enqueue_due_self_evolve_jobs(
            session=session,
            tenant_id="tenant_s4",
            source="periodic_worker",
            now=datetime(2026, 2, 17, 22, 0, 0, tzinfo=timezone.utc),
        )
        assert summary.scanned_graphs == 1
        assert summary.enqueued == 1
        assert _count_evolve_jobs(session, tenant_id="tenant_s4") == 1
    finally:
        session.close()


def test_s4_worker_scan_interval_throttle(monkeypatch):
    import orchestration.jobs.worker as worker_mod

    class DummySession:
        def close(self):
            return None

    calls = {"get_session": 0}

    def fake_get_session():
        calls["get_session"] += 1
        return DummySession()

    monkeypatch.setattr(worker_mod, "get_session", fake_get_session)
    monkeypatch.setattr(
        "orchestration.self_evolve_scheduler.list_self_evolve_tenants",
        lambda session: [],
    )

    worker = Worker(poll_interval=1.0, self_evolve_scan_interval_seconds=120.0)
    worker._last_self_evolve_scan_monotonic = time.monotonic()
    worker._maybe_run_self_evolve_scan()
    assert calls["get_session"] == 0

    worker._last_self_evolve_scan_monotonic = 0.0
    worker._maybe_run_self_evolve_scan()
    assert calls["get_session"] == 1


def test_s4_worker_scan_calls_scheduler_per_tenant(monkeypatch):
    import orchestration.jobs.worker as worker_mod

    class DummySession:
        def close(self):
            return None

    called_tenants: list[str] = []

    monkeypatch.setattr(worker_mod, "get_session", lambda: DummySession())
    monkeypatch.setattr(
        "orchestration.self_evolve_scheduler.list_self_evolve_tenants",
        lambda session: ["tenant_a", "tenant_b"],
    )

    def _fake_scan(**kwargs):
        called_tenants.append(str(kwargs["tenant_id"]))
        return SelfEvolveScanSummary(
            tenant_id=str(kwargs["tenant_id"]),
            scanned_graphs=0,
            enqueued=0,
            existing=0,
            skipped=0,
            errors=0,
            trigger_mode="periodic",
            reason=None,
        )

    monkeypatch.setattr(
        "orchestration.self_evolve_scheduler.scan_and_enqueue_due_self_evolve_jobs",
        _fake_scan,
    )

    worker = Worker(poll_interval=1.0, self_evolve_scan_interval_seconds=0.0)
    worker._last_self_evolve_scan_monotonic = 0.0
    worker._maybe_run_self_evolve_scan()
    assert called_tenants == ["tenant_a", "tenant_b"]
