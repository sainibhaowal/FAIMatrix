"""Phase B: upload/job cancellation behavior."""

from __future__ import annotations


def test_cancel_requested_job_is_not_claimed(session_factory):
    from orchestration.jobs.job_store import JobStore

    with session_factory.session() as session:
        job_id = JobStore.enqueue(
            session,
            tenant_id="tenant_phase_b",
            graph_id="graph_phase_b",
            kind="storage_upload",
            payload={"requested_files": 2},
        )

        updated = JobStore.request_cancel(session, job_id, reason="user_cancelled")
        assert updated is not None
        assert (updated.payload_json or {}).get("cancel_requested") is True
        assert JobStore.is_cancel_requested(session, job_id) is True

        claimed = JobStore.claim_next(session)
        assert claimed is None

        final = JobStore.get_job(session, job_id)
        assert final is not None
        assert final.status == "cancelled"
        assert "user_cancelled" in str(final.error_message or "")


def test_mark_done_honors_cancel_request(session_factory):
    from orchestration.jobs.job_store import JobStore

    with session_factory.session() as session:
        job_id = JobStore.enqueue(
            session,
            tenant_id="tenant_phase_b",
            graph_id="graph_phase_b",
            kind="storage_upload",
            payload={"requested_files": 1},
        )
        claimed = JobStore.claim_next(session)
        assert claimed is not None
        assert claimed.status == "running"

        JobStore.request_cancel(session, job_id, reason="stop_now")
        JobStore.mark_done(session, job_id)

        final = JobStore.get_job(session, job_id)
        assert final is not None
        assert final.status == "cancelled"
        assert "stop_now" in str(final.error_message or "")
