"""Unit tests for deterministic graph hash."""

from __future__ import annotations

import sys
from pathlib import Path

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.dynamics.nativegraph import compute_graph_hash  # noqa: E402


class TestGraphHashReceipt:
    """Unit tests for deterministic graph hash."""

    def test_empty_graph_hash(self):
        """Empty graph should have consistent hash."""
        hash1 = compute_graph_hash([], [])
        hash2 = compute_graph_hash([], [])

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_same_nodes_same_hash(self):
        """Same nodes should produce same hash."""
        nodes = [
            ("node1", "hash1", 0, 0.0),
            ("node2", "hash2", 0, 0.1),
        ]

        hash1 = compute_graph_hash(nodes, [])
        hash2 = compute_graph_hash(nodes, [])

        assert hash1 == hash2

    def test_node_order_doesnt_matter(self):
        """Node order should not affect hash (sorted internally)."""
        nodes1 = [
            ("node1", "hash1", 0, 0.0),
            ("node2", "hash2", 0, 0.1),
        ]
        nodes2 = [
            ("node2", "hash2", 0, 0.1),
            ("node1", "hash1", 0, 0.0),
        ]

        hash1 = compute_graph_hash(nodes1, [])
        hash2 = compute_graph_hash(nodes2, [])

        assert hash1 == hash2

    def test_different_nodes_different_hash(self):
        """Different nodes should produce different hash."""
        nodes1 = [("node1", "hash1", 0, 0.0)]
        nodes2 = [("node2", "hash2", 0, 0.0)]

        hash1 = compute_graph_hash(nodes1, [])
        hash2 = compute_graph_hash(nodes2, [])

        assert hash1 != hash2

    def test_edges_included_in_hash(self):
        """Edges should affect hash."""
        nodes = [("node1", "hash1", 0, 0.0)]
        edges = [("edge1", "node0", "node1", "inheritance", 1.0)]

        hash_with_edges = compute_graph_hash(nodes, edges)
        hash_without_edges = compute_graph_hash(nodes, [])

        assert hash_with_edges != hash_without_edges

    def test_edge_order_doesnt_matter(self):
        """Edge order should not affect hash."""
        nodes = [("node1", "hash1", 0, 0.0)]
        edges1 = [
            ("edge1", "a", "b", "inheritance", 0.5),
            ("edge2", "b", "c", "inheritance", 0.5),
        ]
        edges2 = [
            ("edge2", "b", "c", "inheritance", 0.5),
            ("edge1", "a", "b", "inheritance", 0.5),
        ]

        hash1 = compute_graph_hash(nodes, edges1)
        hash2 = compute_graph_hash(nodes, edges2)

        assert hash1 == hash2

    def test_residual_affects_hash(self):
        """Different residual should produce different hash."""
        nodes1 = [("node1", "hash1", 0, 0.0)]
        nodes2 = [("node1", "hash1", 0, 0.5)]

        hash1 = compute_graph_hash(nodes1, [])
        hash2 = compute_graph_hash(nodes2, [])

        assert hash1 != hash2

    def test_level_affects_hash(self):
        """Different level should produce different hash."""
        nodes1 = [("node1", "hash1", 0, 0.0)]
        nodes2 = [("node1", "hash1", 1, 0.0)]

        hash1 = compute_graph_hash(nodes1, [])
        hash2 = compute_graph_hash(nodes2, [])

        assert hash1 != hash2
