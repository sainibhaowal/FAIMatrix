"""Deterministic confidence scoring for Phase 9."""

from __future__ import annotations

from typing import Sequence

from core.query.span_selection import CandidateSpan


def compute_confidence(
    *,
    spans: Sequence[CandidateSpan],
    contradiction_count: int = 0,
) -> float:
    if not spans:
        return 0.0
    avg_support = sum(span.span_score for span in spans) / len(spans)
    breadth = min(1.0, len(spans) / 3.0)
    temporal = sum(1.0 for span in spans if span.temporal_status != "HISTORICAL") / max(
        len(spans), 1
    )
    contradiction_penalty = min(0.5, 0.15 * contradiction_count)
    confidence = max(
        0.0,
        min(
            1.0,
            0.45 * avg_support
            + 0.30 * breadth
            + 0.25 * temporal
            - contradiction_penalty,
        ),
    )
    return round(confidence, 6)


__all__ = ["compute_confidence"]
