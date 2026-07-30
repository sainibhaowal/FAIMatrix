"""Postgres-backed FAIMStore + PayloadStore + EventJournal.

Production implementation using SQLAlchemy ORM and the models defined in
faim.models_sql (NodeStorage, PayloadStorage, EventJournalEntry).

This replaces the SQLite-based sqlite_store.py for production deployments.
Operations are scoped by graph_id (which is user-isolated).
"""

from __future__ import annotations

import datetime
import hashlib
from typing import Iterator, Optional
from uuid import UUID

import numpy as np
from faim.config.models import EventJournalEntry, NodeStorage
from faim.config.models import PayloadStorage as PayloadStorageModel
from faim.core.types import GraphId, NodeId, NodeRecord, ParentRef, PayloadRef, Vector
from faim.data.storage.cipher import build_cipher_from_env
from faim.data.storage.journal import EventJournal, JournalEvent
from faim.data.storage.payload_store import PayloadStore
from faim.data.storage.store import FAIMStore
from sqlalchemy.orm import Session


def _serialize_vec(vec: Vector) -> bytes:
    """Serialize numpy vector to bytes for Postgres storage."""
    return vec.astype(np.float32).tobytes()


def _deserialize_vec(blob: bytes) -> Vector:
    """Deserialize bytes back to numpy vector."""
    return np.frombuffer(blob, dtype=np.float32).copy()


