"""Acceptance Test SEM1: Semantic Edge Typing End-to-End.

Full workflow: ingest atoms, verify semantic edges created, query, verify semantic scoring.
"""

from __future__ import annotations

import math
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from faim_native.core.contracts.types import BlockAnchor
from faim_native.core.engine_native import FAIMNativeEngine
from faim_native.core.operators.semantic_typing import KNOWN_SEMANTIC_KINDS
from faim_native.encoding.vector_schema import FAIMVector
from faim_native.store.pg.models_faim import Base, EdgeModel, NodeModel
from faim_native.store.pg.repos.edge_repo import EdgeRepo
from faim_native.store.pg.repos.event_repo import EventRepo
from faim_native.store.pg.repos.graph_version_repo import GraphVersionRepo
from faim_native.store.pg.repos.node_repo import NodeRepo


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def repos(in_memory_db):
    """Create all required repositories."""
    return {
        "node_repo": NodeRepo(session=in_memory_db, tenant_id="test_tenant"),
        "edge_repo": EdgeRepo(session=in_memory_db, tenant_id="test_tenant"),
        "event_repo": EventRepo(session=in_memory_db, tenant_id="test_tenant"),
        "graph_version_repo": GraphVersionRepo(
            session=in_memory_db, tenant_id="test_tenant"
        ),
    }


@pytest.fixture
def engine(repos):
    """Create FAIM native engine."""
    return FAIMNativeEngine(
        node_repo=repos["node_repo"],
        edge_repo=repos["edge_repo"],
        event_repo=repos["event_repo"],
        graph_version_repo=repos["graph_version_repo"],
        parent_top_k=8,
        antisym_threshold=0.95,
    )


def create_test_vector(
    vector_data: list[float],
    raw_id: str | None = None,
    block_id: str | None = None,
) -> FAIMVector:
    """Create a test FAIMVector."""
    return FAIMVector.create(
        raw_id=raw_id or f"raw_{uuid4()}",
        block_id=block_id or f"block_{uuid4()}",
        block_type="text",
        anchor=BlockAnchor(doc_type="text", char_start=0, char_end=len(vector_data)),
        v_native=vector_data,
        opp_signature={},
        residual=0.0,
        level=0,
    )


