"""Phase 8: Semantic edges in EdgeRepo unit tests.

Tests for semantic edge storage, idempotency, meta handling, and list operations.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from faim_native.core.operators.semantic_typing import KNOWN_SEMANTIC_KINDS
from faim_native.store.pg.models_faim import Base, EdgeModel, NodeModel
from faim_native.store.pg.repos.edge_repo import EdgeRepo
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
def edge_repo(in_memory_db):
    """Create EdgeRepo with test session."""
    return EdgeRepo(session=in_memory_db, tenant_id="test_tenant")


@pytest.fixture
def node_repo(in_memory_db):
    """Create NodeRepo with test session."""
    return NodeRepo(session=in_memory_db, tenant_id="test_tenant")


class TestAddSemanticEdge:
    """Test semantic edge creation and upsert behavior."""

    def test_add_semantic_edge_synonym(self, edge_repo, in_memory_db):
        """Create a semantic edge with synonym type."""
        from uuid import uuid4

        graph_id = "test_graph"
        src_id = uuid4()
        dst_id = uuid4()

        edge_id = edge_repo.add_semantic_edge(
            graph_id=graph_id,
            src_node_id=src_id,
            dst_node_id=dst_id,
            semantic_type="synonym",
            semantic_weight=0.95,
            meta=None,
        )

        # Verify edge was created
        assert edge_id is not None

        # Retrieve and verify
        edges = (
            in_memory_db.query(EdgeModel)
            .filter(
                EdgeModel.graph_id == graph_id,
                EdgeModel.kind == "synonym",
            )
            .all()
        )
        assert len(edges) == 1
        assert edges[0].edge_id == edge_id
        assert edges[0].kind == "synonym"
        assert abs(edges[0].weight / 1e9 - 0.95) < 1e-6

    def test_add_semantic_edge_idempotency(self, edge_repo, in_memory_db):
        """Adding same semantic edge twice should update, not duplicate."""
        from uuid import uuid4

        graph_id = "test_graph"
        src_id = uuid4()
        dst_id = uuid4()

        edge_id_1 = edge_repo.add_semantic_edge(
            graph_id=graph_id,
            src_node_id=src_id,
            dst_node_id=dst_id,
            semantic_type="hypernym",
            semantic_weight=0.80,
            meta=None,
        )

        edge_id_2 = edge_repo.add_semantic_edge(
            graph_id=graph_id,
            src_node_id=src_id,
            dst_node_id=dst_id,
            semantic_type="hypernym",
            semantic_weight=0.85,  # Updated weight
            meta=None,
        )

        # Edge ID should be the same (same (src, dst, kind) tuple)
        # Count should be 1
        edges = (
            in_memory_db.query(EdgeModel)
            .filter(
                EdgeModel.graph_id == graph_id,
                EdgeModel.kind == "hypernym",
            )
            .all()
        )
        assert len(edges) == 1
        assert abs(edges[0].weight / 1e9 - 0.85) < 1e-6  # Updated weight

    def test_add_multiple_semantic_types_same_pair(self, edge_repo, in_memory_db):
        """Different semantic types can exist between same pair."""
        from uuid import uuid4

        graph_id = "test_graph"
        src_id = uuid4()
        dst_id = uuid4()

        # Add synonym edge
        edge_repo.add_semantic_edge(
            graph_id=graph_id,
            src_node_id=src_id,
            dst_node_id=dst_id,
            semantic_type="synonym",
            semantic_weight=0.95,
            meta=None,
        )

        # Add hypernym edge (different kind)
        edge_repo.add_semantic_edge(
            graph_id=graph_id,
            src_node_id=src_id,
            dst_node_id=dst_id,
            semantic_type="hypernym",
            semantic_weight=0.80,
            meta=None,
        )

        # Both should exist
        edges = (
            in_memory_db.query(EdgeModel)
            .filter(
                EdgeModel.graph_id == graph_id,
                EdgeModel.src_node_id == src_id,
                EdgeModel.dst_node_id == dst_id,
            )
            .all()
        )
        assert len(edges) == 2
        kinds = {e.kind for e in edges}
        assert "synonym" in kinds
        assert "hypernym" in kinds


class TestSetInheritanceParentsWithMeta:
    """Test inheritance edge creation with semantic metadata (Layer A)."""

    def test_set_inheritance_with_semantic_meta(self, edge_repo, in_memory_db):
        """Setting inheritance parents with meta should store metadata."""
        from uuid import uuid4

        graph_id = "test_graph"
        child_id = uuid4()
        parent_id_1 = uuid4()
        parent_id_2 = uuid4()

        parents = [(parent_id_1, 0.6), (parent_id_2, 0.4)]
        parents_meta = [
            {"semantic_type": "synonym", "semantic_weight": 0.95},
            {"semantic_type": "hypernym", "semantic_weight": 0.80},
        ]

        edge_ids = edge_repo.set_inheritance_parents(
            graph_id=graph_id,
            child_id=child_id,
            parents=parents,
            parents_meta=parents_meta,
        )

        assert len(edge_ids) == 2

        # Verify edges have correct metadata
        edges = (
            in_memory_db.query(EdgeModel)
            .filter(
                EdgeModel.graph_id == graph_id,
                EdgeModel.dst_node_id == child_id,
                EdgeModel.kind == "inheritance",
            )
            .all()
        )

        assert len(edges) == 2
        meta_by_parent = {e.src_node_id: e.meta for e in edges}

        assert meta_by_parent[parent_id_1]["semantic_type"] == "synonym"
        assert meta_by_parent[parent_id_2]["semantic_type"] == "hypernym"

    def test_set_inheritance_parents_deletes_only_inheritance(
        self, edge_repo, in_memory_db
    ):
        """Re-ingesting should delete only inheritance edges, not semantic edges."""
        from uuid import uuid4

        graph_id = "test_graph"
        child_id = uuid4()
        parent_id = uuid4()

        # Create initial inheritance edge
        edge_repo.set_inheritance_parents(
            graph_id=graph_id,
            child_id=child_id,
            parents=[(parent_id, 1.0)],
        )

        # Create a semantic edge pointing to the same child
        edge_repo.add_semantic_edge(
            graph_id=graph_id,
            src_node_id=parent_id,
            dst_node_id=child_id,
            semantic_type="synonym",
            semantic_weight=0.95,
            meta=None,
        )

        # Re-ingest: set new parents (should delete old inheritance, keep semantic)
        other_parent_id = uuid4()
        edge_repo.set_inheritance_parents(
            graph_id=graph_id,
            child_id=child_id,
            parents=[(other_parent_id, 1.0)],
        )

        # Verify: old inheritance edge deleted, but semantic edge remains
        inheritance_edges = (
            in_memory_db.query(EdgeModel)
            .filter(
                EdgeModel.graph_id == graph_id,
                EdgeModel.dst_node_id == child_id,
                EdgeModel.kind == "inheritance",
            )
            .all()
        )

        semantic_edges = (
            in_memory_db.query(EdgeModel)
            .filter(
                EdgeModel.graph_id == graph_id,
                EdgeModel.dst_node_id == child_id,
                EdgeModel.kind == "synonym",
            )
            .all()
        )

        assert len(inheritance_edges) == 1
        assert inheritance_edges[0].src_node_id == other_parent_id

        assert len(semantic_edges) == 1
        assert semantic_edges[0].kind == "synonym"


class TestListSemanticNeighbors:
    """Test batch querying of semantic edges."""

    def test_list_semantic_neighbors_no_edges(self, edge_repo):
        """List semantic neighbors when none exist should return empty."""
        from uuid import uuid4

        node_ids = [uuid4()]
        neighbors = edge_repo.list_semantic_neighbors(
            graph_id="test_graph",
            node_ids=node_ids,
        )

        assert len(neighbors) == 0

    def test_list_semantic_neighbors_with_edges(self, edge_repo, in_memory_db):
        """List semantic neighbors should return edges touching given nodes."""
        from uuid import uuid4

        graph_id = "test_graph"
        node_a = uuid4()
        node_b = uuid4()
        node_c = uuid4()

        # Create semantic edges
        edge_repo.add_semantic_edge(
            graph_id=graph_id,
            src_node_id=node_a,
            dst_node_id=node_b,
            semantic_type="synonym",
            semantic_weight=0.95,
            meta=None,
        )

        edge_repo.add_semantic_edge(
            graph_id=graph_id,
            src_node_id=node_b,
            dst_node_id=node_c,
            semantic_type="hypernym",
            semantic_weight=0.80,
            meta=None,
        )

        # Query neighbors of [node_a, node_b]
        neighbors = edge_repo.list_semantic_neighbors(
            graph_id=graph_id,
            node_ids=[node_a, node_b],
        )

        # Should find both edges (both touch node_a or node_b)
        assert len(neighbors) >= 2

        # Verify edge connectivity
        edge_pairs = {(e.src_node_id, e.dst_node_id) for e in neighbors}
        assert (node_a, node_b) in edge_pairs or (node_b, node_c) in edge_pairs

    def test_list_semantic_neighbors_filters_by_kind(self, edge_repo, in_memory_db):
        """List semantic neighbors should filter by kind when provided."""
        from uuid import uuid4

        graph_id = "test_graph"
        node_a = uuid4()
        node_b = uuid4()

        # Create edges of different kinds
        edge_repo.add_semantic_edge(
            graph_id=graph_id,
            src_node_id=node_a,
            dst_node_id=node_b,
            semantic_type="synonym",
            semantic_weight=0.95,
            meta=None,
        )

        edge_repo.add_semantic_edge(
            graph_id=graph_id,
            src_node_id=node_a,
            dst_node_id=node_b,
            semantic_type="hypernym",
            semantic_weight=0.80,
            meta=None,
        )

        # Query only synonym edges
        neighbors = edge_repo.list_semantic_neighbors(
            graph_id=graph_id,
            node_ids=[node_a],
            kinds=["synonym"],
        )

        # Should find only synonym edge
        assert all(e.kind == "synonym" for e in neighbors)
