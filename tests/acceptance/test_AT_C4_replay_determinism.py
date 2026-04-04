"""Acceptance tests for replay determinism."""

from __future__ import annotations

import sys
from pathlib import Path

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.contracts.types import EventRecord, uuid7  # noqa: E402
from core.engine_native import FAIMNativeEngine  # noqa: E402
from encoding.text_vectorizer import vectorize_blocks  # noqa: E402
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

    def emit(self, session, graph_id: str, kind: str, payload: dict):
        """Match production interface."""
        return self.append(graph_id, kind, payload)


class GraphVersionRepoWrapper:
    """Wrapper to give GraphVersionRepo a session."""

    def __init__(self, session):
        self.session = session
        self._repo = GraphVersionRepo()

    def get(self, session, graph_id: str):
        return self._repo.get(self.session, graph_id)

    def bump(self, session, graph_id: str, reason: str = None):
        return self._repo.bump(self.session, graph_id, reason=reason)


def create_fresh_session():
    """Create a fresh test database and session."""
    engine = create_engine("sqlite:///:memory:")
    create_all_tables(engine)
    Session = sessionmaker(bind=engine)
    return Session()


class TestAT_C4_ReplayDeterminism:
    """Acceptance tests for replay determinism."""

    def test_same_input_same_vectors(self):
        """Same input should produce same v_native vectors."""
        content = b"Deterministic replay test content for FAIM-native."
        raw_id = "raw_replay_001"
        graph_id = "test_replay_001"

        # First run
        session1 = create_fresh_session()
        repos1 = {
            "node_repo": NodeRepo(session1),
            "edge_repo": EdgeRepo(session1),
            "event_repo": EventRepoWrapper(session1),
            "graph_version_repo": GraphVersionRepoWrapper(session1),
        }
        engine1 = FAIMNativeEngine(**repos1)

        blocks1 = route_extraction(content, "test.txt", raw_id)
        vectors1 = vectorize_blocks(blocks1)
        engine1.write_atoms(graph_id, vectors1)

        # Get v_native from first run
        nodes1 = repos1["node_repo"].list_nodes(graph_id, limit=100)
        v_natives1 = [tuple(n.v_native) for n in nodes1]

        # Second run (fresh database)
        session2 = create_fresh_session()
        repos2 = {
            "node_repo": NodeRepo(session2),
            "edge_repo": EdgeRepo(session2),
            "event_repo": EventRepoWrapper(session2),
            "graph_version_repo": GraphVersionRepoWrapper(session2),
        }
        engine2 = FAIMNativeEngine(**repos2)

        blocks2 = route_extraction(content, "test.txt", raw_id)
        vectors2 = vectorize_blocks(blocks2)
        engine2.write_atoms(graph_id, vectors2)

        # Get v_native from second run
        nodes2 = repos2["node_repo"].list_nodes(graph_id, limit=100)
        v_natives2 = [tuple(n.v_native) for n in nodes2]

        session1.close()
        session2.close()

        # v_native vectors should match (deterministic from content)
        assert v_natives1 == v_natives2

    def test_different_input_different_hash(self):
        """Different input should produce different graph hash."""
        graph_id = "test_replay_002"

        # First content
        session1 = create_fresh_session()
        repos1 = {
            "node_repo": NodeRepo(session1),
            "edge_repo": EdgeRepo(session1),
            "event_repo": EventRepoWrapper(session1),
            "graph_version_repo": GraphVersionRepoWrapper(session1),
        }
        engine1 = FAIMNativeEngine(**repos1)

        blocks1 = route_extraction(b"Content A", "a.txt", "raw_a")
        vectors1 = vectorize_blocks(blocks1)
        engine1.write_atoms(graph_id, vectors1)
        hash1 = engine1.compute_graph_hash(graph_id)

        # Different content
        session2 = create_fresh_session()
        repos2 = {
            "node_repo": NodeRepo(session2),
            "edge_repo": EdgeRepo(session2),
            "event_repo": EventRepoWrapper(session2),
            "graph_version_repo": GraphVersionRepoWrapper(session2),
        }
        engine2 = FAIMNativeEngine(**repos2)

        blocks2 = route_extraction(b"Content B", "b.txt", "raw_b")
        vectors2 = vectorize_blocks(blocks2)
        engine2.write_atoms(graph_id, vectors2)
        hash2 = engine2.compute_graph_hash(graph_id)

        session1.close()
        session2.close()

        # Hashes should differ
        assert hash1 != hash2

    def test_graph_hash_stable_after_read(self):
        """Graph hash should be stable after multiple reads."""
        graph_id = "test_replay_003"
        content = b"Stable hash test."

        session = create_fresh_session()
        repos = {
            "node_repo": NodeRepo(session),
            "edge_repo": EdgeRepo(session),
            "event_repo": EventRepoWrapper(session),
            "graph_version_repo": GraphVersionRepoWrapper(session),
        }
        engine = FAIMNativeEngine(**repos)

        blocks = route_extraction(content, "test.txt", "raw_003")
        vectors = vectorize_blocks(blocks)
        engine.write_atoms(graph_id, vectors)

        # Multiple reads
        hash1 = engine.compute_graph_hash(graph_id)
        hash2 = engine.compute_graph_hash(graph_id)
        hash3 = engine.compute_graph_hash(graph_id)

        session.close()

        assert hash1 == hash2 == hash3
