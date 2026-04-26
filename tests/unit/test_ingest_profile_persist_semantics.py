"""Phase R7 unit checks: ingest strict/relaxed profile-persist semantics."""

from __future__ import annotations

from dataclasses import dataclass

import pytest


@dataclass
class _FakeWriteResult:
    graph_version: int = 7
    nodes_written: int = 2
    merges: int = 1
    node_ids: list[str] | None = None
    diagnostics_hash: str | None = None


class _FakeVector:
    def __init__(self, idx: int):
        self.v_native = [0.0] * 256
        self.vector_hash = f"vec-{idx}"


class _FakeEventRepo:
    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    def emit(self, _session, graph_id, kind, payload):
        self.events.append((kind, {"graph_id": graph_id, **dict(payload or {})}))


class _DummySession:
    def __init__(self):
        self.added = 0
        self.commits = 0
        self.flushes = 0
        self.rollbacks = 0

    def add(self, _obj):
        self.added += 1

    def commit(self):
        self.commits += 1

    def flush(self):
        self.flushes += 1

    def rollback(self):
        self.rollbacks += 1


def _install_ingest_mocks(monkeypatch):
    from store.pg.models_faim import IngestDedupModel

    monkeypatch.setattr(
        "perception.router.route_extraction",
        lambda _bytes, _filename, _raw_id, **kwargs: [object(), object()],
    )
    monkeypatch.setattr(
        "perception.packetize.create_packet",
        lambda _raw_id, _blocks: type("Packet", (), {"packet_hash": "packet-r7-hash"})(),
    )
    monkeypatch.setattr("perception.validate.assert_valid", lambda _packet, _blocks: None)
    monkeypatch.setattr(
        "encoding.vectorize_blocks",
        lambda blocks: [_FakeVector(i) for i, _ in enumerate(blocks)],
    )

    class _FakeEngine:
        def __init__(self, **_kwargs):
            pass

        def write_atoms(self, **_kwargs):
            return _FakeWriteResult(node_ids=["n1", "n2"])

    monkeypatch.setattr("core.engine.FAIMNativeEngine", _FakeEngine)
    monkeypatch.setattr(
        IngestDedupModel,
        "check_exists",
        classmethod(lambda cls, _session, _tenant_id, _graph_id, _packet_hash: None),
    )
    monkeypatch.setattr(
        IngestDedupModel,
        "record_ingest",
        classmethod(
            lambda cls,
            _session,
            _tenant_id,
            _graph_id,
            _packet_hash,
            _raw_id,
            _node_count: None
        ),
    )


def _run_ingest(monkeypatch, *, profile: str, persist_mode: str, jobs_enabled: bool):
    from orchestration.ingest_flow import run_ingest

    _install_ingest_mocks(monkeypatch)
    monkeypatch.setenv("FAIM_PROFILE_PERSIST_COMPAT_MODE", "false")
    monkeypatch.setenv("FAIM_ENABLE_JOBS", "true" if jobs_enabled else "false")
    monkeypatch.setattr(
        "orchestration.ingest_flow._upsert_index_sync",
        lambda **kwargs: len(kwargs.get("vectors", [])),
    )
    monkeypatch.setattr(
        "orchestration.ingest_flow._enqueue_async_index_upsert_job",
        lambda **_kwargs: "job-r7-queued",
    )

    session = _DummySession()
    event_repo = _FakeEventRepo()
    result = run_ingest(
        graph_id="graph_r7_ingest",
        raw_id="11111111-1111-1111-1111-111111111111",
        filename="r7.txt",
        file_bytes=b"phase-r7-ingest",
        tenant_id="tenant_r7",
        session=session,
        profile=profile,
        persist_mode=persist_mode,
        event_repo=event_repo,
        node_repo=object(),
        edge_repo=object(),
        gv_repo=object(),
    )
    return result, event_repo


def test_r7_ingest_strict_profile_strict_persist_skips_index(monkeypatch):
    result, event_repo = _run_ingest(
        monkeypatch,
        profile="strict",
        persist_mode="strict",
        jobs_enabled=True,
    )

    assert result.status == "completed"
    assert result.requested_profile == "strict"
    assert result.requested_persist_mode == "strict"
    assert result.effective_profile == "strict"
    assert result.effective_persist_mode == "strict"
    assert result.durability_path == "sync_strict"
    assert result.index_write_mode == "skipped_profile_strict"
    assert result.secondary_task_status == "skipped_profile_strict"
    assert result.secondary_task_job_id is None
    assert any(kind == "INDEX_UPSERT_SKIPPED" for kind, _ in event_repo.events)


def test_r7_ingest_fast_profile_strict_persist_applies_sync_secondary(monkeypatch):
    result, event_repo = _run_ingest(
        monkeypatch,
        profile="fast",
        persist_mode="strict",
        jobs_enabled=True,
    )

    assert result.status == "completed"
    assert result.requested_profile == "fast"
    assert result.requested_persist_mode == "strict"
    assert result.effective_profile == "fast"
    assert result.effective_persist_mode == "strict"
    assert result.durability_path == "sync_strict"
    assert result.index_write_mode == "sync_inline"
    assert result.secondary_task_status == "completed_sync"
    assert result.secondary_task_job_id is None
    assert any(kind == "INDEX_UPSERTED" for kind, _ in event_repo.events)


def test_r7_ingest_fast_profile_relaxed_persist_queues_secondary_when_jobs_enabled(
    monkeypatch,
):
    result, event_repo = _run_ingest(
        monkeypatch,
        profile="fast",
        persist_mode="relaxed",
        jobs_enabled=True,
    )

    assert result.status == "completed"
    assert result.requested_profile == "fast"
    assert result.requested_persist_mode == "relaxed"
    assert result.effective_profile == "fast"
    assert result.effective_persist_mode == "relaxed"
    assert result.durability_path == "core_sync_secondary_async"
    assert result.index_write_mode == "async_queued"
    assert result.secondary_task_status == "queued"
    assert result.secondary_task_job_id == "job-r7-queued"
    assert any(kind == "INDEX_UPSERT_QUEUED" for kind, _ in event_repo.events)


def test_r7_ingest_fast_profile_relaxed_persist_sync_fallback_when_jobs_disabled(
    monkeypatch,
):
    result, event_repo = _run_ingest(
        monkeypatch,
        profile="fast",
        persist_mode="relaxed",
        jobs_enabled=False,
    )

    assert result.status == "completed"
    assert result.requested_profile == "fast"
    assert result.requested_persist_mode == "relaxed"
    assert result.effective_profile == "fast"
    assert result.effective_persist_mode == "relaxed"
    assert result.durability_path == "core_sync_secondary_async"
    assert result.index_write_mode == "sync_fallback_no_jobs"
    assert result.secondary_task_status == "completed_sync_fallback"
    assert result.secondary_task_job_id is None
    assert any(kind == "INDEX_UPSERTED" for kind, _ in event_repo.events)

