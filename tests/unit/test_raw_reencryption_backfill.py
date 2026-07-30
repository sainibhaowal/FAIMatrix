"""P2 tests: legacy raw re-encryption backfill."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orchestration.jobs.raw_reencryption import run_raw_reencryption_backfill
from store.pg.repos.raw_repo import RawRepo
from store.pg.repos.storage_file_repo import StorageFileRepo


def _make_encrypted_store(*, inner, session_factory, tenant_id: str, monkeypatch):
    monkeypatch.setenv("FAIM_MASTER_KEY", "33" * 32)

    from store.raw.crypto import EnvelopeCipher
    from store.raw.encrypted_payload_store import EncryptedRawStore

    return EncryptedRawStore(
        inner=inner,
        cipher=EnvelopeCipher(tenant_id=tenant_id, session_factory=session_factory.create),
        graph_id=tenant_id,
    )


def _seed_legacy_raw(session, *, store, tenant_id: str, graph_id: str, payload: bytes):
    raw_repo = RawRepo(tenant_id=tenant_id)
    storage_repo = StorageFileRepo(tenant_id=tenant_id)

    raw_ref = store.store(payload, mime_type="text/plain", graph_id=graph_id)
    saved = raw_repo.create(session, raw_ref)

    storage_repo.upsert_upload(
        session,
        graph_id=graph_id,
        raw_id=saved.id,
        filename=f"{tenant_id}.txt",
        mime_type="text/plain",
        size_bytes=len(payload),
        sha256=str(saved.sha256),
        job_id=None,
    )
    session.commit()
    return saved, raw_repo, storage_repo


def test_raw_reencryption_dry_run_execute_and_rerun_idempotent(
    session_factory, raw_store, monkeypatch
):
    tenant_id = "tenant_raw_reencryption_single"
    graph_id = "graph_raw_reencryption_single"
    payload = b"legacy-plaintext-payload"

    with session_factory.session() as session:
        saved, raw_repo, storage_repo = _seed_legacy_raw(
            session,
            store=raw_store,
            tenant_id=tenant_id,
            graph_id=graph_id,
            payload=payload,
        )
        encrypted_store = _make_encrypted_store(
            inner=raw_store,
            session_factory=session_factory,
            tenant_id=tenant_id,
            monkeypatch=monkeypatch,
        )
        cutoff = datetime.now(timezone.utc) + timedelta(days=1)

        dry_run = run_raw_reencryption_backfill(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            cutoff_created_at=cutoff,
            raw_repo=raw_repo,
            storage_file_repo=storage_repo,
            raw_store=encrypted_store,
            page_size=50,
            dry_run=True,
            irreversible=False,
            reason="dry-run",
        )
        assert dry_run.scanned == 1
        assert dry_run.reencrypted == 0
        assert dry_run.already_encrypted == 0
        assert dry_run.results[0].status == "would_reencrypt"

        executed = run_raw_reencryption_backfill(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            cutoff_created_at=cutoff,
            raw_repo=raw_repo,
            storage_file_repo=storage_repo,
            raw_store=encrypted_store,
            page_size=50,
            dry_run=False,
            irreversible=True,
            reason="execute",
        )
        assert executed.scanned == 1
        assert executed.reencrypted == 1
        assert executed.failed == 0
        assert executed.results[0].status == "reencrypted"
        assert executed.results[0].raw_ref_updated is True

        migrated = raw_repo.get_by_id(session, saved.id)
        assert migrated is not None
        assert migrated.sha256 != str(saved.sha256)
        assert storage_repo.get_by_raw_id(session, saved.id, graph_id).sha256 == migrated.sha256
        assert encrypted_store.load(migrated, verify=True) == payload
        assert raw_store.exists_by_sha(str(saved.sha256)) is False

        rerun = run_raw_reencryption_backfill(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            cutoff_created_at=cutoff,
            raw_repo=raw_repo,
            storage_file_repo=storage_repo,
            raw_store=encrypted_store,
            page_size=50,
            dry_run=True,
            irreversible=False,
            reason="rerun",
        )
        assert rerun.scanned == 1
        assert rerun.already_encrypted == 1
        assert rerun.reencrypted == 0
        assert rerun.results[0].status == "already_encrypted"


def test_raw_reencryption_preserves_shared_plaintext_blob_until_last_ref(
    session_factory, raw_store, monkeypatch
):
    tenant_a = "tenant_raw_reencryption_a"
    tenant_b = "tenant_raw_reencryption_b"
    graph_a = "graph_raw_reencryption_a"
    graph_b = "graph_raw_reencryption_b"
    payload = b"shared-plaintext-payload"

    with session_factory.session() as session:
        saved_a, raw_repo_a, storage_repo_a = _seed_legacy_raw(
            session,
            store=raw_store,
            tenant_id=tenant_a,
            graph_id=graph_a,
            payload=payload,
        )
        saved_b, raw_repo_b, storage_repo_b = _seed_legacy_raw(
            session,
            store=raw_store,
            tenant_id=tenant_b,
            graph_id=graph_b,
            payload=payload,
        )

        encrypted_a = _make_encrypted_store(
            inner=raw_store,
            session_factory=session_factory,
            tenant_id=tenant_a,
            monkeypatch=monkeypatch,
        )
        encrypted_b = _make_encrypted_store(
            inner=raw_store,
            session_factory=session_factory,
            tenant_id=tenant_b,
            monkeypatch=monkeypatch,
        )
        cutoff = datetime.now(timezone.utc) + timedelta(days=1)

        result_a = run_raw_reencryption_backfill(
            session=session,
            tenant_id=tenant_a,
            graph_id=graph_a,
            cutoff_created_at=cutoff,
            raw_repo=raw_repo_a,
            storage_file_repo=storage_repo_a,
            raw_store=encrypted_a,
            page_size=50,
            dry_run=False,
            irreversible=True,
            reason="tenant-a",
        )
        assert result_a.reencrypted == 1
        assert result_a.results[0].legacy_blob_deleted is False
        assert raw_store.exists_by_sha(str(saved_a.sha256)) is True

        result_b = run_raw_reencryption_backfill(
            session=session,
            tenant_id=tenant_b,
            graph_id=graph_b,
            cutoff_created_at=cutoff,
            raw_repo=raw_repo_b,
            storage_file_repo=storage_repo_b,
            raw_store=encrypted_b,
            page_size=50,
            dry_run=False,
            irreversible=True,
            reason="tenant-b",
        )
        assert result_b.reencrypted == 1
        assert result_b.results[0].legacy_blob_deleted is True
        assert raw_store.exists_by_sha(str(saved_b.sha256)) is False

        migrated_a = raw_repo_a.get_by_id(session, saved_a.id)
        migrated_b = raw_repo_b.get_by_id(session, saved_b.id)
        assert migrated_a is not None and migrated_b is not None
        assert storage_repo_a.get_by_raw_id(session, saved_a.id, graph_a).sha256 == migrated_a.sha256
        assert storage_repo_b.get_by_raw_id(session, saved_b.id, graph_b).sha256 == migrated_b.sha256
