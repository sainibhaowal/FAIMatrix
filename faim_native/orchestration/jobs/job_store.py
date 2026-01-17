"""FAIM-Native Job Store.

Repository for managing durable background jobs and their event journals.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from store.pg.models_faim import JobEventModel, JobModel

logger = logging.getLogger(__name__)


class JobStore:
    """Repository for persistent jobs and progress tracking."""

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

        if job:
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
            job.status = "failed"
            job.error_message = error
            job.completed_at = datetime.now(timezone.utc)
            job.updated_at = datetime.now(timezone.utc)
            session.commit()
            logger.error(f"Job failed: {job_id} - {error}")

    @staticmethod
    def append_event(
        session: Session,
        job_id: UUID,
        kind: str,
        payload: Dict[str, Any],
    ):
        """Append a progress event for a job."""
        event = JobEventModel(
            job_id=job_id,
            kind=kind,
            payload=payload,
        )
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
