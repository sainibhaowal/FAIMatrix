"""Unit tests for StorageFileRepo."""

from __future__ import annotations

from uuid import uuid4

from store.pg.repos.storage_file_repo import StorageFileRepo


def test_upsert_and_mark_ingest(session_factory):
    repo = StorageFileRepo(tenant_id="tenant-test")
    raw_id = uuid4()

    with session_factory.atomic() as session:
        row = repo.upsert_upload(
            session,
            graph_id="g1",
            raw_id=raw_id,
            filename="alpha.txt",
            mime_type="text/plain",
            size_bytes=100,
            sha256="a" * 64,
            job_id=None,
        )
        assert row.ingest_status == "uploaded"

        repo.mark_ingesting(session, raw_id=raw_id, graph_id="g1", job_id=None)
        row2 = repo.mark_ingest_result(
            session,
            raw_id=raw_id,
            graph_id="g1",
            status="completed",
            packet_hash="p" * 64,
            node_count=12,
            vector_count=12,
            error_message=None,
            job_id=None,
        )
        assert row2 is not None
        assert row2.ingest_status == "ingested"
        assert row2.node_count == 12

    with session_factory.session() as session:
        fetched = repo.get_by_raw_id(session, raw_id, "g1")
        assert fetched is not None
        assert fetched.filename == "alpha.txt"
        assert fetched.packet_hash == "p" * 64


def test_list_and_summary(session_factory):
    repo = StorageFileRepo(tenant_id="tenant-summary")

    with session_factory.atomic() as session:
        repo.upsert_upload(
            session,
            graph_id="g-summary",
            raw_id=uuid4(),
            filename="doc1.pdf",
            mime_type="application/pdf",
            size_bytes=2048,
            sha256="1" * 64,
            job_id=None,
        )
        r2_id = uuid4()
        repo.upsert_upload(
            session,
            graph_id="g-summary",
            raw_id=r2_id,
            filename="doc2.txt",
            mime_type="text/plain",
            size_bytes=512,
            sha256="2" * 64,
            job_id=None,
        )
        repo.mark_ingest_result(
            session,
            raw_id=r2_id,
            graph_id="g-summary",
            status="error",
            packet_hash=None,
            node_count=0,
            vector_count=0,
            error_message="failed",
            job_id=None,
        )

    with session_factory.session() as session:
        rows, total = repo.list_files(
            session,
            graph_id="g-summary",
            status=None,
            query=None,
            limit=50,
            offset=0,
            include_delete_requested=True,
        )
        assert total == 2
        assert len(rows) == 2

        summary = repo.summary(session, graph_id="g-summary")
        assert summary["total_files"] == 2
        assert summary["total_bytes"] == 2560
        assert summary["by_status"].get("uploaded", 0) >= 1
        assert summary["by_status"].get("failed", 0) >= 1
