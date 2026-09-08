"""FAIM-Native Background Worker.

Polls for durable jobs and executes them.
Supports 'evolve' and potentially 'backup/restore' jobs.
"""

from __future__ import annotations

import logging
import signal
import time
from datetime import datetime, timezone
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
        self.executable_job_kinds = (
            "evolve",
            "storage_upload",
            "domain_autonomy",
            "crypto_rotation",
            "ingest_secondary_index",
            "storage_retention",
            "raw_reencryption",
        )
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
            job = JobStore.claim_next_of_kinds(
                session=session,
                executable_kinds=list(self.executable_job_kinds),
            )
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
                elif kind == "raw_reencryption":
                    self._run_raw_reencryption_job(
                        session, tenant_id, graph_id, payload, job_id
                    )
                elif kind == "storage_upload":
                    self._run_storage_upload_job(
                        session, tenant_id, graph_id, payload, job_id
                    )
                elif kind == "domain_autonomy":
                    self._run_domain_autonomy_job(
                        session, tenant_id, graph_id, payload, job_id
                    )
                elif kind == "crypto_rotation":
                    self._run_crypto_rotation_job(
                        session, tenant_id, graph_id, payload, job_id
                    )
                else:
                    raise ValueError(f"Unknown job kind: {kind}")

                # Success
                if JobStore.is_cancel_requested(session, job_id):
                    JobStore.mark_cancelled(
                        session,
                        job_id,
                        JobStore.get_cancel_reason(session, job_id),
                    )
                    self._emit_journal_event(
                        session,
                        tenant_id,
                        graph_id,
                        "JOB_CANCELLED",
                        {
                            "job_id": str(job_id),
                        },
                    )
                else:
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

        if result.advanced_warnings:
            JobStore.append_event(
                session,
                job_id,
                "step_progress",
                {
                    "message": "Evolution completed with degraded advanced components",
                    "status": "completed_with_warnings",
                    "warnings": result.advanced_warnings,
                },
            )

        JobStore.append_event(
            session,
            job_id,
            "step_progress",
            {
                "message": "Evolution cycle complete",
                "merges": result.merges,
                "prunes": result.prunes,
                "version": result.graph_version,
                "requested_profile": result.requested_profile,
                "requested_persist_mode": result.requested_persist_mode,
                "effective_profile": result.effective_profile,
                "effective_persist_mode": result.effective_persist_mode,
                "durability_path": result.durability_path,
                "evolve_aggressiveness": result.evolve_aggressiveness,
                "completion_mode": result.completion_mode,
                "state_update_status": result.state_update_status,
                "state_update_error": result.state_update_error,
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

    def _run_raw_reencryption_job(self, session, tenant_id, graph_id, payload, job_id):
        """Execute legacy raw-blob re-encryption job."""
        from datetime import datetime

        from orchestration.jobs.raw_reencryption import run_raw_reencryption_backfill
        from runtime.context import _get_raw_store
        from store.pg.repos.event_repo import EventRepo
        from store.pg.repos.raw_repo import RawRepo
        from store.pg.repos.storage_file_repo import StorageFileRepo

        JobStore.append_event(
            session,
            job_id,
            "step_progress",
            {"message": "Running legacy raw re-encryption"},
        )

        cutoff_raw = payload.get("cutoff_created_at")
        if not cutoff_raw:
            raise ValueError("cutoff_created_at is required for raw re-encryption jobs")

        cutoff_created_at = datetime.fromisoformat(
            str(cutoff_raw).replace("Z", "+00:00")
        )

        result = run_raw_reencryption_backfill(
            session=session,
            tenant_id=tenant_id,
            graph_id=payload.get("graph_id") or graph_id,
            cutoff_created_at=cutoff_created_at,
            raw_repo=RawRepo(tenant_id=tenant_id),
            storage_file_repo=StorageFileRepo(tenant_id=tenant_id),
            raw_store=_get_raw_store(tenant_id),
            event_repo=EventRepo(tenant_id=tenant_id),
            page_size=max(1, int(payload.get("limit", 100))),
            dry_run=bool(payload.get("dry_run", True)),
            irreversible=bool(payload.get("irreversible", False)),
            reason=payload.get("reason"),
        )

        JobStore.append_event(
            session,
            job_id,
            "step_progress",
            {
                "message": "Legacy raw re-encryption complete",
                "cutoff_created_at": result.cutoff_created_at.isoformat(),
                "dry_run": result.dry_run,
                "already_encrypted": result.already_encrypted,
                "reencrypted": result.reencrypted,
                "failed": result.failed,
            },
        )

    def _run_crypto_rotation_job(self, session, tenant_id, graph_id, payload, job_id):
        """Execute tenant master-key rewrap job."""
        from orchestration.jobs.crypto_rotation import (
            run_tenant_crypto_rotation_backfill,
        )

        tenant_rotation_id = str(
            payload.get("tenant_id") or graph_id or tenant_id or ""
        ).strip()
        dry_run = bool(payload.get("dry_run", True))
        reason = payload.get("reason")

        JobStore.append_event(
            session,
            job_id,
            "step_progress",
            {
                "message": "Running tenant crypto rotation",
                "tenant_id": tenant_rotation_id,
                "dry_run": dry_run,
            },
        )

        result = run_tenant_crypto_rotation_backfill(
            session=session,
            tenant_id=tenant_rotation_id or None,
            dry_run=dry_run,
            reason=reason,
        )

        JobStore.append_event(
            session,
            job_id,
            "step_progress",
            {
                "message": "Tenant crypto rotation complete",
                "tenant_id": tenant_rotation_id,
                "dry_run": result.dry_run,
                "scanned": result.scanned,
                "already_current": result.already_current,
                "rewrapped": result.rewrapped,
                "created": result.created,
                "failed": result.failed,
            },
        )

    def _run_domain_autonomy_job(self, session, tenant_id, graph_id, payload, job_id):
        """Execute autonomous graph-local domain adaptation."""
        from orchestration.domain_autonomy import run_domain_autonomy_now
        from runtime.context import _get_raw_store
        from store.pg.repos.event_repo import EventRepo
        from store.pg.repos.graph_version_repo import GraphVersionRepo
        from store.pg.repos.node_repo import NodeRepo
        from store.pg.repos.raw_repo import RawRepo
        from store.pg.repos.storage_file_repo import StorageFileRepo

        source = str(payload.get("source") or "unknown")
        JobStore.append_event(
            session,
            job_id,
            "step_progress",
            {
                "message": "Running autonomous domain adaptation",
                "source": source,
            },
        )

        result = run_domain_autonomy_now(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            raw_repo=RawRepo(tenant_id=tenant_id),
            storage_file_repo=StorageFileRepo(session=session, tenant_id=tenant_id),
            raw_store=_get_raw_store(tenant_id),
            node_repo=NodeRepo(session=session, tenant_id=tenant_id),
            gv_repo=GraphVersionRepo(session=session, tenant_id=tenant_id),
            event_repo=EventRepo(tenant_id=tenant_id),
        )

        JobStore.append_event(
            session,
            job_id,
            "step_progress",
            {
                "message": "Autonomous domain adaptation complete",
                "source": source,
                "files_scanned": result.files_scanned,
                "matched_nodes": result.matched_nodes,
                "lexicon_written": result.lexicon_written,
                "sources_written": result.sources_written,
                "fact_nodes_written": result.fact_nodes_written,
                "edges_written": result.edges_written,
                "detected_packs": result.detected_packs,
                "graph_version": result.graph_version,
                "errors": result.errors[:25],
            },
        )

        if result.errors:
            raise RuntimeError(
                f"Domain adaptation completed with {len(result.errors)} error(s)"
            )

    def _run_storage_upload_job(self, session, tenant_id, graph_id, payload, job_id):
        """Execute durable upload ingest work after the HTTP request returns."""
        from datetime import datetime
        from uuid import UUID

        from orchestration.ingest_flow import FAIMProfile, PersistMode, run_ingest
        from runtime.context import _get_raw_store
        from store.pg.repos.edge_repo import EdgeRepo
        from store.pg.repos.event_repo import EventRepo
        from store.pg.repos.graph_version_repo import GraphVersionRepo
        from store.pg.repos.node_repo import NodeRepo
        from store.pg.repos.raw_repo import RawRepo
        from store.pg.repos.storage_file_repo import StorageFileRepo

        requested_profile = str(
            payload.get("requested_profile") or payload.get("profile") or "strict"
        )
        requested_persist_mode = str(
            payload.get("requested_persist_mode")
            or payload.get("persist_mode")
            or "relaxed"
        )
        requested_extractor_mode = str(
            payload.get("requested_extractor_mode")
            or payload.get("extractor_mode")
            or "auto"
        )
        effective_profile = str(payload.get("effective_profile") or requested_profile)
        effective_persist_mode = str(
            payload.get("effective_persist_mode") or requested_persist_mode
        )
        effective_extractor_mode = str(
            payload.get("effective_extractor_mode") or requested_extractor_mode
        )
        durability_path = str(payload.get("durability_path") or "")

        files = payload.get("files") or []
        if not isinstance(files, list):
            raise ValueError("files payload must be a list")

        profile_enum = FAIMProfile(requested_profile.lower())
        persist_mode_enum = PersistMode(requested_persist_mode.lower())

        raw_repo = RawRepo(tenant_id=tenant_id)
        node_repo = NodeRepo(session=session, tenant_id=tenant_id)
        edge_repo = EdgeRepo(session=session, tenant_id=tenant_id)
        gv_repo = GraphVersionRepo(session=session, tenant_id=tenant_id)
        storage_repo = StorageFileRepo(session=session, tenant_id=tenant_id)
        event_repo = EventRepo(tenant_id=tenant_id)
        raw_store = _get_raw_store(tenant_id)

        JobStore.append_event(
            session,
            job_id,
            "step_progress",
            {
                "message": "Running storage upload ingest",
                "requested_profile": requested_profile,
                "requested_persist_mode": requested_persist_mode,
                "effective_profile": effective_profile,
                "effective_persist_mode": effective_persist_mode,
                "effective_extractor_mode": effective_extractor_mode,
                "durability_path": durability_path,
            },
        )

        processed = 0
        success = 0
        failed = 0
        dedup_hits = 0
        cancelled = 0

        for index, file_item in enumerate(files):
            if JobStore.is_cancel_requested(session, job_id):
                cancelled += self._cancel_remaining_storage_upload_files(
                    session=session,
                    graph_id=graph_id,
                    job_id=job_id,
                    files=files[index:],
                    storage_repo=storage_repo,
                )
                JobStore.append_event(
                    session,
                    job_id,
                    "step_progress",
                    {
                        "message": "Storage upload cancelled before worker ingest",
                        "cancelled_files": cancelled,
                    },
                )
                break

            try:
                raw_uuid = UUID(str(file_item.get("raw_id") or ""))
            except (ValueError, TypeError, AttributeError):
                failed += 1
                JobStore.append_event(
                    session,
                    job_id,
                    "step_progress",
                    {
                        "index": index,
                        "status": "failed",
                        "message": "Invalid raw_id in queued upload payload",
                    },
                )
                continue

            raw_ref = raw_repo.get_by_id(session, raw_uuid)
            if raw_ref is None:
                failed += 1
                JobStore.append_event(
                    session,
                    job_id,
                    "step_progress",
                    {
                        "index": index,
                        "raw_id": str(raw_uuid),
                        "status": "failed",
                        "message": "Queued raw ref not found",
                    },
                )
                continue

            filename = str(file_item.get("filename") or raw_uuid)
            mime_type = str(file_item.get("mime_type") or "application/octet-stream")

            storage_repo.mark_ingesting(
                session,
                raw_id=raw_uuid,
                graph_id=graph_id,
                job_id=job_id,
            )
            JobStore.append_event(
                session,
                job_id,
                "step_progress",
                {
                    "index": index,
                    "filename": filename,
                    "raw_id": str(raw_uuid),
                    "message": "Ingest started",
                    "requested_extractor_mode": requested_extractor_mode,
                    "effective_profile": effective_profile,
                    "effective_persist_mode": effective_persist_mode,
                    "effective_extractor_mode": effective_extractor_mode,
                    "durability_path": durability_path,
                },
            )

            try:
                file_bytes = raw_store.load(raw_ref, verify=True)
                result = run_ingest(
                    graph_id=graph_id,
                    raw_id=str(raw_uuid),
                    filename=filename,
                    file_bytes=file_bytes,
                    profile=profile_enum,
                    persist_mode=persist_mode_enum,
                    extraction_settings={
                        "extractor_mode": requested_extractor_mode
                    },
                    tenant_id=tenant_id,
                    session=session,
                    node_repo=node_repo,
                    edge_repo=edge_repo,
                    event_repo=event_repo,
                    gv_repo=gv_repo,
                )
            except Exception as exc:
                failed += 1
                storage_repo.mark_ingest_result(
                    session,
                    raw_id=raw_uuid,
                    graph_id=graph_id,
                    status="error",
                    packet_hash=None,
                    node_count=0,
                    vector_count=0,
                    error_message=str(exc),
                    job_id=job_id,
                )
                JobStore.append_event(
                    session,
                    job_id,
                    "step_progress",
                    {
                        "index": index,
                        "filename": filename,
                        "raw_id": str(raw_uuid),
                        "status": "failed",
                        "error": str(exc),
                    },
                )
                continue

            storage_repo.mark_ingest_result(
                session,
                raw_id=raw_uuid,
                graph_id=graph_id,
                status=result.status,
                packet_hash=result.packet_hash or None,
                node_count=result.nodes_written,
                vector_count=result.vector_count,
                error_message=result.error,
                job_id=job_id,
            )
            processed += 1
            if result.status == "dedup_hit":
                dedup_hits += 1
                success += 1
            elif result.status == "error":
                failed += 1
            else:
                success += 1

            JobStore.append_event(
                session,
                job_id,
                "step_progress",
                {
                    "index": index,
                    "filename": filename,
                    "raw_id": str(raw_uuid),
                    "status": result.status,
                    "packet_hash": result.packet_hash,
                    "nodes_written": result.nodes_written,
                    "vector_count": result.vector_count,
                    "requested_profile": result.requested_profile,
                    "requested_persist_mode": result.requested_persist_mode,
                    "effective_profile": result.effective_profile,
                    "effective_persist_mode": result.effective_persist_mode,
                    "effective_extractor_mode": result.effective_extractor_mode,
                    "durability_path": result.durability_path,
                },
            )

            if JobStore.is_cancel_requested(session, job_id):
                cancelled += self._cancel_remaining_storage_upload_files(
                    session=session,
                    graph_id=graph_id,
                    job_id=job_id,
                    files=files[index + 1 :],
                    storage_repo=storage_repo,
                )
                JobStore.append_event(
                    session,
                    job_id,
                    "step_progress",
                    {
                        "message": "Storage upload cancelled after worker ingest",
                        "cancelled_files": cancelled,
                    },
                )
                break

        job = JobStore.get_job(session, job_id)
        if job is not None:
            payload_json = dict(job.payload_json or {})
            payload_json.update(
                {
                    "processed_files": processed,
                    "success_files": success,
                    "failed_files": failed,
                    "dedup_hits": dedup_hits,
                    "cancelled_files": cancelled,
                }
            )
            job.payload_json = payload_json
            job.updated_at = datetime.now(timezone.utc)
            session.flush()

        JobStore.append_event(
            session,
            job_id,
            "step_progress",
            {
                "message": "Storage upload ingest complete",
                "processed": processed,
                "success": success,
                "failed": failed,
                "dedup_hits": dedup_hits,
                "cancelled_files": cancelled,
            },
        )

        if success > 0:
            try:
                from orchestration.domain_autonomy import (
                    enqueue_domain_autonomy_if_needed,
                )

                domain_result = enqueue_domain_autonomy_if_needed(
                    session=session,
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    source="storage_upload_worker",
                    request_id=str(job_id),
                )
                if domain_result.job_id is not None:
                    JobStore.append_event(
                        session,
                        job_id,
                        "step_progress",
                        {
                            "message": "Autonomous domain adaptation triggered",
                            "domain_autonomy_job_id": str(domain_result.job_id),
                            "domain_autonomy_status": domain_result.status,
                        },
                    )
            except Exception as exc:  # nosec B110
                logger.warning(
                    "Failed to enqueue autonomous domain adaptation after upload job %s: %s",
                    job_id,
                    exc,
                )

    def _cancel_remaining_storage_upload_files(
        self,
        *,
        session,
        graph_id,
        job_id,
        files,
        storage_repo,
    ) -> int:
        """Mark queued upload rows as cancelled."""
        from uuid import UUID

        cancelled = 0
        for file_item in files:
            try:
                raw_uuid = UUID(str(file_item.get("raw_id") or ""))
            except (ValueError, TypeError, AttributeError):
                continue
            row = storage_repo.get_by_raw_id(session, raw_uuid, graph_id)
            if row is None:
                continue
            if row.ingest_status in {"ingested", "dedup_hit", "failed", "cancelled"}:
                continue
            storage_repo.mark_cancelled(
                session,
                raw_id=raw_uuid,
                graph_id=graph_id,
                error_message="Upload cancelled before worker ingest",
                job_id=job_id,
            )
            cancelled += 1
        return cancelled

    def _run_ingest_secondary_index_job(
        self,
        session,
        tenant_id,
        graph_id,
        payload,
        job_id,
    ):
        """Execute async secondary index upsert for relaxed ingest durability."""
        from index.qdrant_index import FAIMIndex
        from sqlalchemy import and_
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
