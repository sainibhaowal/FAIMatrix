"""Unit tests for antisym idempotence."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID, uuid4

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.antisym import (  # noqa: E402
    check_merge_idempotence,
    find_merge_candidates,
    merge_vectors,
    opposition_score,
    select_winner,
    should_merge,
)


class TestAntisymIdempotence:
    """Unit tests for antisym idempotence."""

    def test_merge_same_pair_same_result(self):
        """Merging same pair should give same result."""
        a_id = UUID("00000000-0000-0000-0000-000000000001")
        b_id = UUID("00000000-0000-0000-0000-000000000002")
        a_hash = "aaa111"
        b_hash = "bbb222"

        result1 = merge_vectors(a_id, b_id, a_hash, b_hash, 0.98)
        result2 = merge_vectors(a_id, b_id, a_hash, b_hash, 0.98)

        assert result1.winner_id == result2.winner_id
        assert result1.loser_id == result2.loser_id

    def test_idempotence_check_detects_merged(self):
        """check_merge_idempotence should detect already merged."""
        merged_ids = {UUID("00000000-0000-0000-0000-000000000001")}
        a_id = UUID("00000000-0000-0000-0000-000000000001")
        b_id = UUID("00000000-0000-0000-0000-000000000002")

        assert check_merge_idempotence(merged_ids, a_id, b_id) is True

    def test_idempotence_check_allows_fresh(self):
        """check_merge_idempotence should allow fresh pair."""
        merged_ids = set()
        a_id = UUID("00000000-0000-0000-0000-000000000001")
        b_id = UUID("00000000-0000-0000-0000-000000000002")

        assert check_merge_idempotence(merged_ids, a_id, b_id) is False

    def test_winner_selection_deterministic(self):
        """Winner selection should be deterministic."""
        a_id = uuid4()
        b_id = uuid4()
        a_hash = "aaa"
        b_hash = "bbb"

        winner1, loser1 = select_winner(a_id, b_id, a_hash, b_hash)
        winner2, loser2 = select_winner(a_id, b_id, a_hash, b_hash)

        assert winner1 == winner2
        assert loser1 == loser2

    def test_winner_is_lower_hash(self):
        """Winner should have lower hash."""
        a_id = uuid4()
        b_id = uuid4()

        winner, loser = select_winner(a_id, b_id, "aaa", "bbb")
        assert winner == a_id

        winner, loser = select_winner(a_id, b_id, "zzz", "aaa")
        assert winner == b_id

    def test_opposition_score_symmetric(self):
        """Opposition score should be symmetric."""
        v1 = [0.5] * 256
        v2 = [0.6] * 256

        score1 = opposition_score(v1, v2)
        score2 = opposition_score(v2, v1)

        assert abs(score1 - score2) < 1e-9

    def test_should_merge_threshold_exact(self):
        """should_merge should handle exact threshold."""
        assert should_merge(0.95, 0.95) is True
        assert should_merge(0.9499999, 0.95) is False

    def test_find_merge_candidates_sorted(self):
        """find_merge_candidates should return sorted by score."""
        target = [0.5] * 256
        candidates = [
            (uuid4(), "hash1", [0.4] * 256),
            (uuid4(), "hash2", [0.5] * 256),  # Most similar
            (uuid4(), "hash3", [0.3] * 256),
        ]

        results = find_merge_candidates(target, candidates, threshold=0.0)

        if len(results) >= 2:
            assert results[0][2] >= results[1][2]
