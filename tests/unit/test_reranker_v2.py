"""Unit tests for Phase 4 deterministic reranker v2."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from faim_native.core.query.reranker_v2 import RerankerV2Candidate, score_reranker_v2
from faim_native.encoding.representation_v2 import build_representation_v2


def test_reranker_v2_suppresses_older_conflicting_candidate():
    query_repr = build_representation_v2("Atlas lives in Berlin in 2026")
    current_repr = build_representation_v2("Atlas lives in Berlin in 2026")
    older_repr = build_representation_v2("Atlas lives in Munich in 2026")

    newer_id = uuid4()
    older_id = uuid4()
    totals, components, explain, suppressed = score_reranker_v2(
        query_text="Atlas lives in Berlin in 2026",
        query_repr=query_repr,
        candidates=[
            RerankerV2Candidate(
                node_id=newer_id,
                created_at=datetime.now(timezone.utc),
                representation=current_repr,
                base_score=0.7,
            ),
            RerankerV2Candidate(
                node_id=older_id,
                created_at=datetime.now(timezone.utc) - timedelta(days=1),
                representation=older_repr,
                base_score=0.69,
            ),
        ],
    )

    assert totals[newer_id] > totals[older_id]
    assert older_id in suppressed
    assert components[older_id]["contradiction"] == 1.0
    assert explain[older_id]["dominance"]["reason"] == "conflict"
