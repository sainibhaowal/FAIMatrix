from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import JSON, TypeDecorator

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import (
        EventRecord,
        GraphId,
        GraphVersion,
        RawRef,
        Sha256Hex,
        SnapshotRecord,
    )
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import (
        EventRecord,
        GraphId,
        GraphVersion,
        RawRef,
        Sha256Hex,
        SnapshotRecord,
    )


# Create shared base for all store models
Base = declarative_base()


# -----------------------------------------------------------------------------
# Custom Type for cross-database JSONB compatibility
# -----------------------------------------------------------------------------


class JSONBType(TypeDecorator):
    """Cross-database JSON type (uses JSONB on Postgres, JSON on SQLite)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class UUIDType(TypeDecorator):
    """Cross-database UUID type (native on Postgres, string on SQLite)."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, UUID):
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        return UUID(value)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))


# -----------------------------------------------------------------------------
# RawRefModel - Maps to raw_refs table
# -----------------------------------------------------------------------------


class RawRefModel(Base):
    """ORM model for raw blob references.

    Maps to raw_refs table in schema.sql.
    """

    __tablename__ = "raw_refs"

    id = Column(UUIDType, primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)  # Stage-7.1: Required
    sha256 = Column(String(64), nullable=False)
    uri = Column(Text, nullable=False)
    mime_type = Column(String(128), default="application/octet-stream")
    size_bytes = Column(BigInteger, nullable=False)
    graph_id = Column(String(64), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_domain(self) -> RawRef:
        """Convert to domain object."""
        return RawRef(
            id=self.id if isinstance(self.id, UUID) else UUID(self.id),
            sha256=Sha256Hex(self.sha256),
            uri=self.uri,
            mime_type=self.mime_type or "application/octet-stream",
            size_bytes=self.size_bytes,
            graph_id=GraphId(self.graph_id) if self.graph_id else None,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(cls, raw_ref: RawRef, tenant_id: str = "__test__") -> "RawRefModel":
        """Create from domain object."""
        return cls(
            id=raw_ref.id,
            tenant_id=tenant_id,
            sha256=raw_ref.sha256,
            uri=raw_ref.uri,
            mime_type=raw_ref.mime_type,
            size_bytes=raw_ref.size_bytes,
            graph_id=raw_ref.graph_id,
            created_at=raw_ref.created_at,
        )


# -----------------------------------------------------------------------------
# StorageFileModel - P1 storage catalog table
# -----------------------------------------------------------------------------


class StorageFileModel(Base):
    """ORM model for storage upload/catalog metadata."""

    __tablename__ = "storage_files"

    id = Column(UUIDType, primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    graph_id = Column(String(64), nullable=False, index=True)
    raw_id = Column(UUIDType, nullable=False, index=True)
    filename = Column(Text, nullable=False)
    mime_type = Column(String(128), default="application/octet-stream")
    size_bytes = Column(BigInteger, nullable=False, default=0)
    sha256 = Column(String(64), nullable=False, index=True)
    ingest_status = Column(String(32), nullable=False, default="uploaded")
    packet_hash = Column(String(64), nullable=True)
    node_count = Column(Integer, nullable=False, default=0)
    vector_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    last_job_id = Column(UUIDType, nullable=True, index=True)
    delete_requested = Column(Boolean, nullable=False, default=False)
    delete_requested_at = Column(DateTime(timezone=True), nullable=True)
    uploaded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    ingested_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


# -----------------------------------------------------------------------------
# MemoryWriteRequestModel - K5 memory write idempotency ledger
# -----------------------------------------------------------------------------


class MemoryWriteRequestModel(Base):
    """ORM model for memory write idempotency ledger."""

    __tablename__ = "memory_write_requests"

    id = Column(UUIDType, primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    graph_id = Column(String(64), nullable=False, index=True)
    idempotency_key = Column(Text, nullable=False)
    request_hash = Column(String(64), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="in_progress")
    response_json = Column(JSONBType, nullable=True)
    packet_hash = Column(String(64), nullable=True)
    raw_id = Column(UUIDType, nullable=True)
    node_count = Column(Integer, nullable=False, default=0)
    vector_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API-safe dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "graph_id": self.graph_id,
            "idempotency_key": self.idempotency_key,
            "request_hash": self.request_hash,
            "status": self.status,
            "response_json": self.response_json,
            "packet_hash": self.packet_hash,
            "raw_id": str(self.raw_id) if self.raw_id else None,
            "node_count": self.node_count,
            "vector_count": self.vector_count,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


# -----------------------------------------------------------------------------
# EventModel - Maps to events table
# -----------------------------------------------------------------------------


class EventModel(Base):
    """ORM model for append-only events.

    Maps to events table in schema.sql.
    The seq column is auto-assigned by the database.
    """

    __tablename__ = "events"
    __table_args__ = {"sqlite_autoincrement": True}

    seq = Column(Integer, primary_key=True, autoincrement=True)
    id = Column(UUIDType, nullable=False, unique=True)
    tenant_id = Column(
        String(64), nullable=False, index=True
    )  # Stage-7.1: Required, no default
    ts = Column(DateTime(timezone=True), nullable=False)
    graph_id = Column(String(64), nullable=False, index=True)
    kind = Column(String(64), nullable=False, index=True)
    payload = Column(JSONBType, nullable=False, default=dict)
    checksum = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_domain(self) -> EventRecord:
        """Convert to domain object."""
        return EventRecord(
            id=self.id if isinstance(self.id, UUID) else UUID(self.id),
            seq=self.seq,
            ts=self.ts,
            graph_id=GraphId(self.graph_id),
            kind=self.kind,
            payload=self.payload or {},
            checksum=self.checksum,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(
        cls, event: EventRecord, tenant_id: str = "__test__"
    ) -> "EventModel":
        """Create from domain object.

        Note: seq is not set here; it's auto-assigned by the database.

        Args:
            event: EventRecord domain object.
            tenant_id: Tenant identifier (required in production, defaults to __test__ for tests).
        """
        return cls(
            id=event.id,
            tenant_id=tenant_id,
            ts=event.ts,
            graph_id=event.graph_id,
            kind=event.kind,
            payload=event.payload,
            checksum=event.checksum,
            created_at=event.created_at,
        )


# -----------------------------------------------------------------------------
# SnapshotModel - Maps to snapshots table
# -----------------------------------------------------------------------------


class SnapshotModel(Base):
    """ORM model for graph snapshots.

    Maps to snapshots table in schema.sql.
    """

    __tablename__ = "snapshots"

    id = Column(UUIDType, primary_key=True)
    tenant_id = Column(
        String(64), nullable=False, index=True
    )  # Stage-7.1: Required, no default
    graph_id = Column(String(64), nullable=False, index=True)
    graph_version = Column(BigInteger, nullable=False)
    graph_hash = Column(String(64), nullable=False)
    node_count = Column(Integer, nullable=False, default=0)
    extra_meta = Column(JSONBType, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_domain(self) -> SnapshotRecord:
        """Convert to domain object."""
        return SnapshotRecord(
            id=self.id if isinstance(self.id, UUID) else UUID(self.id),
            graph_id=GraphId(self.graph_id),
            graph_version=self.graph_version,
            graph_hash=self.graph_hash,
            node_count=self.node_count,
            created_at=self.created_at,
            metadata=self.extra_meta,
        )

    @classmethod
    def from_domain(
        cls, snapshot: SnapshotRecord, tenant_id: str = "__test__"
    ) -> "SnapshotModel":
        """Create from domain object."""
        return cls(
            id=snapshot.id,
            tenant_id=tenant_id,
            graph_id=snapshot.graph_id,
            graph_version=snapshot.graph_version,
            graph_hash=snapshot.graph_hash,
            node_count=snapshot.node_count,
            extra_meta=snapshot.metadata,
            created_at=snapshot.created_at,
        )


# -----------------------------------------------------------------------------
# GraphVersionModel - Maps to graph_version table
# -----------------------------------------------------------------------------


class GraphVersionModel(Base):
    """ORM model for graph version tracking.

    Maps to graph_version table in schema.sql.
    """

    __tablename__ = "graph_version"

    tenant_id = Column(
        String(64), nullable=False, index=True
    )  # Stage-7.1: Required, no default
    graph_id = Column(String(64), primary_key=True)
    version = Column(BigInteger, nullable=False, default=0)
    reason = Column(Text, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_domain(self) -> GraphVersion:
        """Convert to domain object."""
        return GraphVersion(
            graph_id=GraphId(self.graph_id),
            version=self.version,
            reason=self.reason,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, gv: GraphVersion) -> "GraphVersionModel":
        """Create from domain object."""
        return cls(
            graph_id=gv.graph_id,
            version=gv.version,
            reason=gv.reason,
            updated_at=gv.updated_at,
        )


# -----------------------------------------------------------------------------
# NodeModel - Maps to nodes table
# -----------------------------------------------------------------------------


class NodeModel(Base):
    """ORM model for FIG graph nodes.

    Maps to nodes table in schema.sql.
    """

    __tablename__ = "nodes"

    node_id = Column(UUIDType, primary_key=True)
    tenant_id = Column(
        String(64), nullable=False, index=True
    )  # Stage-7.1: Required, no default
    graph_id = Column(String(64), nullable=False, index=True)
    kind = Column(String(16), nullable=False, default="atom")
    vector_hash = Column(String(64), nullable=False)
    raw_id = Column(Text, nullable=True)
    block_id = Column(Text, nullable=True)
    anchor_json = Column(JSONBType, nullable=True)
    v_native = Column(JSONBType, nullable=False)
    opp_signature = Column(JSONBType, nullable=True)
    residual = Column(BigInteger, nullable=False, default=0)  # Stored as int * 1e9
    level = Column(Integer, nullable=False, default=0)
    touch_count = Column(Integer, nullable=False, default=0)
    last_access = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": str(self.node_id),
            "graph_id": self.graph_id,
            "kind": self.kind,
            "vector_hash": self.vector_hash,
            "raw_id": self.raw_id,
            "block_id": self.block_id,
            "anchor_json": self.anchor_json,
            "v_native": self.v_native,
            "opp_signature": self.opp_signature,
            "residual": self.residual / 1e9 if self.residual else 0.0,
            "level": self.level,
            "touch_count": self.touch_count,
            "last_access": self.last_access.isoformat() if self.last_access else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# -----------------------------------------------------------------------------
# EdgeModel - Maps to edges table
# -----------------------------------------------------------------------------


class EdgeModel(Base):
    """ORM model for FIG graph edges.

    Maps to edges table in schema.sql.
    """

    __tablename__ = "edges"

    edge_id = Column(UUIDType, primary_key=True)
    tenant_id = Column(
        String(64), nullable=False, index=True
    )  # Stage-7.1: Required, no default
    graph_id = Column(String(64), nullable=False, index=True)
    src_node_id = Column(UUIDType, nullable=False)
    dst_node_id = Column(UUIDType, nullable=False)
    kind = Column(String(32), nullable=False)
    weight = Column(BigInteger, nullable=False, default=0)  # Stored as int * 1e9
    meta = Column(JSONBType, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "edge_id": str(self.edge_id),
            "graph_id": self.graph_id,
            "src_node_id": str(self.src_node_id),
            "dst_node_id": str(self.dst_node_id),
            "kind": self.kind,
            "weight": self.weight / 1e9 if self.weight else 0.0,
            "meta": self.meta,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# -----------------------------------------------------------------------------
# Stage-9: Ingest Dedup Model
# -----------------------------------------------------------------------------


class IngestDedupModel(Base):
    """Ingest idempotency tracking (Stage-9).

    Prevents duplicate processing on retry.
    Key: (tenant_id, graph_id, packet_hash)
    """

    __tablename__ = "ingest_dedup"

    tenant_id = Column(String(64), primary_key=True)
    graph_id = Column(String(64), primary_key=True)
    packet_hash = Column(String(64), primary_key=True)
    raw_id = Column(PG_UUID(as_uuid=True), nullable=True)
    node_count = Column(Integer, default=0)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    @classmethod
    def check_exists(cls, session, tenant_id: str, graph_id: str, packet_hash: str):
        """Check if this packet was already processed."""
        return (
            session.query(cls)
            .filter_by(
                tenant_id=tenant_id,
                graph_id=graph_id,
                packet_hash=packet_hash,
            )
            .first()
        )

    @classmethod
    def record_ingest(
        cls,
        session,
        tenant_id: str,
        graph_id: str,
        packet_hash: str,
        raw_id,
        node_count: int,
    ):
        """Record a successful ingest for future dedup."""
        record = cls(
            tenant_id=tenant_id,
            graph_id=graph_id,
            packet_hash=packet_hash,
            raw_id=raw_id,
            node_count=node_count,
        )
        session.add(record)
        session.commit()
        return record


# -----------------------------------------------------------------------------
# Stage-10: Durable Job Models
# -----------------------------------------------------------------------------


class JobModel(Base):
    """ORM model for durable background jobs (Stage-10).

    Maps to jobs table.
    """

    __tablename__ = "jobs"

    job_id = Column(UUIDType, primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    graph_id = Column(String(64), nullable=False, index=True)
    kind = Column(String(64), nullable=False)  # 'evolve', 'backup', 'cleanup'
    payload_json = Column(JSONBType, nullable=False, default=dict)
    status = Column(
        String(32), nullable=False, default="pending"
    )  # 'pending', 'running', 'done', 'failed'
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class JobEventModel(Base):
    """ORM model for per-job progress tracking (Stage-10).

    Maps to job_events table.
    """

    __tablename__ = "job_events"

    seq = Column(BigInteger, primary_key=True, autoincrement=True)
    job_id = Column(UUIDType, nullable=False, index=True)
    ts = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    kind = Column(String(64), nullable=False)  # 'step_start', 'step_progress', 'log'
    payload = Column(JSONBType, nullable=False, default=dict)


# -----------------------------------------------------------------------------
# Stage-J: Self-Invention Runtime State
# -----------------------------------------------------------------------------


class SelfInventionStateModel(Base):
    """Runtime state for self-invention coactivation tracking.

    Stores cursor and bounded signature counts per tenant+graph so evolve
    can process events incrementally instead of rescanning full history.
    """

    __tablename__ = "self_invention_state"

    tenant_id = Column(String(64), primary_key=True)
    graph_id = Column(String(64), primary_key=True)
    last_event_seq = Column(BigInteger, nullable=False, default=0)
    signature_counts = Column(JSONBType, nullable=False, default=dict)
    last_cycle_macros = Column(Integer, nullable=False, default=0)
    last_cycle_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


# -----------------------------------------------------------------------------
# Phase-S2: Self-Evolution Scheduler State
# -----------------------------------------------------------------------------


class SelfEvolutionStateModel(Base):
    """Durable scheduler state for self-evolution coordination."""

    __tablename__ = "self_evolution_state"

    tenant_id = Column(String(64), primary_key=True)
    graph_id = Column(String(64), primary_key=True)
    last_seen_version = Column(BigInteger, nullable=False, default=0)
    last_evolved_version = Column(BigInteger, nullable=False, default=0)
    last_evolved_at = Column(DateTime(timezone=True), nullable=True)
    last_enqueued_job_id = Column(UUIDType, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


# -----------------------------------------------------------------------------
# Table creation helper
# -----------------------------------------------------------------------------


def create_all_tables(engine) -> None:
    """Create all store tables.

    Args:
        engine: SQLAlchemy engine.
    """
    # Ensure optional models are imported into Base metadata.
    from store.pg import models_crypto as _models_crypto  # noqa: F401

    Base.metadata.create_all(bind=engine)


def drop_all_tables(engine) -> None:
    """Drop all store tables (use with caution!).

    Args:
        engine: SQLAlchemy engine.
    """
    Base.metadata.drop_all(bind=engine)