class PostgresStore(FAIMStore, PayloadStore, EventJournal):
    """Postgres-backed implementation of FAIM storage.

    Operations are scoped by graph_id.
    """

    def __init__(
        self,
        db: Optional[Session] = None,
        project_id: Optional[UUID] = None,  # Kept for signature compatibility, ignored
    ) -> None:
        """Initialize with a database session.

        Args:
            db: SQLAlchemy session. If None, creates one from the default engine.
            project_id: Ignored (deprecated).
        """
        if db is None:
            # Auto-create session from the default engine
            from faim.config.database import SessionLocal

            db = SessionLocal()

        self._db = db
        # Initialize cipher strategy (Noop or Fernet based on env)
        self._cipher = build_cipher_from_env()
        self._user_cache = {}  # graph_id -> user_id

    def _get_user_id(self, graph_id: str) -> Optional[UUID]:
        """Resolve user_id for a graph."""
        if graph_id in self._user_cache:
            return self._user_cache[graph_id]

        from faim.config.models import GraphOwnership

        # No graph_id context, need to look up owner
        graph = (
            self._db.query(GraphOwnership)
            .filter(GraphOwnership.graph_id == graph_id)
            .first()
        )
        if graph:
            self._user_cache[graph_id] = graph.user_id
            return graph.user_id
        return None

    # ------------------------------------------------------------------ FAIMStore

    def get(self, graph_id: GraphId, node_id: NodeId) -> Optional[NodeRecord]:
        """Retrieve a node by ID, scoped to graph."""
        row = (
            self._db.query(NodeStorage)
            .filter(
                NodeStorage.node_id == str(node_id),
                NodeStorage.graph_id == str(graph_id),
            )
            .first()
        )

        if row is None:
            return None

        return self._row_to_record(row)

    def put(self, graph_id: GraphId, record: NodeRecord) -> None:
        """Insert or update a node."""
        existing = (
            self._db.query(NodeStorage)
            .filter(
                NodeStorage.node_id == str(record.id),
                NodeStorage.graph_id == str(graph_id),
            )
            .first()
        )

        try:
            if existing:
                # Update existing
                existing.vec = _serialize_vec(record.vec)
                existing.parents = [
                    {"parent_id": str(p.parent_id), "fraction": p.fraction}
                    for p in record.parents
                ]
                existing.children = [str(c) for c in record.children]
                existing.payload_ref = (
                    str(record.payload_ref) if record.payload_ref else None
                )
                existing.use_count = record.use_count
                existing.last_used_at = datetime.datetime.utcnow()
            else:
                # Insert new
                new_node = NodeStorage(
                    node_id=str(record.id),
                    graph_id=str(graph_id),
                    user_id=self._get_user_id(str(graph_id)),
                    vec=_serialize_vec(record.vec),
                    parents=[
                        {"parent_id": str(p.parent_id), "fraction": p.fraction}
                        for p in record.parents
                    ],
                    children=[str(c) for c in record.children],
                    payload_ref=str(record.payload_ref) if record.payload_ref else None,
                    use_count=record.use_count,
                    created_at=datetime.datetime.utcnow(),
                    last_used_at=datetime.datetime.utcnow(),
                )
                self._db.add(new_node)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    def delete(self, graph_id: GraphId, node_id: NodeId) -> bool:
        """Delete a node."""
        try:
            result = (
                self._db.query(NodeStorage)
                .filter(
                    NodeStorage.node_id == str(node_id),
                    NodeStorage.graph_id == str(graph_id),
                )
                .delete()
            )
            self._db.commit()
            return result > 0
        except Exception:
            self._db.rollback()
            raise

    def iter_graph(self, graph_id: GraphId) -> Iterator[NodeRecord]:
        """Iterate all nodes in a graph."""
        rows = (
            self._db.query(NodeStorage)
            .filter(
                NodeStorage.graph_id == str(graph_id),
            )
            .all()
        )

        for row in rows:
            yield self._row_to_record(row)

    def count(self, graph_id: GraphId) -> int:
        """Count nodes in a graph."""
        return (
            self._db.query(NodeStorage)
            .filter(
                NodeStorage.graph_id == str(graph_id),
            )
            .count()
        )

    # ------------------------------------------------------------------ PayloadStore

    def store_payload(self, graph_id: GraphId, payload: str) -> PayloadRef:
        """Store a payload and return its reference (SHA256 hash)."""
        import base64
        import zlib

        # Calculate consistency hash from the RAW payload (stable reference)
        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        payload_ref = PayloadRef(payload_hash)

        existing = (
            self._db.query(PayloadStorageModel)
            .filter(
                PayloadStorageModel.payload_ref == str(payload_ref),
                PayloadStorageModel.graph_id == str(graph_id),
            )
            .first()
        )

        if not existing:
            try:
                # ENCRYPTION PIPELINE
                # 1. Compress (zlib)
                compressed = zlib.compress(payload.encode("utf-8"))
                # 2. Encrypt (AES-GCM via cipher)
                encrypted_bytes = self._cipher.encrypt(graph_id, compressed)
                # 3. Encode (Base64 for Text column)
                final_content = base64.b64encode(encrypted_bytes).decode("ascii")

                new_payload = PayloadStorageModel(
                    payload_ref=str(payload_ref),
                    graph_id=str(graph_id),
                    user_id=self._get_user_id(str(graph_id)),
                    content=final_content,
                    encrypted=True,  # MARK AS ENCRYPTED
                    created_at=datetime.datetime.utcnow(),
                )
                self._db.add(new_payload)
                self._db.commit()
            except Exception:
                self._db.rollback()
                raise

        return payload_ref

    def get_payload(self, payload_ref: PayloadRef) -> Optional[str]:
        """Retrieve a payload by reference."""
        import base64
        import zlib

        row = (
            self._db.query(PayloadStorageModel)
            .filter(
                PayloadStorageModel.payload_ref == str(payload_ref),
            )
            .first()
        )

        if row is None:
            return None

        # Check Encryption Flag
        if row.encrypted:
            try:
                # DECRYPTION PIPELINE
                # 1. Decode Base64
                encrypted_bytes = base64.b64decode(row.content.encode("ascii"))
                # 2. Decrypt (AES-GCM via cipher)
                # Need graph_id to decrypt (key derivation).
                # Row has graph_id but it's string. Cast it.
                gid = GraphId(row.graph_id)
                compressed = self._cipher.decrypt(gid, encrypted_bytes)
                # 3. Decompress (zlib)
                payload_bytes = zlib.decompress(compressed)
                return payload_bytes.decode("utf-8")
            except Exception as e:
                # Decryption failure (key rotation? data corruption?)
                # Log error and return None or raise
                print(f"[PostgresStore] Decryption failed for {payload_ref}: {e}")
                return None

        # Legacy / Plaintext fallback
        return row.content

    # ------------------------------------------------------------------ EventJournal

    def append(self, event: JournalEvent) -> None:
        """Append an event to the journal."""
        # Map JournalEvent to EventJournalEntry
        # op maps to kind
        # data maps to details
        # node_id is extracted from data if present
        try:
            kind = event.op
            details = event.data or {}
            node_id = details.get("node_id")

            entry = EventJournalEntry(
                ts=datetime.datetime.utcnow(),
                graph_id=str(event.graph_id),
                user_id=self._get_user_id(str(event.graph_id)),
                kind=str(kind),
                node_id=str(node_id) if node_id else None,
                details=details,
            )
            self._db.add(entry)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    def iter_events(
        self, graph_id: GraphId, since: Optional[datetime.datetime] = None
    ) -> Iterator[JournalEvent]:
        """Iterate events for a graph."""
        query = self._db.query(EventJournalEntry).filter(
            EventJournalEntry.graph_id == str(graph_id),
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
            id=NodeId(row.node_id),
            graph_id=GraphId(row.graph_id),
            vec=_deserialize_vec(row.vec),
            parents=parents,
            children=children,
            payload_ref=PayloadRef(row.payload_ref) if row.payload_ref else None,
            use_count=row.use_count or 0,
        )

    def increment_use_count(self, graph_id: GraphId, node_id: NodeId) -> None:
        """Increment the use count for a node."""
        row = (
            self._db.query(NodeStorage)
            .filter(
                NodeStorage.node_id == str(node_id),
                NodeStorage.graph_id == str(graph_id),
            )
            .first()
        )

        try:
            if row:
                row.use_count = (row.use_count or 0) + 1
                row.last_used_at = datetime.datetime.utcnow()
                self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    # ------------------------------------------------------------------ FAIMStore abstract interface

    def get_node(self, graph_id: GraphId, node_id: NodeId) -> Optional[NodeRecord]:
        """FAIMStore interface: Fetch a node by id."""
        return self.get(graph_id, node_id)

    def upsert_node(self, node: NodeRecord) -> None:
        """FAIMStore interface: Insert or update a node."""
        self.put(node.graph_id, node)

    def delete_node(self, graph_id: GraphId, node_id: NodeId) -> None:
        """FAIMStore interface: Delete a node."""
        self.delete(graph_id, node_id)

    def iter_nodes(self, graph_id: GraphId) -> Iterator[NodeRecord]:
        """FAIMStore interface: Iterate over all nodes in a graph."""
        return self.iter_graph(graph_id)

    def count_nodes(self, graph_id: GraphId) -> int:
        """FAIMStore interface: Return number of nodes."""
        return self.count(graph_id)

    def find_node_id_by_payload_ref(
        self, graph_id: GraphId, payload_ref: PayloadRef
    ) -> Optional[NodeId]:
        """FAIMStore interface: Return an existing node id for this payload_ref."""
        row = (
            self._db.query(NodeStorage)
            .filter(
                NodeStorage.payload_ref == str(payload_ref),
                NodeStorage.graph_id == str(graph_id),
            )
            .first()
        )
        if row is None:
            return None
        return NodeId(row.node_id)

    # ------------------------------------------------------------------ PayloadStore abstract interface

    def put_payload(
        self,
        graph_id: GraphId,
        payload_bytes: bytes,
        *,
        mime_type: str = "text/plain",
    ) -> PayloadRef:
        """PayloadStore interface: Store payload bytes."""
        payload_str = payload_bytes.decode("utf-8", errors="replace")
        return self.store_payload(graph_id, payload_str)

    def delete_payload(self, graph_id: GraphId, payload_ref: PayloadRef) -> None:
        """PayloadStore interface: Delete payload bytes."""
        try:
            (
                self._db.query(PayloadStorageModel)
                .filter(
                    PayloadStorageModel.payload_ref == str(payload_ref),
                    PayloadStorageModel.graph_id == str(graph_id),
                )
                .delete()
            )
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
