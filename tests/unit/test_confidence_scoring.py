from __future__ import annotations

from faim_native.core.query.confidence_scoring import compute_confidence
from faim_native.core.query.span_selection import CandidateSpan


def test_confidence_scoring_penalizes_contradictions():
    spans = [
        CandidateSpan("n1", "r1", "b1", {}, "Atlas lives in Berlin.", 0.9, 0, "CURRENT", 0.95),
        CandidateSpan("n2", "r2", "b2", {}, "Atlas lived in Munich.", 0.6, 1, "HISTORICAL", 0.80),
    ]
    high = compute_confidence(spans=spans, contradiction_count=0)
    low = compute_confidence(spans=spans, contradiction_count=1)
    assert low < high
