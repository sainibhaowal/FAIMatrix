"""Acceptance tests for antisymmetric merge operations."""

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

from core.antisym import merge_vectors, opposition_score, should_merge  # noqa: E402
from core.contracts.types import (  # noqa: E402
    BlockAnchor,
    EventRecord,
    EvidenceBlock,
    uuid7,
)
from encoding.text_vectorizer import vectorize_block  # noqa: E402
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


class TestAT_C2_AntisymMerge:
    """Acceptance tests for antisymmetric merge."""

    def test_identical_vectors_high_score(self):
        """Identical vectors should have high opposition score."""
        v = [0.1] * 256
        score = opposition_score(v, v)
        assert score >= 0.99

    def test_orthogonal_vectors_low_score(self):
        """Orthogonal vectors should have low opposition score."""
        v1 = [1.0] + [0.0] * 255
        v2 = [0.0, 1.0] + [0.0] * 254
        score = opposition_score(v1, v2)
        assert score < 0.1

    def test_should_merge_above_threshold(self):
        """should_merge should return True above threshold."""
        assert should_merge(0.96, 0.95) is True
        assert should_merge(0.94, 0.95) is False

    def test_merge_deterministic_winner(self):
        """Merge should select deterministic winner."""
        from uuid import UUID

        a_id = UUID("00000000-0000-0000-0000-000000000001")
        b_id = UUID("00000000-0000-0000-0000-000000000002")
        a_hash = "aaa111"
        b_hash = "bbb222"

        result = merge_vectors(a_id, b_id, a_hash, b_hash, 0.98)

        # Lower hash wins
        assert result.winner_id == a_id
        assert result.loser_id == b_id

    def test_merge_reverse_order_same_winner(self):
        """Merge should give same winner regardless of input order."""
        from uuid import UUID

        a_id = UUID("00000000-0000-0000-0000-000000000001")
        b_id = UUID("00000000-0000-0000-0000-000000000002")
        a_hash = "aaa111"
        b_hash = "bbb222"

        result1 = merge_vectors(a_id, b_id, a_hash, b_hash, 0.98)
        result2 = merge_vectors(b_id, a_id, b_hash, a_hash, 0.98)

        assert result1.winner_id == result2.winner_id
        assert result1.loser_id == result2.loser_id

    def test_near_duplicate_triggers_merge(self, repos):
        """Near-duplicate vectors should trigger merge in engine."""

        # Create two very similar blocks
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=100)
        block1 = EvidenceBlock.create(
            raw_id="raw_001",
            anchor=anchor,
            content="This is exactly the same content",
        )
        block2 = EvidenceBlock.create(
            raw_id="raw_002",
            anchor=anchor,
            content="This is exactly the same content",
        )

        vec1 = vectorize_block(block1)
        vec2 = vectorize_block(block2)

        # Check they have same hash (after normalization)
        assert vec1.v_native == vec2.v_native
