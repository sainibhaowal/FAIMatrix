"""Unit tests: JobStore filtered-claim behavior for worker-safe execution."""

from __future__ import annotations

from orchestration.jobs.job_store import JobStore


def test_claim_next_of_kinds_skips_non_executable_jobs(session_factory):
    with session_factory.session() as session:
        upload_job_id = JobStore.enqueue(
            session,
            tenant_id="tenant_job_filter",
            graph_id="graph_job_filter",
            kind="storage_upload",
            payload={"requested_files": 1},
        )
        evolve_job_id = JobStore.enqueue(
            session,
            tenant_id="tenant_job_filter",
            graph_id="graph_job_filter",
            kind="evolve",
            payload={"source": "test"},
        )

        claimed = JobStore.claim_next_of_kinds(
            session=session,
            executable_kinds=[
                "evolve",
                "storage_upload",
                "crypto_rotation",
                "ingest_secondary_index",
                "storage_retention",
                "raw_reencryption",
            ],
        )

        assert claimed is not None
        assert str(claimed.job_id) == str(upload_job_id)
        assert claimed.kind == "storage_upload"

        evolve_job = JobStore.get_job(session, evolve_job_id)
        assert evolve_job is not None
        assert evolve_job.status == "pending"


def test_claim_next_of_kinds_returns_none_for_empty_kinds(session_factory):
    with session_factory.session() as session:
        JobStore.enqueue(
            session,
            tenant_id="tenant_job_filter_empty",
            graph_id="graph_job_filter_empty",
            kind="storage_upload",
            payload={"requested_files": 1},
        )

        claimed = JobStore.claim_next_of_kinds(session=session, executable_kinds=[])
        assert claimed is None

        fallback_claim = JobStore.claim_next(session=session)
        assert fallback_claim is not None
        assert fallback_claim.kind == "storage_upload"