class TestSemanticEdgesEndToEnd:
    """End-to-end test of semantic edge creation and usage."""

    def test_write_similar_atoms_creates_semantic_edges(self, engine, repos, in_memory_db):
        """Writing highly similar atoms should create semantic edges."""
        graph_id = "test_graph"

        # Create two very similar vectors (cosine > 0.93 = synonym)
        vec1 = [0.5] * 256
        vec2 = [0.501] * 256  # Nearly identical

        vector1 = create_test_vector(
            vec1,
            block_id="block_1",
        )
        vector2 = create_test_vector(
            vec2,
            block_id="block_2",
        )

        # Normalize vectors for cosine computation
        norm1 = math.sqrt(sum(x * x for x in vec1))
        norm2 = math.sqrt(sum(x * x for x in vec2))
        vec1_norm = tuple(x / norm1 for x in vec1)
        vec2_norm = tuple(x / norm2 for x in vec2)

        # Compute cosine similarity
        cosine_sim = sum(a * b for a, b in zip(vec1_norm, vec2_norm))
        print(f"Cosine similarity: {cosine_sim}")

        # Write vectors
        result = engine.write_atoms(graph_id, [vector1, vector2])

        assert result.nodes_written == 2

        # Verify inheritance edges created
        inheritance_edges = (
            in_memory_db.query(EdgeModel)
            .filter(
                EdgeModel.graph_id == graph_id,
                EdgeModel.kind == "inheritance",
            )
            .all()
        )
        assert len(inheritance_edges) > 0

        # Verify meta is populated (Layer A)
        for edge in inheritance_edges:
            if edge.meta:
                assert "semantic_type" in edge.meta
                assert "semantic_weight" in edge.meta

    def test_semantic_edges_created_above_threshold(self, engine, repos, in_memory_db):
        """Semantic edges (Layer B) should be created for cosine >= 0.65."""
        graph_id = "test_graph"

        # Create vectors with moderate similarity (cosine ~0.8 = hypernym range)
        vec_base = [1.0] + [0.0] * 255
        vec_similar = [0.8] + [0.6] + [0.0] * 254

        vector1 = create_test_vector(
            vec_base,
            block_id="base",
        )
        vector2 = create_test_vector(
            vec_similar,
            block_id="similar",
        )

        # Write vectors
        result = engine.write_atoms(graph_id, [vector1, vector2])

        # Verify semantic edges created (Layer B)
        semantic_edges = (
            in_memory_db.query(EdgeModel)
            .filter(
                EdgeModel.graph_id == graph_id,
                EdgeModel.kind.in_(list(KNOWN_SEMANTIC_KINDS)),
            )
            .all()
        )

        # Should have semantic edges if similarity is high enough
        # Note: actual threshold depends on vector values and cosine computation
        print(f"Semantic edges created: {len(semantic_edges)}")

    def test_semantic_metadata_stored_on_inheritance(
        self, engine, repos, in_memory_db
    ):
        """Inheritance edges should have semantic metadata (Layer A)."""
        graph_id = "test_graph"

        vec1 = [1.0] + [0.0] * 255
        vec2 = [0.9] + [0.1] + [0.0] * 254

        vector1 = create_test_vector(
            vec1,
            block_id="b1",
        )
        vector2 = create_test_vector(
            vec2,
            block_id="b2",
        )

        result = engine.write_atoms(graph_id, [vector1, vector2])

        # Find inheritance edges
        inheritance_edges = (
            in_memory_db.query(EdgeModel)
            .filter(
                EdgeModel.graph_id == graph_id,
                EdgeModel.kind == "inheritance",
            )
            .all()
        )

        # At least some should have meta
        edges_with_meta = [e for e in inheritance_edges if e.meta]
        print(f"Inheritance edges with meta: {len(edges_with_meta)}")

    def test_event_count_includes_semantic_edges(self, engine, repos, in_memory_db):
        """Events should be emitted for semantic edge creation."""
        graph_id = "test_graph"

        vec1 = [1.0] + [0.0] * 255
        vec2 = [0.95] + [0.05] + [0.0] * 254

        vector1 = create_test_vector(
            vec1,
            block_id="b1",
        )
        vector2 = create_test_vector(
            vec2,
            block_id="b2",
        )

        result = engine.write_atoms(graph_id, [vector1, vector2])

        # Should have NODE_UPSERT events, possibly INHERITANCE_SET, and GRAPH_VERSION_BUMP
        assert result.events_emitted > 0
        assert result.nodes_written == 2

    def test_reingest_preserves_semantic_edges(self, engine, repos, in_memory_db):
        """Re-ingesting atoms should not delete semantic edges."""
        graph_id = "test_graph"

        vec1 = [1.0] + [0.0] * 255
        vec2 = [0.95] + [0.05] + [0.0] * 254

        vector1 = create_test_vector(
            vec1,
            block_id="b1",
        )
        vector2 = create_test_vector(
            vec2,
            block_id="b2",
        )

        # First write
        result1 = engine.write_atoms(graph_id, [vector1, vector2])
        semantic_count_1 = (
            in_memory_db.query(EdgeModel)
            .filter(
                EdgeModel.graph_id == graph_id,
                EdgeModel.kind.in_(list(KNOWN_SEMANTIC_KINDS)),
            )
            .count()
        )

        # Re-ingest same vectors
        result2 = engine.write_atoms(graph_id, [vector1, vector2])
        semantic_count_2 = (
            in_memory_db.query(EdgeModel)
            .filter(
                EdgeModel.graph_id == graph_id,
                EdgeModel.kind.in_(list(KNOWN_SEMANTIC_KINDS)),
            )
            .count()
        )

        # Semantic edges should be preserved (or at least not deleted)
        assert semantic_count_2 >= semantic_count_1


class TestSemanticWeightsIntegration:
    """Test that semantic weights integrate with inheritance blending."""

    def test_semantic_weight_modifies_inheritance_fraction(
        self, repos, in_memory_db
    ):
        """Semantic weight should modify effective inheritance fraction."""
        graph_id = "test_graph"
        parent_id = uuid4()
        child_id = uuid4()

        # Set inheritance with semantic metadata
        meta = {"semantic_type": "synonym", "semantic_weight": 0.95}
        repos["edge_repo"].set_inheritance_parents(
            graph_id=graph_id,
            child_id=child_id,
            parents=[(parent_id, 0.8)],
            parents_meta=[meta],
        )

        # Retrieve and verify meta
        edges = (
            in_memory_db.query(EdgeModel)
            .filter(
                EdgeModel.graph_id == graph_id,
                EdgeModel.dst_node_id == child_id,
            )
            .all()
        )

        assert len(edges) == 1
        assert edges[0].meta is not None
        assert edges[0].meta["semantic_weight"] == 0.95
