"""Postgres-backed FAIMStore + PayloadStore + EventJournal.

Production implementation using SQLAlchemy ORM and the models defined in
faim.models_sql (NodeStorage, PayloadStorage, EventJournalEntry).

This replaces the SQLite-based sqlite_store.py for production deployments.
All operations are scoped by project_id for multi-tenant isolation.
"""

from __future__ import annotations

import hashlib
import json
import datetime
from typing import Iterator, Optional
from uuid import UUID

import numpy as np
from sqlalchemy.orm import Session

from faim.core.types import (
    GraphId,
    NodeId,
    NodeRecord,
    ParentRef,
    PayloadRef,
    Vector,
)
from faim.storage.journal import EventJournal, JournalEvent
from faim.storage.payload_store import PayloadStore
from faim.storage.store import FAIMStore
from faim.models_sql import NodeStorage, PayloadStorage as PayloadStorageModel, EventJournalEntry


def _serialize_vec(vec: Vector) -> bytes:
    """Serialize numpy vector to bytes for Postgres storage."""
    return vec.astype(np.float32).tobytes()


def _deserialize_vec(blob: bytes) -> Vector:
    """Deserialize bytes back to numpy vector."""
    return np.frombuffer(blob, dtype=np.float32).copy()


class PostgresStore(FAIMStore, PayloadStore, EventJournal):
    """Postgres-backed implementation of FAIM storage with multi-tenant isolation.

    All operations require project_id for tenant isolation.
    """

    def __init__(self, db: Session, project_id: UUID) -> None:
        """Initialize with a database session and project context.

        Args:
            db: SQLAlchemy session
            project_id: The project UUID for tenant isolation
        """
        self._db = db
        self._project_id = project_id

    # ------------------------------------------------------------------ FAIMStore

    def get(self, graph_id: GraphId, node_id: NodeId) -> Optional[NodeRecord]:
        """Retrieve a node by ID, scoped to the current project."""
        row = (
            self._db.query(NodeStorage)
            .filter(
                NodeStorage.node_id == str(node_id),
                NodeStorage.graph_id == str(graph_id),
                NodeStorage.project_id == self._project_id,
            )
            .first()
        )

        if row is None:
            return None

        return self._row_to_record(row)

    def put(self, graph_id: GraphId, record: NodeRecord) -> None:
        """Insert or update a node, scoped to the current project."""
        existing = (
            self._db.query(NodeStorage)
            .filter(
                NodeStorage.node_id == str(record.node_id),
                NodeStorage.project_id == self._project_id,
            )
            .first()
        )

        if existing:
            # Update existing
            existing.graph_id = str(graph_id)
            existing.vec = _serialize_vec(record.vec)
            existing.parents = [
                {"parent_id": str(p.parent_id), "fraction": p.fraction} for p in record.parents
            ]
            existing.children = [str(c) for c in record.children]
            existing.payload_ref = str(record.payload_ref) if record.payload_ref else None
            existing.use_count = record.use_count
            existing.last_used_at = datetime.datetime.utcnow()
        else:
            # Insert new
            new_node = NodeStorage(
                node_id=str(record.node_id),
                graph_id=str(graph_id),
                project_id=self._project_id,
                vec=_serialize_vec(record.vec),
                parents=[
                    {"parent_id": str(p.parent_id), "fraction": p.fraction} for p in record.parents
                ],
                children=[str(c) for c in record.children],
                payload_ref=str(record.payload_ref) if record.payload_ref else None,
                use_count=record.use_count,
                created_at=datetime.datetime.utcnow(),
                last_used_at=datetime.datetime.utcnow(),
            )
            self._db.add(new_node)

        self._db.commit()

    def delete(self, graph_id: GraphId, node_id: NodeId) -> bool:
        """Delete a node, scoped to the current project."""
        result = (
            self._db.query(NodeStorage)
            .filter(
                NodeStorage.node_id == str(node_id),
                NodeStorage.graph_id == str(graph_id),
                NodeStorage.project_id == self._project_id,
            )
            .delete()
        )
        self._db.commit()
        return result > 0

    def iter_graph(self, graph_id: GraphId) -> Iterator[NodeRecord]:
        """Iterate all nodes in a graph, scoped to the current project."""
        rows = (
            self._db.query(NodeStorage)
            .filter(
                NodeStorage.graph_id == str(graph_id),
                NodeStorage.project_id == self._project_id,
            )
            .all()
        )

        for row in rows:
            yield self._row_to_record(row)

    def count(self, graph_id: GraphId) -> int:
        """Count nodes in a graph, scoped to the current project."""
        return (
            self._db.query(NodeStorage)
            .filter(
                NodeStorage.graph_id == str(graph_id),
                NodeStorage.project_id == self._project_id,
            )
            .count()
        )

    # ------------------------------------------------------------------ PayloadStore

    def store_payload(self, graph_id: GraphId, payload: str) -> PayloadRef:
        """Store a payload and return its reference (SHA256 hash)."""
        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        payload_ref = PayloadRef(payload_hash)

        existing = (
            self._db.query(PayloadStorageModel)
            .filter(
                PayloadStorageModel.payload_ref == str(payload_ref),
                PayloadStorageModel.project_id == self._project_id,
            )
            .first()
        )

        if not existing:
            new_payload = PayloadStorageModel(
                payload_ref=str(payload_ref),
                graph_id=str(graph_id),
                project_id=self._project_id,
                content=payload,
                encrypted=False,
                created_at=datetime.datetime.utcnow(),
            )
            self._db.add(new_payload)
            self._db.commit()

        return payload_ref

    def get_payload(self, payload_ref: PayloadRef) -> Optional[str]:
        """Retrieve a payload by reference, scoped to the current project."""
        row = (
            self._db.query(PayloadStorageModel)
            .filter(
                PayloadStorageModel.payload_ref == str(payload_ref),
                PayloadStorageModel.project_id == self._project_id,
            )
            .first()
        )

        if row is None:
            return None
        return row.content

    # ------------------------------------------------------------------ EventJournal

    def append(self, event: JournalEvent) -> None:
        """Append an event to the journal, scoped to the current project."""
        entry = EventJournalEntry(
            ts=datetime.datetime.utcnow(),
            graph_id=str(event.graph_id),
            project_id=self._project_id,
            kind=event.kind,
            node_id=str(event.node_id) if event.node_id else None,
            details=event.details or {},
        )
        self._db.add(entry)
        self._db.commit()

    def iter_events(
        self, graph_id: GraphId, since: Optional[datetime.datetime] = None
    ) -> Iterator[JournalEvent]:
        """Iterate events for a graph, scoped to the current project."""
        query = self._db.query(EventJournalEntry).filter(
            EventJournalEntry.graph_id == str(graph_id),
            EventJournalEntry.project_id == self._project_id,
        )
        if since:
            query = query.filter(EventJournalEntry.ts >= since)
        query = query.order_by(EventJournalEntry.ts)

        for row in query.all():
            yield JournalEvent(
                graph_id=GraphId(row.graph_id),
                kind=row.kind,
                node_id=NodeId(row.node_id) if row.node_id else None,
                details=row.details,
            )

    # ------------------------------------------------------------------ Helpers

    def _row_to_record(self, row: NodeStorage) -> NodeRecord:
        """Convert a database row to a NodeRecord."""
        parents = [
            ParentRef(parent_id=NodeId(p["parent_id"]), fraction=p["fraction"])
            for p in (row.parents or [])
        ]
        children = [NodeId(c) for c in (row.children or [])]

        return NodeRecord(
            node_id=NodeId(row.node_id),
            vec=_deserialize_vec(row.vec),
            parents=parents,
            children=children,
            payload_ref=PayloadRef(row.payload_ref) if row.payload_ref else None,
            use_count=row.use_count,
        )

    def increment_use_count(self, graph_id: GraphId, node_id: NodeId) -> None:
        """Increment the use count for a node (for evolution tracking)."""
        row = (
            self._db.query(NodeStorage)
            .filter(
                NodeStorage.node_id == str(node_id),
                NodeStorage.graph_id == str(graph_id),
                NodeStorage.project_id == self._project_id,
            )
            .first()
        )

        if row:
            row.use_count = (row.use_count or 0) + 1
            row.last_used_at = datetime.datetime.utcnow()
            self._db.commit()
