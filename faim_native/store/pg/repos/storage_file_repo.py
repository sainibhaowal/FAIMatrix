"""Storage file metadata repository for P1 storage APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from core.contracts.types import uuid7
from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.orm import Session

from store.pg.models_faim import StorageFileModel


class StorageFileRepo:
    """Repository for storage upload/catalog records."""

    def __init__(self, session: Optional[Session] = None, tenant_id: str = "default"):
        self.session = session
        self.tenant_id = tenant_id

    def _resolve_session(self, session: Optional[Session]) -> Session:
        resolved = session or self.session
        if resolved is None:
            raise ValueError("Session is required")
        return resolved

    def get_by_raw_id(
        self,
        session: Session,
        raw_id: UUID,
        graph_id: Optional[str] = None,
    ) -> Optional[StorageFileModel]:
        query = session.query(StorageFileModel).filter(
            and_(
                StorageFileModel.tenant_id == self.tenant_id,
                StorageFileModel.raw_id == raw_id,
            )
        )
        if graph_id is not None:
            query = query.filter(StorageFileModel.graph_id == graph_id)
        return query.first()

    def list_by_raw_id(
        self,
        session: Session,
        raw_id: UUID,
        graph_id: Optional[str] = None,
    ) -> List[StorageFileModel]:
        """List all storage rows for a raw reference.

        Raw refs are tenant-scoped but may be reused across multiple catalog
        rows in migration scenarios, so callers that rewrite blob references
        should update every matching storage row.
        """
        query = session.query(StorageFileModel).filter(
            and_(
                StorageFileModel.tenant_id == self.tenant_id,
                StorageFileModel.raw_id == raw_id,
            )
        )
        if graph_id is not None:
            query = query.filter(StorageFileModel.graph_id == graph_id)
        return (
            query.order_by(asc(StorageFileModel.updated_at), asc(StorageFileModel.id))
            .all()
        )

    def list_by_job_id(
        self,
        session: Session,
        job_id: UUID,
        graph_id: Optional[str] = None,
    ) -> List[StorageFileModel]:
        """List all storage rows associated with a job."""
        query = session.query(StorageFileModel).filter(
            and_(
                StorageFileModel.tenant_id == self.tenant_id,
                StorageFileModel.last_job_id == job_id,
            )
        )
        if graph_id is not None:
            query = query.filter(StorageFileModel.graph_id == graph_id)
        return (
            query.order_by(asc(StorageFileModel.updated_at), asc(StorageFileModel.id))
            .all()
        )

    def upsert_upload(
        self,
        session: Session,
        *,
        graph_id: str,
        raw_id: UUID,
        filename: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        job_id: Optional[UUID] = None,
    ) -> StorageFileModel:
        """Create/update a storage row when raw upload is persisted."""
        existing = self.get_by_raw_id(session, raw_id, graph_id)
        now = datetime.now(timezone.utc)

        if existing is not None:
            existing.filename = filename
            existing.mime_type = mime_type
            existing.size_bytes = size_bytes
            existing.sha256 = sha256
            existing.ingest_status = "uploaded"
            existing.error_message = None
            existing.last_job_id = job_id
            existing.updated_at = now
            session.flush()
            return existing

        row = StorageFileModel(
            id=uuid7(),
            tenant_id=self.tenant_id,
            graph_id=graph_id,
            raw_id=raw_id,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
            ingest_status="uploaded",
            last_job_id=job_id,
            uploaded_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
        return row

    def mark_ingesting(
        self,
        session: Session,
        *,
        raw_id: UUID,
        graph_id: str,
        job_id: Optional[UUID] = None,
    ) -> Optional[StorageFileModel]:
        row = self.get_by_raw_id(session, raw_id, graph_id)
        if row is None:
            return None
        row.ingest_status = "ingesting"
        row.error_message = None
        row.last_job_id = job_id
        row.updated_at = datetime.now(timezone.utc)
        session.flush()
        return row

    def mark_ingest_result(
        self,
        session: Session,
        *,
        raw_id: UUID,
        graph_id: str,
        status: str,
        packet_hash: Optional[str],
        node_count: int,
        vector_count: int,
        error_message: Optional[str],
        job_id: Optional[UUID] = None,
    ) -> Optional[StorageFileModel]:
        row = self.get_by_raw_id(session, raw_id, graph_id)
        if row is None:
            return None

        now = datetime.now(timezone.utc)
        row.packet_hash = packet_hash
        row.node_count = max(0, int(node_count))
        row.vector_count = max(0, int(vector_count))
        row.error_message = error_message
        row.last_job_id = job_id
        row.updated_at = now

        normalized = status.lower()
        if normalized == "completed":
            row.ingest_status = "ingested"
            row.ingested_at = now
        elif normalized == "dedup_hit":
            row.ingest_status = "dedup_hit"
            if row.ingested_at is None:
                row.ingested_at = now
        elif normalized == "error":
            row.ingest_status = "failed"
        else:
            row.ingest_status = normalized

        session.flush()
        return row

    def mark_cancelled(
        self,
        session: Session,
        *,
        raw_id: UUID,
        graph_id: str,
        error_message: Optional[str] = None,
        job_id: Optional[UUID] = None,
    ) -> Optional[StorageFileModel]:
        row = self.get_by_raw_id(session, raw_id, graph_id)
        if row is None:
            return None

        row.ingest_status = "cancelled"
        row.last_job_id = job_id
        row.error_message = (error_message or "Upload cancelled")[:1024]
        row.updated_at = datetime.now(timezone.utc)
        session.flush()
        return row

    def mark_delete_requested(
        self,
        session: Session,
        *,
        raw_id: UUID,
        graph_id: str,
        reason: Optional[str] = None,
    ) -> Optional[StorageFileModel]:
        row = self.get_by_raw_id(session, raw_id, graph_id)
        if row is None:
            return None

        now = datetime.now(timezone.utc)
        row.delete_requested = True
        row.delete_requested_at = now
        row.ingest_status = "delete_requested"
        if reason:
            row.error_message = reason[:1024]
        row.updated_at = now
        session.flush()
        return row

    def mark_delete_executed(
        self,
        session: Session,
        *,
        raw_id: UUID,
        graph_id: str,
        note: Optional[str] = None,
    ) -> Optional[StorageFileModel]:
        row = self.get_by_raw_id(session, raw_id, graph_id)
        if row is None:
            return None

        now = datetime.now(timezone.utc)
        row.delete_requested = True
        if row.delete_requested_at is None:
            row.delete_requested_at = now
        row.ingest_status = "deleted"
        row.error_message = (note or "Physical deletion executed")[:1024]
        row.updated_at = now
        session.flush()
        return row

    def list_delete_requested(
        self,
        session: Session,
        *,
        graph_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[StorageFileModel]:
        q = session.query(StorageFileModel).filter(
            and_(
                StorageFileModel.tenant_id == self.tenant_id,
                StorageFileModel.delete_requested.is_(True),
                StorageFileModel.ingest_status != "deleted",
            )
        )
        if graph_id:
            q = q.filter(StorageFileModel.graph_id == graph_id)
        return (
            q.order_by(
                asc(StorageFileModel.delete_requested_at), asc(StorageFileModel.id)
            )
            .limit(max(1, int(limit)))
            .all()
        )

    def count_active_references(
        self,
        session: Session,
        *,
        raw_id: UUID,
        exclude_graph_id: Optional[str] = None,
    ) -> int:
        q = session.query(StorageFileModel).filter(
            and_(
                StorageFileModel.tenant_id == self.tenant_id,
                StorageFileModel.raw_id == raw_id,
                StorageFileModel.ingest_status != "deleted",
                StorageFileModel.delete_requested.is_(False),
            )
        )
        if exclude_graph_id:
            q = q.filter(StorageFileModel.graph_id != exclude_graph_id)
        return int(q.count())

    def list_files(
        self,
        session: Session,
        *,
        graph_id: Optional[str],
        status: Optional[str],
        query: Optional[str],
        limit: int,
        offset: int,
        include_delete_requested: bool,
    ) -> Tuple[List[StorageFileModel], int]:
        q = session.query(StorageFileModel).filter(
            StorageFileModel.tenant_id == self.tenant_id
        )

        if graph_id:
            q = q.filter(StorageFileModel.graph_id == graph_id)

        if status:
            q = q.filter(StorageFileModel.ingest_status == status)

        if query:
            like = f"%{query}%"
            q = q.filter(
                or_(
                    StorageFileModel.filename.ilike(like),
                    StorageFileModel.sha256.ilike(like),
                )
            )

        if not include_delete_requested:
            q = q.filter(StorageFileModel.delete_requested.is_(False))

        total = q.count()

        rows = (
            q.order_by(desc(StorageFileModel.updated_at), asc(StorageFileModel.id))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return rows, total

    def summary(self, session: Session, *, graph_id: Optional[str]) -> Dict[str, Any]:
        q = session.query(StorageFileModel).filter(
            StorageFileModel.tenant_id == self.tenant_id
        )
        if graph_id:
            q = q.filter(StorageFileModel.graph_id == graph_id)

        total_files = q.count()

        total_bytes = (
            q.with_entities(
                func.coalesce(func.sum(StorageFileModel.size_bytes), 0)
            ).scalar()
            or 0
        )

        status_rows = (
            q.with_entities(
                StorageFileModel.ingest_status, func.count(StorageFileModel.id)
            )
            .group_by(StorageFileModel.ingest_status)
            .all()
        )
        by_status = {s: int(c) for s, c in status_rows}

        type_rows = (
            q.with_entities(StorageFileModel.mime_type, func.count(StorageFileModel.id))
            .group_by(StorageFileModel.mime_type)
            .all()
        )
        by_type = {mime or "application/octet-stream": int(c) for mime, c in type_rows}

        from store.pg.models_faim import NodeModel, EdgeModel, NodeRepresentationV2Model, EventModel

        if total_files == 0:
            graph_memory_bytes = 0
            event_log_bytes = 0
            total_user_footprint_bytes = 0
        else:
            nq = session.query(NodeModel).filter(NodeModel.tenant_id == self.tenant_id)
            eq = session.query(EdgeModel).filter(EdgeModel.tenant_id == self.tenant_id)
            rq = session.query(NodeRepresentationV2Model).filter(NodeRepresentationV2Model.tenant_id == self.tenant_id)
            evq = session.query(EventModel).filter(EventModel.tenant_id == self.tenant_id)

            if graph_id:
                nq = nq.filter(NodeModel.graph_id == graph_id)
                eq = eq.filter(EdgeModel.graph_id == graph_id)
                rq = rq.filter(NodeRepresentationV2Model.graph_id == graph_id)
                evq = evq.filter(EventModel.graph_id == graph_id)

            node_count = nq.count()
            edge_count = eq.count()
            rep_count = rq.count()
            event_count = evq.count()

            raw_bytes = int(total_bytes)
            graph_memory_bytes = (node_count * 2048) + (edge_count * 512) + (rep_count * 1536)
            event_log_bytes = event_count * 768
            total_user_footprint_bytes = raw_bytes + graph_memory_bytes + event_log_bytes

        return {
            "total_files": int(total_files),
            "total_bytes": int(total_bytes),
            "raw_bytes": int(total_bytes),
            "graph_memory_bytes": graph_memory_bytes,
            "event_log_bytes": event_log_bytes,
            "total_user_footprint_bytes": total_user_footprint_bytes,
            "by_status": by_status,
            "by_type": by_type,
        }
