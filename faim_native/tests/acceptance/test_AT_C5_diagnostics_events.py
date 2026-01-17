"""Acceptance tests for diagnostics events.

Tests that evolve_once emits DIAGNOSTICS_SNAPSHOT with D/H/λ.
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

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from core.contracts.types import EventRecord, uuid7  # noqa: E402
from core.dynamics.evolution_native import evolve_once  # noqa: E402
from core.engine_native import FAIMNativeEngine  # noqa: E402
from encoding.text_vectorizer import vectorize_blocks  # noqa: E402
from perception.router import route_extraction  # noqa: E402
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

    def list(self, graph_id: str, limit: int = 100):
        return self._repo.get_all(self.session, graph_id=graph_id, limit=limit)


class GraphVersionRepoWrapper:
    """Wrapper to give GraphVersionRepo a session."""

    def __init__(self, session):
        self.session = session
        self._repo = GraphVersionRepo()

    def get(self, graph_id: str):
        return self._repo.get(self.session, graph_id)

    def bump(self, graph_id: str, reason: str = None):
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


class TestAT_C5_DiagnosticsEvents:
    """Acceptance tests for diagnostics events."""

    def test_evolve_emits_diagnostics_snapshot(self, repos):
        """evolve_once should emit DIAGNOSTICS_SNAPSHOT event."""
        graph_id = "test_diag_001"

        # Write some data first
        faim_engine = FAIMNativeEngine(**repos)

        for text in [b"Test content one", b"Test content two", b"Test content three"]:
            blocks = route_extraction(text, "test.txt", str(uuid7()))
            vectors = vectorize_blocks(blocks)
            faim_engine.write_atoms(graph_id, vectors)

        # Run evolve
        evolve_once(
            graph_id=graph_id,
            node_repo=repos["node_repo"],
            edge_repo=repos["edge_repo"],
            event_repo=repos["event_repo"],
            graph_version_repo=repos["graph_version_repo"],
        )

        # Check for DIAGNOSTICS_SNAPSHOT event
        events = repos["event_repo"].list(graph_id=graph_id, limit=100)
        snapshot_events = [e for e in events if e.kind == "DIAGNOSTICS_SNAPSHOT"]

        assert len(snapshot_events) >= 1

    def test_diagnostics_payload_has_D_H_lambda(self, repos):
        """DIAGNOSTICS_SNAPSHOT payload should include D/H/λ."""
        graph_id = "test_diag_002"

        # Write data
        faim_engine = FAIMNativeEngine(**repos)

        for text in [b"Alpha content", b"Beta content"]:
            blocks = route_extraction(text, "test.txt", str(uuid7()))
            vectors = vectorize_blocks(blocks)
            faim_engine.write_atoms(graph_id, vectors)

        # Run evolve
        evolve_once(
            graph_id=graph_id,
            node_repo=repos["node_repo"],
            edge_repo=repos["edge_repo"],
            event_repo=repos["event_repo"],
            graph_version_repo=repos["graph_version_repo"],
        )

        # Get DIAGNOSTICS_SNAPSHOT event
        events = repos["event_repo"].list(graph_id=graph_id, limit=100)
        snapshot_events = [e for e in events if e.kind == "DIAGNOSTICS_SNAPSHOT"]

        assert len(snapshot_events) >= 1
        payload = snapshot_events[0].payload

        # Check required fields
        assert "D_hat" in payload
        assert "H_hat" in payload
        assert "lambda_hat" in payload
        assert "diagnostics_hash" in payload
        assert "graph_version" in payload

    def test_diagnostics_hash_is_64_hex(self, repos):
        """diagnostics_hash should be 64-char hex string."""
        graph_id = "test_diag_003"

        # Write data
        faim_engine = FAIMNativeEngine(**repos)

        blocks = route_extraction(b"Test for hash", "test.txt", str(uuid7()))
        vectors = vectorize_blocks(blocks)
        faim_engine.write_atoms(graph_id, vectors)

        # Run evolve
        evolve_once(
            graph_id=graph_id,
            node_repo=repos["node_repo"],
            edge_repo=repos["edge_repo"],
            event_repo=repos["event_repo"],
            graph_version_repo=repos["graph_version_repo"],
        )

        # Get hash
        events = repos["event_repo"].list(graph_id=graph_id, limit=100)
        snapshot_events = [e for e in events if e.kind == "DIAGNOSTICS_SNAPSHOT"]

        if snapshot_events:
            diag_hash = snapshot_events[0].payload.get("diagnostics_hash", "")
            assert len(diag_hash) == 64
            assert all(c in "0123456789abcdef" for c in diag_hash)

    def test_evolution_result_has_diagnostics(self, repos):
        """EvolutionResult should include diagnostics object."""
        graph_id = "test_diag_004"

        # Write data
        faim_engine = FAIMNativeEngine(**repos)

        blocks = route_extraction(b"Diagnostics test", "test.txt", str(uuid7()))
        vectors = vectorize_blocks(blocks)
        faim_engine.write_atoms(graph_id, vectors)

        # Run evolve
        result = evolve_once(
            graph_id=graph_id,
            node_repo=repos["node_repo"],
            edge_repo=repos["edge_repo"],
            event_repo=repos["event_repo"],
            graph_version_repo=repos["graph_version_repo"],
        )

        # Check result has diagnostics
        assert result.diagnostics is not None
        assert result.diagnostics.s > 0
        assert result.diagnostics.D_hat >= 0
        assert result.diagnostics.H_hat >= 0
        assert result.diagnostics.lambda_hat >= 0
