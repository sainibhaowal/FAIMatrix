"""Unit tests for SnapshotRepo."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest

# Setup path for isolated imports
_FAIM_NATIVE_ROOT = Path(__file__).parent.parent.parent
if str(_FAIM_NATIVE_ROOT) not in sys.path:
    sys.path.insert(0, str(_FAIM_NATIVE_ROOT))

from core.contracts.types import SnapshotRecord, compute_graph_hash  # noqa: E402
from store.pg.repos.graph_version_repo import GraphVersionRepo  # noqa: E402
from store.pg.repos.snapshot_repo import SnapshotRepo  # noqa: E402
from store.pg.session import SessionFactory  # noqa: E402


@pytest.mark.unit
class TestSnapshotRepo:
    """Unit tests for SnapshotRepo operations."""

    def test_create_snapshot(self, session_factory: SessionFactory):
        """Creating a snapshot stores it in the database."""
        with session_factory.atomic() as session:
            repo = SnapshotRepo()
            graph_hash = compute_graph_hash(["hash1", "hash2", "hash3"])
            snapshot = SnapshotRecord.create(
                graph_id="test_graph",
                graph_version=1,
                graph_hash=graph_hash,
                node_count=3,
            )
            saved = repo.create(session, snapshot)
            assert saved.id == snapshot.id
            assert saved.graph_id == "test_graph"
            assert saved.graph_version == 1
            assert saved.graph_hash == graph_hash
            assert saved.node_count == 3

    def test_get_by_id(self, session_factory: SessionFactory):
        """Get snapshot by UUID works correctly."""
        with session_factory.atomic() as session:
            repo = SnapshotRepo()
            snapshot = SnapshotRecord.create(
                graph_id="test_graph",
                graph_version=1,
                graph_hash="abc123",
                node_count=5,
            )
            saved = repo.create(session, snapshot)
            fetched = repo.get_by_id(session, saved.id)
            assert fetched is not None
            assert fetched.id == saved.id
            assert fetched.graph_hash == "abc123"

    def test_get_by_id_not_found(self, session_factory: SessionFactory):
        """Get by non-existent ID returns None."""
        with session_factory.session() as session:
            repo = SnapshotRepo()
            result = repo.get_by_id(session, uuid4())
            assert result is None

    def test_list_by_graph(self, session_factory: SessionFactory):
        """List snapshots for a graph returns correct results."""
        with session_factory.atomic() as session:
            repo = SnapshotRepo()
            for i in range(5):
                snapshot = SnapshotRecord.create(
                    graph_id="test_graph",
                    graph_version=i + 1,
                    graph_hash=f"hash_{i}",
                    node_count=i * 10,
                )
                repo.create(session, snapshot)
            results = repo.list_by_graph(session, "test_graph", limit=10)
            assert len(results) == 5

    def test_list_ordered_by_created_desc(self, session_factory: SessionFactory):
        """Snapshots are listed newest first."""
        with session_factory.atomic() as session:
            repo = SnapshotRepo()
            for i in range(3):
                snapshot = SnapshotRecord.create(
                    graph_id="test_graph",
                    graph_version=i + 1,
                    graph_hash=f"hash_{i}",
                    node_count=i,
                )
                repo.create(session, snapshot)
            results = repo.list_by_graph(session, "test_graph", limit=10)
            versions = [r.graph_version for r in results]
            assert versions == sorted(versions, reverse=True)

    def test_get_latest(self, session_factory: SessionFactory):
        """Get latest snapshot returns most recent."""
        with session_factory.atomic() as session:
            repo = SnapshotRepo()
            for i in range(5):
                snapshot = SnapshotRecord.create(
                    graph_id="test_graph",
                    graph_version=i + 1,
                    graph_hash=f"hash_{i}",
                    node_count=i,
                )
                repo.create(session, snapshot)
            latest = repo.get_latest(session, "test_graph")
            assert latest is not None
            assert latest.graph_version == 5

    def test_get_latest_empty_graph(self, session_factory: SessionFactory):
        """Get latest on graph with no snapshots returns None."""
        with session_factory.session() as session:
            repo = SnapshotRepo()
            result = repo.get_latest(session, "nonexistent_graph")
            assert result is None

    def test_graph_hash_stored_correctly(self, session_factory: SessionFactory):
        """Graph hash is stored and retrieved correctly."""
        with session_factory.atomic() as session:
            repo = SnapshotRepo()
            node_hashes = ["aaa111", "bbb222", "ccc333"]
            graph_hash = compute_graph_hash(node_hashes)
            snapshot = SnapshotRecord.create(
                graph_id="test_graph",
                graph_version=1,
                graph_hash=graph_hash,
                node_count=3,
            )
            repo.create(session, snapshot)
            fetched = repo.get_latest(session, "test_graph")
            assert fetched.graph_hash == graph_hash
            assert len(fetched.graph_hash) == 64

    def test_graph_version_recorded(self, session_factory: SessionFactory):
        """Snapshot records the correct graph version."""
        with session_factory.atomic() as session:
            version_repo = GraphVersionRepo()
            snapshot_repo = SnapshotRepo()
            version = version_repo.bump(session, "test_graph", "test bump")
            snapshot = SnapshotRecord.create(
                graph_id="test_graph",
                graph_version=version,
                graph_hash="test_hash",
                node_count=10,
            )
            snapshot_repo.create(session, snapshot)
            fetched = snapshot_repo.get_latest(session, "test_graph")
            assert fetched.graph_version == version

    def test_get_by_version(self, session_factory: SessionFactory):
        """Get snapshot by exact version works."""
        with session_factory.atomic() as session:
            repo = SnapshotRepo()
            for v in [1, 5, 10]:
                snapshot = SnapshotRecord.create(
                    graph_id="test_graph",
                    graph_version=v,
                    graph_hash=f"hash_v{v}",
                    node_count=v * 10,
                )
                repo.create(session, snapshot)
            result = repo.get_by_version(session, "test_graph", 5)
            assert result is not None
            assert result.graph_version == 5
            assert result.graph_hash == "hash_v5"

    def test_count(self, session_factory: SessionFactory):
        """Count returns correct number of snapshots."""
        with session_factory.atomic() as session:
            repo = SnapshotRepo()
            for i in range(7):
                snapshot = SnapshotRecord.create(
                    graph_id="test_graph",
                    graph_version=i + 1,
                    graph_hash=f"hash_{i}",
                    node_count=i,
                )
                repo.create(session, snapshot)
            count = repo.count(session, "test_graph")
            assert count == 7

    def test_graph_isolation(self, session_factory: SessionFactory):
        """Snapshots from different graphs are isolated."""
        with session_factory.atomic() as session:
            repo = SnapshotRepo()
            for graph_id in ["graph_a", "graph_b", "graph_c"]:
                for i in range(2):
                    snapshot = SnapshotRecord.create(
                        graph_id=graph_id,
                        graph_version=i + 1,
                        graph_hash=f"{graph_id}_hash_{i}",
                        node_count=i,
                    )
                    repo.create(session, snapshot)

            results_a = repo.list_by_graph(session, "graph_a", limit=10)
            results_b = repo.list_by_graph(session, "graph_b", limit=10)
            assert len(results_a) == 2
            assert len(results_b) == 2
            assert all(r.graph_id == "graph_a" for r in results_a)
            assert all(r.graph_id == "graph_b" for r in results_b)

    def test_metadata_stored(self, session_factory: SessionFactory):
        """Snapshot metadata is stored and retrieved."""
        with session_factory.atomic() as session:
            repo = SnapshotRepo()
            snapshot = SnapshotRecord.create(
                graph_id="test_graph",
                graph_version=1,
                graph_hash="test_hash",
                node_count=5,
                metadata={"source": "unit_test", "extra": {"nested": True}},
            )
            repo.create(session, snapshot)
            fetched = repo.get_latest(session, "test_graph")
            assert fetched.metadata is not None
            assert fetched.metadata["source"] == "unit_test"
            assert fetched.metadata["extra"]["nested"] is True
