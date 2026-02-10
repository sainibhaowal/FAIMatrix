"""FAIM-Native Background Worker.

Polls for durable jobs and executes them.
Supports 'evolve' and potentially 'backup/restore' jobs.
"""

from __future__ import annotations

import logging
import signal
import time

from orchestration.evolve_flow import run_evolve
from orchestration.jobs.job_store import JobStore
from store.pg.session import get_session

logger = logging.getLogger(__name__)


class Worker:
    """Background worker for durable jobs."""

    def __init__(self, poll_interval: float = 1.0):
        self.poll_interval = poll_interval
        self.running = True

        # Setup signals
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    def _handle_exit(self, signum, frame):
        logger.info("Worker received exit signal. Shutting down gracefully...")
        self.running = False

    def run(self):
        """Main polling loop."""
        logger.info("Worker started.")

        while self.running:
            try:
                self._poll_and_execute()
            except Exception as e:
                logger.error(f"Worker iteration error: {e}")

            if self.running:
                time.sleep(self.poll_interval)

        logger.info("Worker stopped.")

    def _poll_and_execute(self):
        """Poll for next job and execute it."""
        session = get_session()
        try:
            job = JobStore.claim_next(session)
            if not job:
                return

            job_id = job.job_id
            kind = job.kind
            tenant_id = job.tenant_id
            graph_id = job.graph_id
            payload = job.payload_json or {}

            logger.info(f"Executing job {job_id} ({kind})")

            # Emit JOB_STARTED into main journal
            self._emit_journal_event(
                session,
                tenant_id,
                graph_id,
                "JOB_STARTED",
                {
                    "job_id": str(job_id),
                    "kind": kind,
                },
            )

            JobStore.append_event(
                session, job_id, "step_start", {"message": f"Starting {kind} job"}
            )

            try:
                if kind == "evolve":
                    self._run_evolve_job(session, tenant_id, graph_id, payload, job_id)
                elif kind == "storage_retention":
                    self._run_storage_retention_job(
                        session, tenant_id, graph_id, payload, job_id
                    )
                else:
                    raise ValueError(f"Unknown job kind: {kind}")

                # Success
                JobStore.mark_done(session, job_id)
                self._emit_journal_event(
                    session,
                    tenant_id,
                    graph_id,
                    "JOB_DONE",
                    {
                        "job_id": str(job_id),
                    },
                )

            except Exception as e:
                logger.error(f"Job {job_id} failed: {e}")
                JobStore.mark_failed(session, job_id, str(e))
                self._emit_journal_event(
                    session,
                    tenant_id,
                    graph_id,
                    "JOB_FAILED",
                    {
                        "job_id": str(job_id),
                        "error": str(e),
                    },
                )

            session.commit()

        finally:
            session.close()

    def _run_evolve_job(self, session, tenant_id, graph_id, payload, job_id):
        """Execute evolution job."""
        JobStore.append_event(
            session, job_id, "step_progress", {"message": "Running evolution cycle"}
        )

        # run_evolve handles its own lock internally
        result = run_evolve(
            graph_id=graph_id,
            tenant_id=tenant_id,
            session=session,
            profile=payload.get("profile", "strict"),
        )

        if result.status == "error":
            raise RuntimeError(result.error)

        JobStore.append_event(
            session,
            job_id,
            "step_progress",
            {
                "message": "Evolution cycle complete",
                "merges": result.merges,
                "prunes": result.prunes,
                "version": result.graph_version,
            },
        )

    def _run_storage_retention_job(self, session, tenant_id, graph_id, payload, job_id):
        """Execute storage retention cleanup job."""
        from orchestration.jobs.storage_retention import run_storage_retention_cleanup
        from runtime.context import _get_raw_store
        from store.pg.repos.event_repo import EventRepo
        from store.pg.repos.raw_repo import RawRepo
        from store.pg.repos.storage_file_repo import StorageFileRepo

        JobStore.append_event(
            session,
            job_id,
            "step_progress",
            {"message": "Running storage retention cleanup"},
        )

        result = run_storage_retention_cleanup(
            session=session,
            tenant_id=tenant_id,
            storage_file_repo=StorageFileRepo(tenant_id=tenant_id),
            raw_repo=RawRepo(tenant_id=tenant_id),
            raw_store=_get_raw_store(tenant_id),
            event_repo=EventRepo(tenant_id=tenant_id),
            graph_id=payload.get("graph_id") or graph_id,
            limit=int(payload.get("limit", 100)),
            dry_run=bool(payload.get("dry_run", True)),
            irreversible=bool(payload.get("irreversible", False)),
            reason=payload.get("reason"),
        )

        JobStore.append_event(
            session,
            job_id,
            "step_progress",
            {
                "message": "Storage retention cleanup complete",
                "dry_run": result.dry_run,
                "scanned": result.scanned,
                "deleted": result.deleted,
                "skipped": result.skipped,
                "failed": result.failed,
            },
        )

    def _emit_journal_event(self, session, tenant_id, graph_id, kind, payload):
        """Helper to emit event into the main EventJournal table."""
        try:
            from store.pg.repos.event_repo import EventRepo

            event_repo = EventRepo()
            event_repo.emit(session, graph_id, kind, payload)
        except Exception as e:
            logger.warning(f"Failed to emit journal event {kind}: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = Worker()
    worker.run()
