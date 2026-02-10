"""Phase B: storage retention cleanup worker tests."""

from __future__ import annotations

from orchestration.jobs.storage_retention import run_storage_retention_cleanup
from store.pg.repos.event_repo import EventRepo
from store.pg.repos.raw_repo import RawRepo
from store.pg.repos.storage_file_repo import StorageFileRepo


def _seed_delete_requested(session, raw_store, tenant_id: str, graph_id: str):
    raw_repo = RawRepo(tenant_id=tenant_id)
    storage_repo = StorageFileRepo(tenant_id=tenant_id)

    payload = b"phase-b-retention-payload"
    raw_ref = raw_store.store(payload, mime_type="text/plain", graph_id=graph_id)
    saved = raw_repo.create(session, raw_ref)

    storage_repo.upsert_upload(
        session,
        graph_id=graph_id,
        raw_id=saved.id,
        filename="retention.txt",
        mime_type="text/plain",
        size_bytes=len(payload),
        sha256=str(saved.sha256),
        job_id=None,
    )
    storage_repo.mark_delete_requested(
        session,
        raw_id=saved.id,
        graph_id=graph_id,
        reason="retention-test",
    )
    session.commit()
    return saved


def test_retention_requires_irreversible_for_physical_delete(session_factory, raw_store):
    tenant_id = "tenant_retention_guardrail"
    graph_id = "graph_retention_guardrail"

    with session_factory.session() as session:
        _seed_delete_requested(session, raw_store, tenant_id, graph_id)
        storage_repo = StorageFileRepo(tenant_id=tenant_id)
        raw_repo = RawRepo(tenant_id=tenant_id)

        try:
            run_storage_retention_cleanup(
                session=session,
                tenant_id=tenant_id,
                storage_file_repo=storage_repo,
                raw_repo=raw_repo,
                raw_store=raw_store,
                event_repo=EventRepo(tenant_id=tenant_id),
                graph_id=graph_id,
                limit=100,
                dry_run=False,
                irreversible=False,
                reason="test",
            )
            assert False, "expected ValueError for irreversible guardrail"
        except ValueError as exc:
            assert "irreversible=true" in str(exc)


def test_retention_dry_run_and_execute(session_factory, raw_store):
    tenant_id = "tenant_retention_phase_b"
    graph_id = "graph_retention_phase_b"

    with session_factory.session() as session:
        saved = _seed_delete_requested(session, raw_store, tenant_id, graph_id)
        storage_repo = StorageFileRepo(tenant_id=tenant_id)
        raw_repo = RawRepo(tenant_id=tenant_id)
        event_repo = EventRepo(tenant_id=tenant_id)

        dry_run = run_storage_retention_cleanup(
            session=session,
            tenant_id=tenant_id,
            storage_file_repo=storage_repo,
            raw_repo=raw_repo,
            raw_store=raw_store,
            event_repo=event_repo,
            graph_id=graph_id,
            limit=100,
            dry_run=True,
            irreversible=False,
            reason="dry-run",
        )
        assert dry_run.scanned == 1
        assert dry_run.deleted == 0
        assert dry_run.skipped == 1
        assert dry_run.results[0].status == "would_delete"

        pre_ref = raw_repo.get_by_id(session, saved.id)
        assert pre_ref is not None
        assert raw_store.exists(pre_ref) is True

        executed = run_storage_retention_cleanup(
            session=session,
            tenant_id=tenant_id,
            storage_file_repo=storage_repo,
            raw_repo=raw_repo,
            raw_store=raw_store,
            event_repo=event_repo,
            graph_id=graph_id,
            limit=100,
            dry_run=False,
            irreversible=True,
            reason="execute",
        )
        assert executed.scanned == 1
        assert executed.deleted == 1
        assert executed.failed == 0
        assert executed.results[0].status == "deleted"
        assert executed.results[0].raw_ref_deleted is True

        assert raw_repo.get_by_id(session, saved.id) is None
        row = storage_repo.get_by_raw_id(session, saved.id, graph_id)
        assert row is not None
        assert row.ingest_status == "deleted"

        events = event_repo.get_all(session, graph_id=graph_id, limit=200)
        kinds = [event.kind for event in events]
        assert "STORAGE_DELETE_EXECUTED" in kinds
