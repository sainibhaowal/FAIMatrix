"""FAIM-Native Job Store.

Repository for managing durable background jobs and their event journals.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session
from store.pg.models_faim import JobEventModel, JobModel

logger = logging.getLogger(__name__)


class JobStore:
    """Repository for persistent jobs and progress tracking."""

    @staticmethod
    def _is_cancel_requested(job: Optional[JobModel]) -> bool:
        if job is None:
            return False
        payload = job.payload_json or {}
        return bool(payload.get("cancel_requested"))

    @staticmethod
    def _cancel_reason(job: Optional[JobModel]) -> Optional[str]:
        if job is None:
            return None
        payload = job.payload_json or {}
        reason = payload.get("cancel_reason")
        if reason is None:
            return None
        return str(reason)

    @staticmethod
    def enqueue(
        session: Session,
        tenant_id: str,
        graph_id: str,
        kind: str,
        payload: Dict[str, Any],
    ) -> UUID:
        """Enqueue a new pending job."""
        job_id = uuid4()
        job = JobModel(
            job_id=job_id,
            tenant_id=tenant_id,
            graph_id=graph_id,
            kind=kind,
            payload_json=payload,
            status="pending",
        )
        session.add(job)
        session.commit()

        logger.info(f"Job enqueued: {job_id} ({kind}) for tenant {tenant_id}")
        return job_id

    @staticmethod
    def claim_next(session: Session, timeout_seconds: int = 300) -> Optional[JobModel]:
        """Claim the next available job (pending or stale running)."""
        # A job is claimable if:
        # 1. status is 'pending'
        # 2. status is 'running' but updated_at is more than timeout_seconds ago
        datetime.now(timezone.utc)
        # SQLAlchemy doesn't handle intervals easily across dialects,
        # so we calculate the threshold in Python for now.
        from datetime import timedelta

        stale_time = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)

        while True:
            job = (
                session.query(JobModel)
                .filter(
                    or_(
                        JobModel.status == "pending",
                        and_(
                            JobModel.status == "running", JobModel.updated_at < stale_time
                        ),
                    )
                )
                .order_by(JobModel.created_at.asc(), JobModel.job_id.asc())
                .with_for_update(skip_locked=True)
                .first()
            )

            if job is None:
                return None

            if JobStore._is_cancel_requested(job):
                # Request acknowledged before claim: finalize as cancelled and continue.
                job.status = "cancelled"
                job.completed_at = datetime.now(timezone.utc)
                job.updated_at = datetime.now(timezone.utc)
                if not job.error_message:
                    reason = JobStore._cancel_reason(job) or "Cancelled before execution"
                    job.error_message = reason[:1024]
                session.commit()
                logger.info("Job cancelled before claim: %s", job.job_id)
                continue

            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            job.updated_at = datetime.now(timezone.utc)
            session.commit()
            logger.info(f"Job claimed: {job.job_id} ({job.kind})")
            return job

        return None

    @staticmethod
    def heartbeat(session: Session, job_id: UUID):
        """Update the updated_at timestamp to prevent job from becoming stale."""
        job = session.query(JobModel).filter_by(job_id=job_id).first()
        if job:
            job.updated_at = datetime.now(timezone.utc)
            session.commit()

    @staticmethod
    def mark_done(session: Session, job_id: UUID):
        """Mark job as successfully completed."""
        job = session.query(JobModel).filter_by(job_id=job_id).first()
        if job:
            if JobStore._is_cancel_requested(job):
                JobStore.mark_cancelled(session, job_id, JobStore._cancel_reason(job))
                return
            job.status = "done"
            job.completed_at = datetime.now(timezone.utc)
            job.updated_at = datetime.now(timezone.utc)
            session.commit()
            logger.info(f"Job done: {job_id}")

    @staticmethod
    def mark_failed(session: Session, job_id: UUID, error: str):
        """Mark job as failed."""
        job = session.query(JobModel).filter_by(job_id=job_id).first()
        if job:
            if JobStore._is_cancel_requested(job):
                JobStore.mark_cancelled(session, job_id, JobStore._cancel_reason(job))
                return
            job.status = "failed"
            job.error_message = error
            job.completed_at = datetime.now(timezone.utc)
            job.updated_at = datetime.now(timezone.utc)
            session.commit()
            logger.error(f"Job failed: {job_id} - {error}")

    @staticmethod
    def request_cancel(
        session: Session,
        job_id: UUID,
        reason: Optional[str] = None,
    ) -> Optional[JobModel]:
        """Request job cancellation (idempotent)."""
        job = session.query(JobModel).filter_by(job_id=job_id).first()
        if job is None:
            return None

        if job.status in {"done", "failed", "cancelled"}:
            return job

        payload = dict(job.payload_json or {})
        payload["cancel_requested"] = True
        payload["cancel_requested_at"] = datetime.now(timezone.utc).isoformat()
        if reason:
            payload["cancel_reason"] = reason[:1024]
        job.payload_json = payload
        job.updated_at = datetime.now(timezone.utc)
        session.commit()
        return job

    @staticmethod
    def is_cancel_requested(session: Session, job_id: UUID) -> bool:
        """Check if cancellation has been requested for the job."""
        job = session.query(JobModel).filter_by(job_id=job_id).first()
        return JobStore._is_cancel_requested(job)

    @staticmethod
    def get_cancel_reason(session: Session, job_id: UUID) -> Optional[str]:
        """Read cancellation reason if present."""
        job = session.query(JobModel).filter_by(job_id=job_id).first()
        return JobStore._cancel_reason(job)

    @staticmethod
    def mark_cancelled(session: Session, job_id: UUID, reason: Optional[str] = None):
        """Mark job as cancelled."""
        job = session.query(JobModel).filter_by(job_id=job_id).first()
        if job is None:
            return

        payload = dict(job.payload_json or {})
        payload["cancel_requested"] = True
        if reason:
            payload["cancel_reason"] = reason[:1024]
        if "cancel_requested_at" not in payload:
            payload["cancel_requested_at"] = datetime.now(timezone.utc).isoformat()
        payload["cancelled_at"] = datetime.now(timezone.utc).isoformat()
        job.payload_json = payload
        job.status = "cancelled"
        job.completed_at = datetime.now(timezone.utc)
        job.updated_at = datetime.now(timezone.utc)
        if reason:
            job.error_message = reason[:1024]
        elif not job.error_message:
            job.error_message = "Cancelled"
        session.commit()
        logger.info("Job cancelled: %s", job_id)

    @staticmethod
    def append_event(
        session: Session,
        job_id: UUID,
        kind: str,
        payload: Dict[str, Any],
    ):
        """Append a progress event for a job."""
        seq: Optional[int] = None
        bind = session.get_bind()
        dialect_name = (getattr(bind, "dialect", None) and bind.dialect.name) or ""

        # SQLite does not auto-increment BigInteger PK columns reliably.
        # Assign seq explicitly there to keep local/dev parity with Postgres paths.
        if dialect_name == "sqlite":
            next_seq = session.query(func.max(JobEventModel.seq)).scalar()
            seq = int(next_seq or 0) + 1

        event_kwargs: Dict[str, Any] = {
            "job_id": job_id,
            "kind": kind,
            "payload": payload,
        }
        if seq is not None:
            event_kwargs["seq"] = seq

        event = JobEventModel(**event_kwargs)
        session.add(event)

        # Also heartbeat the job
        job = session.query(JobModel).filter_by(job_id=job_id).first()
        if job:
            job.updated_at = datetime.now(timezone.utc)

        session.commit()

    @staticmethod
    def get_job(session: Session, job_id: UUID) -> Optional[JobModel]:
        """Get job by ID."""
        return session.query(JobModel).filter_by(job_id=job_id).first()

    @staticmethod
    def get_job_events(session: Session, job_id: UUID) -> List[JobEventModel]:
        """Get all events for a specific job."""
        return (
            session.query(JobEventModel)
            .filter_by(job_id=job_id)
            .order_by(JobEventModel.seq.asc())
            .all()
        )
