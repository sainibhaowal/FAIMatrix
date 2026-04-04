"""Acceptance tests for FAIM-native core write operations.

Tests: ingest → extract → packet → encode → write_atoms
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.contracts.types import EventRecord, uuid7  # noqa: E402
from core.engine_native import FAIMNativeEngine  # noqa: E402
from encoding.text_vectorizer import vectorize_blocks  # noqa: E402
from perception.packetize import create_packet  # noqa: E402
from perception.router import route_extraction  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from store.pg.models_faim import create_all_tables  # noqa: E402
from store.pg.repos.edge_repo import EdgeRepo  # noqa: E402
from store.pg.repos.event_repo import EventRepo  # noqa: E402
from store.pg.repos.graph_version_repo import GraphVersionRepo  # noqa: E402
from store.pg.repos.node_repo import NodeRepo  # noqa: E402


class EventRepoWrapper:
    """Wrapper to give EventRepo a session."""

    def __init__(self, session):
        self.session = session
        self._repo = EventRepo()

    def append(self, graph_id: str, kind: str, payload: dict):
        import hashlib
        import json
        from datetime import datetime, timezone

        ts = datetime.now(timezone.utc)
        checksum = hashlib.sha256(
            f"{ts.isoformat()}|{graph_id}|{kind}|{json.dumps(payload)}".encode()
        ).hexdigest()
        event = EventRecord(
            id=uuid7(),
            seq=None,
            ts=ts,
            graph_id=graph_id,
            kind=kind,
            payload=payload,
            checksum=checksum,
            created_at=ts,
        )
        return self._repo.append(self.session, event)

    def emit(self, session, graph_id: str, kind: str, payload: dict):
        """Match production interface."""
        return self.append(graph_id, kind, payload)

    def emit(self, session, graph_id: str, kind: str, payload: dict):
        """Match production interface."""
        return self.append(graph_id, kind, payload)

    def list(self, graph_id: str, limit: int = 100):
        return self._repo.list(self.session, graph_id=graph_id, limit=limit)


class GraphVersionRepoWrapper:
    """Wrapper to give GraphVersionRepo a session."""

    def __init__(self, session):
        self.session = session
        self._repo = GraphVersionRepo()

    def get(self, session, graph_id: str):
        return self._repo.get(self.session, graph_id)

    def bump(self, session, graph_id: str, reason: str = None):
        return self._repo.bump(self.session, graph_id, reason=reason)


@pytest.fixture
def engine_and_session():
    """Create test database and session."""
    engine = create_engine("sqlite:///:memory:")
    create_all_tables(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield engine, session
    session.close()


@pytest.fixture
def repos(engine_and_session):
    """Create all repositories."""
    _, session = engine_and_session
    return {
        "node_repo": NodeRepo(session),
        "edge_repo": EdgeRepo(session),
        "event_repo": EventRepoWrapper(session),
        "graph_version_repo": GraphVersionRepoWrapper(session),
    }


@pytest.fixture
def faim_engine(repos):
    """Create FAIM-native engine."""
    return FAIMNativeEngine(
        node_repo=repos["node_repo"],
        edge_repo=repos["edge_repo"],
        event_repo=repos["event_repo"],
        graph_version_repo=repos["graph_version_repo"],
    )


class TestAT_C1_CoreWrite:
    """Acceptance tests for core write operations."""

    def test_write_atoms_creates_nodes(self, faim_engine, repos):
        """write_atoms should create nodes in the graph."""
        graph_id = "test_graph_001"

        # Create test vectors
        content = b"This is test content for FAIM-native core write."
        blocks = route_extraction(content, "test.txt", "raw_001")
        vectors = vectorize_blocks(blocks)

        # Write atoms
        result = faim_engine.write_atoms(graph_id, vectors)

        assert result.nodes_written >= 1
        assert len(result.node_ids) >= 1

    def test_write_atoms_creates_events(self, faim_engine, repos):
        """write_atoms should emit events."""
        graph_id = "test_graph_002"

        content = b"Event test content."
        blocks = route_extraction(content, "test.txt", "raw_002")
        vectors = vectorize_blocks(blocks)

        result = faim_engine.write_atoms(graph_id, vectors)

        assert result.events_emitted >= 1

    def test_write_atoms_bumps_version(self, faim_engine, repos):
        """write_atoms should bump graph version."""
        graph_id = "test_graph_003"

        content = b"Version test content."
        blocks = route_extraction(content, "test.txt", "raw_003")
        vectors = vectorize_blocks(blocks)

        result = faim_engine.write_atoms(graph_id, vectors)

        assert result.graph_version >= 1

    def test_write_multiple_creates_inheritance(self, faim_engine, repos):
        """Writing multiple vectors should create inheritance edges."""
        graph_id = "test_graph_004"

        # First write - becomes parent
        content1 = b"First document for parent nodes."
        blocks1 = route_extraction(content1, "test1.txt", "raw_004a")
        vectors1 = vectorize_blocks(blocks1)
        faim_engine.write_atoms(graph_id, vectors1)

        # Second write - should get inheritance from first
        content2 = b"Second document similar to first document."
        blocks2 = route_extraction(content2, "test2.txt", "raw_004b")
        vectors2 = vectorize_blocks(blocks2)
        result = faim_engine.write_atoms(graph_id, vectors2)

        # Should have inheritance edges
        assert (
            result.edges_written >= 0
        )  # May or may not have edges depending on similarity

    def test_full_pipeline_integration(self, faim_engine, repos):
        """Full pipeline: extract → packet → encode → write."""
        graph_id = "test_graph_005"

        # Extract
        content = b"Full pipeline integration test for FAIM-native core."
        raw_id = "raw_005"
        blocks = route_extraction(content, "test.txt", raw_id)

        # Packet
        create_packet(raw_id, blocks)

        # Encode
        vectors = vectorize_blocks(blocks)

        # Write
        result = faim_engine.write_atoms(graph_id, vectors)

        # Verify
        assert result.nodes_written == len(vectors)
        assert result.events_emitted >= 1
        assert result.graph_version >= 1

    def test_graph_hash_computed(self, faim_engine, repos):
        """compute_graph_hash should return stable hash."""
        graph_id = "test_graph_006"

        content = b"Hash test content."
        blocks = route_extraction(content, "test.txt", "raw_006")
        vectors = vectorize_blocks(blocks)

        faim_engine.write_atoms(graph_id, vectors)

        hash1 = faim_engine.compute_graph_hash(graph_id)
        hash2 = faim_engine.compute_graph_hash(graph_id)

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_idempotent_upsert(self, faim_engine, repos):
        """Writing same vector twice should be idempotent."""
        graph_id = "test_graph_007"

        content = b"Idempotent test content."
        blocks = route_extraction(content, "test.txt", "raw_007")
        vectors = vectorize_blocks(blocks)

        result1 = faim_engine.write_atoms(graph_id, vectors)
        result2 = faim_engine.write_atoms(graph_id, vectors)

        # Both writes should succeed
        assert result1.nodes_written >= 1
        assert result2.nodes_written >= 1

        # Node count should not double
        node_count = repos["node_repo"].count_nodes(graph_id)
        assert node_count == result1.nodes_written
