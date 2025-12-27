"""SQLite-backed FAIMStore + PayloadStore + EventJournal.

Implements the NodeTable, PayloadTable, and EventJournal using a single
SQLite database, as per the FAIM Production spec.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import os
from pathlib import Path
from typing import Iterator

import numpy as np

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

def _default_db_path() -> Path:
    raw = (os.getenv("FAIM_DB_PATH") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    root = (os.getenv("FAIM_ROOT") or "").strip()
    if root:
        return (Path(root).expanduser().resolve() / "Runtime" / "Storage" / "faim.sqlite3")
    return Path("Runtime/Storage/faim.sqlite3")


DEFAULT_DB_PATH = _default_db_path()


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _serialize_vec(vec: Vector) -> bytes:
    return vec.astype(np.float32).tobytes()


def _deserialize_vec(blob: bytes) -> Vector:
    arr = np.frombuffer(blob, dtype=np.float32)
    return arr.astype(np.float32)


def _parents_to_json(parents: list[ParentRef]) -> str:
    return json.dumps([{"parent_id": str(p.parent_id), "fraction": p.fraction} for p in parents])


def _parents_from_json(raw: str) -> list[ParentRef]:
    if not raw:
        return []
    items = json.loads(raw)
    return [
        ParentRef(parent_id=NodeId(item["parent_id"]), fraction=float(item["fraction"]))
        for item in items
    ]


def _children_to_json(children: list[NodeId]) -> str:
    return json.dumps([str(c) for c in children])


def _children_from_json(raw: str) -> list[NodeId]:
    if not raw:
        return []
    items = json.loads(raw)
    return [NodeId(s) for s in items]


class SqliteStore(FAIMStore, PayloadStore, EventJournal):
    """SQLite-backed implementation of FAIM storage and journaling."""

    def __init__(self, db_path: Path | str) -> None:
        path = Path(db_path)
        _ensure_parent_dir(path)

        self._conn = sqlite3.connect(
            path,
            isolation_level=None,  # autocommit
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._ensure_schema()

    # ------------------------------------------------------------------ factory

    @classmethod
    def default(cls) -> "SqliteStore":
        """Create a store using the default Runtime/Storage/faim.sqlite3 path."""
        return cls(DEFAULT_DB_PATH)

    # ------------------------------------------------------------------ schema

    def _ensure_schema(self) -> None:
        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    graph_id TEXT NOT NULL,
                    vec BLOB NOT NULL,
                    parents TEXT NOT NULL,
                    children TEXT NOT NULL,
                    payload_ref TEXT,
                    created_at REAL,
                    last_used_at REAL,
                    use_count INTEGER,
                    merged_count INTEGER,
                    flags INTEGER
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_nodes_graph ON nodes(graph_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_nodes_graph_payloadref ON nodes(graph_id, payload_ref)")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS payloads (
                    payload_ref TEXT,
                    graph_id TEXT,
                    payload_bytes BLOB NOT NULL,
                    mime_type TEXT,
                    compressed INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (graph_id, payload_ref)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    graph_id TEXT NOT NULL,
                    op TEXT NOT NULL,
                    data TEXT NOT NULL
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_events_graph_ts ON events(graph_id, ts)")

    # ------------------------------------------------------------------ node I/O

    def get_node(self, graph_id: GraphId, node_id: NodeId) -> NodeRecord | None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM nodes
                WHERE id = ? AND graph_id = ?
                """,
                (str(node_id), str(graph_id)),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_node(row)
        
    def find_node_id_by_payload_ref(
        self, graph_id: GraphId, payload_ref: PayloadRef
    ) -> NodeId | None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT id
                FROM nodes
                WHERE graph_id = ? AND payload_ref = ?
                LIMIT 1
                """,
                (str(graph_id), str(payload_ref)),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return NodeId(str(row[0]))

    def upsert_node(self, node: NodeRecord) -> None:
        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO nodes (
                    id, graph_id, vec, parents, children,
                    payload_ref, created_at, last_used_at,
                    use_count, merged_count, flags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    graph_id = excluded.graph_id,
                    vec = excluded.vec,
                    parents = excluded.parents,
                    children = excluded.children,
                    payload_ref = excluded.payload_ref,
                    created_at = excluded.created_at,
                    last_used_at = excluded.last_used_at,
                    use_count = excluded.use_count,
                    merged_count = excluded.merged_count,
                    flags = excluded.flags
                """,
                (
                    str(node.id),
                    str(node.graph_id),
                    _serialize_vec(node.vec),
                    _parents_to_json(node.parents),
                    _children_to_json(node.children),
                    str(node.payload_ref) if node.payload_ref is not None else None,
                    float(node.created_at),
                    float(node.last_used_at),
                    int(node.use_count),
                    int(node.merged_count),
                    int(node.flags),
                ),
            )

    def delete_node(self, graph_id: GraphId, node_id: NodeId) -> None:
        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.execute(
                "DELETE FROM nodes WHERE id = ? AND graph_id = ?",
                (str(node_id), str(graph_id)),
            )

    def iter_nodes(self, graph_id: GraphId) -> Iterator[NodeRecord]:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM nodes
                WHERE graph_id = ?
                ORDER BY id
                """,
                (str(graph_id),),
            )
            rows = cur.fetchall()
        for row in rows:
            yield self._row_to_node(row)

    def count_nodes(self, graph_id: GraphId) -> int:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM nodes WHERE graph_id = ?",
                (str(graph_id),),
            )
            row = cur.fetchone()
            return int(row["cnt"] if row is not None else 0)

    # ---------------------------------------------------------------- payload I/O

    def put_payload(
        self,
        graph_id: GraphId,
        payload_bytes: bytes,
        *,
        mime_type: str = "text/plain",
    ) -> PayloadRef:
        """Store payload bytes and return a SHA256-based PayloadRef.

        Idempotent: same (graph_id, payload_bytes) pair will not create duplicates.
        """
        digest = hashlib.sha256(payload_bytes).hexdigest()
        ref = PayloadRef(digest)
        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT OR IGNORE INTO payloads (
                    payload_ref, graph_id, payload_bytes, mime_type, compressed
                )
                VALUES (?, ?, ?, ?, 0)
                """,
                (digest, str(graph_id), payload_bytes, mime_type),
            )
        return ref

    def get_payload(
        self,
        graph_id: GraphId,
        payload_ref: PayloadRef,
    ) -> bytes | None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT payload_bytes
                FROM payloads
                WHERE graph_id = ? AND payload_ref = ?
                """,
                (str(graph_id), str(payload_ref)),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return bytes(row["payload_bytes"])

    def delete_payload(self, graph_id: GraphId, payload_ref: PayloadRef) -> None:
        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.execute(
                """
                DELETE FROM payloads
                WHERE graph_id = ? AND payload_ref = ?
                """,
                (str(graph_id), str(payload_ref)),
            )

    # -------------------------------------------------------------- journal I/O

    def append(self, event: JournalEvent) -> None:
        """Append a journal event into the events table."""
        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO events (ts, graph_id, op, data)
                VALUES (?, ?, ?, ?)
                """,
                (
                    float(event.ts),
                    str(event.graph_id),
                    event.op,
                    json.dumps(event.data, separators=(",", ":")),
                ),
            )

    # ----------------------------------------------------------------- helpers

    @staticmethod
    def _row_to_node(row: sqlite3.Row) -> NodeRecord:
        vec = _deserialize_vec(row["vec"])
        parents = _parents_from_json(row["parents"])
        children = _children_from_json(row["children"])
        payload_ref = PayloadRef(row["payload_ref"]) if row["payload_ref"] is not None else None
        return NodeRecord(
            id=NodeId(row["id"]),
            graph_id=GraphId(row["graph_id"]),
            vec=vec,
            parents=parents,
            children=children,
            payload_ref=payload_ref,
            created_at=float(row["created_at"] or 0.0),
            last_used_at=float(row["last_used_at"] or 0.0),
            use_count=int(row["use_count"] or 0),
            merged_count=int(row["merged_count"] or 0),
            flags=int(row["flags"] or 0),
        )
