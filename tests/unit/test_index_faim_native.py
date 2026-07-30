"""Stage-6 Tests: Index FAIM-Native.

Tests for index layer:
- test_index_point_id_is_deterministic
- test_index_dim_matches_vector_schema_256
- test_index_fallback_bruteforce_matches_expected_topk
- test_index_results_sorted_stably_with_ties
"""

import unittest


class TestIndexFAIMNative(unittest.TestCase):
    """Tests for FAIM-native index layer."""

    def test_index_dim_matches_vector_schema_256(self):
        """Index dimension must be 256 from encoding.vector_schema."""
        from encoding.vector_schema import VECTOR_DIMENSION as ENCODING_DIM
        from index.qdrant_collections import VECTOR_DIMENSION

        self.assertEqual(VECTOR_DIMENSION, 256)
        self.assertEqual(ENCODING_DIM, 256)
        self.assertEqual(VECTOR_DIMENSION, ENCODING_DIM)

    def test_index_point_id_is_deterministic(self):
        """Point IDs must be deterministic (not Python hash())."""
        from index.qdrant_collections import point_id_from_node_id

        node_id = "abc123-def456-ghi789"

        # Same input = same output
        id1 = point_id_from_node_id(node_id)
        id2 = point_id_from_node_id(node_id)

        self.assertEqual(id1, id2)

        # Different input = different output
        id3 = point_id_from_node_id("different-node-id")
        self.assertNotEqual(id1, id3)

    def test_index_point_id_not_python_hash(self):
        """Point ID must NOT use Python hash() which is non-deterministic."""
        import inspect

        from index.qdrant_collections import point_id_from_node_id

        # Get source and extract function body (skip docstring)
        source = inspect.getsource(point_id_from_node_id)

        # Remove docstring to avoid false positive
        # The docstring mentions "DO NOT use Python hash()" as a warning
        lines = source.split("\n")
        in_docstring = False
        body_lines = []
        for line in lines:
            if '"""' in line:
                in_docstring = not in_docstring
                if not in_docstring:
                    continue
            if not in_docstring and "def " not in line:
                body_lines.append(line)

        body = "\n".join(body_lines)

        # Check that function body doesn't use hash()
        # It should just return node_id directly
        self.assertNotIn("= hash(", body)
        self.assertIn("return node_id", source)

    def test_index_fallback_bruteforce_matches_expected_topk(self):
        """Brute-force fallback must return correct top-k results."""
        from index.qdrant_index import BruteForceIndex

        index = BruteForceIndex()
        graph_id = "test_graph"

        # Add some vectors
        index.add(graph_id, "node1", (1.0, 0.0, 0.0))
        index.add(graph_id, "node2", (0.9, 0.1, 0.0))
        index.add(graph_id, "node3", (0.0, 1.0, 0.0))

        # Query similar to node1
        query = (1.0, 0.0, 0.0)
        results = index.top_k(graph_id, query, k=2)

        # Should return node1 first (exact match), then node2 (similar)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0], "node1")
        self.assertAlmostEqual(results[0][1], 1.0, places=5)

    def test_index_results_sorted_stably_with_ties(self):
        """Results must be sorted by (-score, node_id) for stable ties."""
        from index.qdrant_index import BruteForceIndex

        index = BruteForceIndex()
        graph_id = "test_graph"

        # Add vectors with same content (same score when queried)
        vec = (0.5, 0.5, 0.0)
        index.add(graph_id, "node_z", vec)
        index.add(graph_id, "node_a", vec)
        index.add(graph_id, "node_m", vec)

        # Query with same vector (all scores = 1.0)
        results = index.top_k(graph_id, vec, k=3)

        # All have same score, so should be sorted by node_id (ascending)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0][0], "node_a")
        self.assertEqual(results[1][0], "node_m")
        self.assertEqual(results[2][0], "node_z")

    def test_collection_name_format(self):
        """Collection name must follow faim_<project_id> format."""
        from uuid import UUID

        from index.qdrant_collections import collection_name

        project_id = UUID("12345678-1234-5678-1234-567812345678")
        name = collection_name(project_id)

        self.assertTrue(name.startswith("faim_"))
        self.assertIn("12345678", name)

    def test_faim_index_requires_256_dim(self):
        """FAIMIndex must reject non-256 dimensions."""
        from uuid import UUID

        from index.qdrant_index import FAIMIndex

        project_id = UUID("12345678-1234-5678-1234-567812345678")

        # 256 should work
        index = FAIMIndex(project_id, dim=256)
        self.assertEqual(index.dim, 256)

        # Other dims should raise
        with self.assertRaises(ValueError):
            FAIMIndex(project_id, dim=384)

        with self.assertRaises(ValueError):
            FAIMIndex(project_id, dim=64)

    def test_create_payload_has_required_fields(self):
        """create_payload must include all required fields."""
        from index.qdrant_collections import (
            FIELD_GRAPH_ID,
            FIELD_KIND,
            FIELD_LEVEL,
            FIELD_NODE_ID,
            create_payload,
        )

        payload = create_payload(
            graph_id="graph_123",
            node_id="node_456",
            level=2,
            kind="macro",
        )

        self.assertEqual(payload[FIELD_GRAPH_ID], "graph_123")
        self.assertEqual(payload[FIELD_NODE_ID], "node_456")
        self.assertEqual(payload[FIELD_LEVEL], 2)
        self.assertEqual(payload[FIELD_KIND], "macro")


if __name__ == "__main__":
    unittest.main()
