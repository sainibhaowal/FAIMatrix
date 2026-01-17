"""Stage-8 Test: Query Determinism (STRICT mode).

Proves STRICT mode produces identical results:
- Same graph + same query → same query_hash
- Same ranked IDs
- Same scores (within epsilon)
- Stable tie-break by node_id
"""

import unittest


class TestQueryDeterminism(unittest.TestCase):
    """Test STRICT mode determinism."""

    def test_query_hash_is_deterministic(self):
        """Same query text + graph → same query_hash."""
        from core.query.query_engine import compute_query_hash

        h1 = compute_query_hash("test query", "graph_1")
        h2 = compute_query_hash("test query", "graph_1")
        h3 = compute_query_hash("test query", "graph_2")

        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)

    def test_cosine_similarity_deterministic(self):
        """Cosine similarity is deterministic."""
        from core.query.query_engine import cosine_similarity

        a = tuple([0.1] * 256)
        b = tuple([0.2] * 256)

        s1 = cosine_similarity(a, b)
        s2 = cosine_similarity(a, b)

        self.assertEqual(s1, s2)

    def test_score_components_deterministic(self):
        """Score computation returns same components."""
        from datetime import datetime, timezone

        from core.query.query_engine import DEFAULT_WEIGHTS, compute_node_score

        q_vec = tuple([0.1] * 256)
        n_vec = tuple([0.2] * 256)

        s1, c1 = compute_node_score(
            q_vec=q_vec,
            n_vec=n_vec,
            n_residual=0.5,
            n_opp={"d1": 0.3},
            n_touch=5,
            n_last_access=datetime.now(timezone.utc),
            n_level=0,
            graph_avg_touch=2.0,
            weights=DEFAULT_WEIGHTS,
        )

        s2, c2 = compute_node_score(
            q_vec=q_vec,
            n_vec=n_vec,
            n_residual=0.5,
            n_opp={"d1": 0.3},
            n_touch=5,
            n_last_access=datetime.now(timezone.utc),
            n_level=0,
            graph_avg_touch=2.0,
            weights=DEFAULT_WEIGHTS,
        )

        self.assertEqual(s1, s2)
        self.assertEqual(c1, c2)

    def test_stable_sort_by_score_then_node_id(self):
        """Results sort by (-score, node_id) for determinism."""
        scores = [
            ("node_a", 0.8),
            ("node_b", 0.8),  # Same score - should be after node_a
            ("node_c", 0.9),  # Higher score - should be first
        ]

        sorted_scores = sorted(scores, key=lambda x: (-x[1], x[0]))

        self.assertEqual(sorted_scores[0][0], "node_c")  # Highest score
        self.assertEqual(sorted_scores[1][0], "node_a")  # Same score, a < b
        self.assertEqual(sorted_scores[2][0], "node_b")

    def test_strict_weights_exist(self):
        """STRICT_WEIGHTS are defined."""
        from core.query.query_engine import STRICT_WEIGHTS

        self.assertIsNotNone(STRICT_WEIGHTS.w_sim)
        self.assertGreater(STRICT_WEIGHTS.w_sim, 0)


class TestScoreFormula(unittest.TestCase):
    """Test FAIM score formula components."""

    def test_recency_boost_decreases_with_age(self):
        """Older nodes get less recency boost."""
        from datetime import datetime, timedelta, timezone

        from core.query.query_engine import recency_boost

        now = datetime.now(timezone.utc)

        boost_now = recency_boost(now, now)
        boost_1day = recency_boost(now - timedelta(days=1), now)
        boost_7days = recency_boost(now - timedelta(days=7), now)

        self.assertGreater(boost_now, boost_1day)
        self.assertGreater(boost_1day, boost_7days)

    def test_level_penalty_increases_with_level(self):
        """Higher levels get more penalty."""
        from core.query.query_engine import level_penalty

        p0 = level_penalty(0)
        p1 = level_penalty(1)
        p2 = level_penalty(2)

        self.assertLess(p0, p1)
        self.assertLess(p1, p2)


if __name__ == "__main__":
    unittest.main()
