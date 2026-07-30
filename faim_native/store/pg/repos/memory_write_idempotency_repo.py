"""K5 memory write idempotency repository."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from store.pg.models_faim import MemoryWriteRequestModel


@dataclass(frozen=True)
class BeginResult:
    """Result of begin() classification."""

    state: str  # new | replay | in_progress | failed | conflict_payload
    record: MemoryWriteRequestModel


class MemoryWriteIdempotencyRepo:
    """Repository for `/api/v1/memory/write` idempotency records."""

    def __init__(self, session: Optional[Session] = None, tenant_id: str = "default"):
        self.session = session
        self.tenant_id = tenant_id

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    def _resolve_session(self, session: Optional[Session]) -> Session:
        resolved = session or self.session
        if resolved is None:
            raise ValueError("Session is required")
        return resolved

    def get(
        self,
        session: Session,
        *,
        graph_id: str,
        idempotency_key: str,
    ) -> Optional[MemoryWriteRequestModel]:
        return (
            session.query(MemoryWriteRequestModel)
            .filter(
                and_(
                    MemoryWriteRequestModel.tenant_id == self.tenant_id,
                    MemoryWriteRequestModel.graph_id == graph_id,
                    MemoryWriteRequestModel.idempotency_key == idempotency_key,
                )
            )
            .first()
        )

    def begin(
        self,
        session: Session,
        *,
        graph_id: str,
        idempotency_key: str,
        request_hash: str,
    ) -> BeginResult:
        """Start or classify idempotent request for a key/hash pair."""
        idem_key = str(idempotency_key or "").strip()
        if not idem_key:
            raise ValueError("idempotency_key is required")
        req_hash = str(request_hash or "").strip()
        if not req_hash:
            raise ValueError("request_hash is required")

        existing = self.get(
            session,
            graph_id=graph_id,
            idempotency_key=idem_key,
        )
        if existing is not None:
            return self._classify_existing(existing, req_hash)

        now = self._utcnow()
        record = MemoryWriteRequestModel(
            id=uuid4(),
            tenant_id=self.tenant_id,
            graph_id=graph_id,
            idempotency_key=idem_key,
            request_hash=req_hash,
            status="in_progress",
            created_at=now,
            updated_at=now,
        )

        session.add(record)
        try:
            session.flush()
            return BeginResult(state="new", record=record)
        except IntegrityError:
            session.rollback()
            # Race case: another request inserted first.
            existing = self.get(
                session,
                graph_id=graph_id,
                idempotency_key=idem_key,
            )
            if existing is None:
                raise
            return self._classify_existing(existing, req_hash)

    def _classify_existing(
        self,
        record: MemoryWriteRequestModel,
        request_hash: str,
    ) -> BeginResult:
        if record.request_hash != request_hash:
            return BeginResult(state="conflict_payload", record=record)

        status = str(record.status or "").strip().lower()
        if status == "completed":
            return BeginResult(state="replay", record=record)
        if status == "failed":
            return BeginResult(state="failed", record=record)
        return BeginResult(state="in_progress", record=record)

    def mark_completed(
        self,
        session: Session,
        *,
        record: MemoryWriteRequestModel,
        response_json: dict[str, Any],
        packet_hash: Optional[str],
        raw_id: Optional[UUID],
        node_count: int,
        vector_count: int,
    ) -> MemoryWriteRequestModel:
        now = self._utcnow()
        record.status = "completed"
        record.response_json = response_json
        record.packet_hash = (packet_hash or "").strip() or None
        record.raw_id = raw_id
        record.node_count = max(0, int(node_count))
        record.vector_count = max(0, int(vector_count))
        record.error_message = None
        record.updated_at = now
        record.completed_at = now
        session.flush()
        return record

    def mark_failed(
        self,
        session: Session,
        *,
        record: MemoryWriteRequestModel,
        error_message: Optional[str],
    ) -> MemoryWriteRequestModel:
        record.status = "failed"
        record.error_message = (error_message or "memory write failed")[:1024]
        record.updated_at = self._utcnow()
        session.flush()
        return record
