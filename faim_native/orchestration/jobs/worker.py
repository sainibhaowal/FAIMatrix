"""FAIM-Native Background Worker.

Polls for durable jobs and executes them.
Supports 'evolve' and potentially 'backup/restore' jobs.
"""

from __future__ import annotations

import logging
import signal
import time
from uuid import UUID

from orchestration.evolve_flow import run_evolve
from orchestration.jobs.job_store import JobStore
from runtime.feature_flags import get_feature_flags
from store.pg.session import get_session

logger = logging.getLogger(__name__)


class Worker:
    """Background worker for durable jobs."""

    def __init__(
        self,
        poll_interval: float = 1.0,
        self_evolve_scan_interval_seconds: float | None = None,
    ):
        self.poll_interval = poll_interval
        self.running = True
        flags = get_feature_flags()
        default_scan_interval = max(
            30,
            int(getattr(flags, "self_evolve_scan_interval_seconds", 60)),
        )
        self.self_evolve_scan_interval_seconds = float(
            self_evolve_scan_interval_seconds
            if self_evolve_scan_interval_seconds is not None
            else default_scan_interval
        )
        self._last_self_evolve_scan_monotonic = 0.0

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
                self._maybe_run_self_evolve_scan()
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
                elif kind == "ingest_secondary_index":
                    self._run_ingest_secondary_index_job(
                        session, tenant_id, graph_id, payload, job_id
                    )
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

    def _maybe_run_self_evolve_scan(self):
        """Run periodic autonomous self-evolve scan (tenant-scoped)."""
        now_mono = time.monotonic()
        if (
            now_mono - self._last_self_evolve_scan_monotonic
            < self.self_evolve_scan_interval_seconds
        ):
            return
        self._last_self_evolve_scan_monotonic = now_mono

        session = get_session()
        try:
            from orchestration.self_evolve_scheduler import (
                list_self_evolve_tenants,
                scan_and_enqueue_due_self_evolve_jobs,
            )

            tenants = list_self_evolve_tenants(session=session)
            if not tenants:
                return

            for tenant_id in tenants:
                summary = scan_and_enqueue_due_self_evolve_jobs(
                    session=session,
                    tenant_id=tenant_id,
                    source="periodic_worker",
                )
                if (
                    summary.enqueued > 0
                    or summary.existing > 0
                    or summary.errors > 0
                    or summary.reason is not None
                ):
                    logger.info(
                        "self-evolve periodic scan tenant=%s mode=%s scanned=%d enqueued=%d existing=%d skipped=%d errors=%d reason=%s",
                        tenant_id,
                        summary.trigger_mode,
                        summary.scanned_graphs,
                        summary.enqueued,
                        summary.existing,
                        summary.skipped,
                        summary.errors,
                        summary.reason,
                    )
        except Exception as e:  # nosec B110
            logger.error("Self-evolve periodic scan failed: %s", e)
        finally:
            session.close()

    def _run_evolve_job(self, session, tenant_id, graph_id, payload, job_id):
        """Execute evolution job."""
        from orchestration.profile_persist_policy import (
            PolicyOperation,
            resolve_profile_persist_policy,
        )

        requested_profile = str(payload.get("profile", "strict"))
        requested_persist_mode = str(payload.get("persist_mode", "relaxed"))
        policy = resolve_profile_persist_policy(
            operation=PolicyOperation.EVOLVE,
            requested_profile=requested_profile,
            requested_persist_mode=requested_persist_mode,
        )

        JobStore.append_event(
            session,
            job_id,
            "step_progress",
            {
                "message": "Running evolution cycle",
                "requested_profile": requested_profile,
                "requested_persist_mode": requested_persist_mode,
                "effective_profile": policy.effective_profile,
                "effective_persist_mode": policy.effective_persist_mode,
                "profile_persist_compat_mode": policy.compatibility_mode,
            },
        )

        # run_evolve handles its own lock internally
        result = run_evolve(
            graph_id=graph_id,
            tenant_id=tenant_id,
            session=session,
            profile=policy.effective_profile,
            persist_mode=policy.effective_persist_mode,
            self_invent_requested=payload.get("self_invent_requested"),
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

    def _run_ingest_secondary_index_job(
        self,
        session,
        tenant_id,
        graph_id,
        payload,
        job_id,
    ):
        """Execute async secondary index upsert for relaxed ingest durability."""
        from sqlalchemy import and_

        from index.qdrant_index import FAIMIndex
        from store.pg.models_faim import NodeModel

        requested_profile = str(payload.get("requested_profile") or "")
        requested_persist_mode = str(payload.get("requested_persist_mode") or "")
        effective_profile = str(payload.get("effective_profile") or "")
        effective_persist_mode = str(payload.get("effective_persist_mode") or "")
        durability_path = str(payload.get("durability_path") or "")
        packet_hash = str(payload.get("packet_hash") or "")
        raw_id = str(payload.get("raw_id") or "")

        node_ids_raw = payload.get("node_ids") or []
        node_ids: list[UUID] = []
        for item in node_ids_raw:
            try:
                node_ids.append(UUID(str(item)))
            except (ValueError, TypeError, AttributeError):
                continue

        if not node_ids:
            JobStore.append_event(
                session,
                job_id,
                "step_progress",
                {
                    "message": "No valid node_ids provided for async index upsert",
                    "requested_profile": requested_profile,
                    "requested_persist_mode": requested_persist_mode,
                    "effective_profile": effective_profile,
                    "effective_persist_mode": effective_persist_mode,
                    "durability_path": durability_path,
                },
            )
            return

        # Keep deterministic ordering for repeatable upsert behavior.
        nodes = (
            session.query(
                NodeModel.node_id,
                NodeModel.v_native,
                NodeModel.level,
                NodeModel.kind,
            )
            .filter(
                and_(
                    NodeModel.tenant_id == tenant_id,
                    NodeModel.graph_id == graph_id,
                    NodeModel.node_id.in_(node_ids),
                )
            )
            .order_by(NodeModel.created_at.asc(), NodeModel.node_id.asc())
            .all()
        )

        project_id_raw = payload.get("project_id")
        try:
            project_id = UUID(str(project_id_raw))
        except (ValueError, TypeError, AttributeError):
            try:
                project_id = UUID(str(graph_id))
            except (ValueError, TypeError, AttributeError):
                project_id = UUID("00000000-0000-0000-0000-000000000000")

        index = FAIMIndex(project_id)
        indexed = 0
        failed = 0

        for node in nodes:
            try:
                vector = list(node.v_native or [])
                if not vector:
                    failed += 1
                    continue
                index.add(
                    graph_id=graph_id,
                    node_id=str(node.node_id),
                    vector=vector,
                    level=int(node.level or 0),
                    kind=str(node.kind or "atom"),
                )
                indexed += 1
            except Exception as exc:  # nosec B110
                failed += 1
                logger.warning(
                    "Async index upsert failed for node=%s graph=%s: %s",
                    getattr(node, "node_id", "unknown"),
                    graph_id,
                    exc,
                )

        missing = max(0, len(node_ids) - len(nodes))

        JobStore.append_event(
            session,
            job_id,
            "step_progress",
            {
                "message": "Async ingest secondary index upsert complete",
                "requested_profile": requested_profile,
                "requested_persist_mode": requested_persist_mode,
                "effective_profile": effective_profile,
                "effective_persist_mode": effective_persist_mode,
                "durability_path": durability_path,
                "indexed": indexed,
                "failed": failed,
                "missing": missing,
                "raw_id": raw_id,
                "packet_hash": packet_hash,
            },
        )

        self._emit_journal_event(
            session,
            tenant_id,
            graph_id,
            "INDEX_UPSERTED_ASYNC",
            {
                "job_id": str(job_id),
                "indexed": indexed,
                "failed": failed,
                "missing": missing,
                "raw_id": raw_id,
                "packet_hash": packet_hash,
                "requested_profile": requested_profile,
                "requested_persist_mode": requested_persist_mode,
                "effective_profile": effective_profile,
                "effective_persist_mode": effective_persist_mode,
                "durability_path": durability_path,
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
