"""Unit tests for Phase 4 evidence span scoring."""

from __future__ import annotations

from faim_native.core.query.evidence_scoring import compute_evidence_span_score
from faim_native.core.query.proposition_extractor import extract_propositions


def test_evidence_span_scores_matching_doc_higher():
    query = extract_propositions("Atlas lives in Berlin in 2026")
    doc_match = extract_propositions(
        "Atlas resides in Berlin in 2026 and revenue grows"
    )
    doc_other = extract_propositions("Warehouse inventory changed yesterday")

    score_match, comp_match = compute_evidence_span_score(query, doc_match)
    score_other, comp_other = compute_evidence_span_score(query, doc_other)

    assert score_match > score_other
    assert comp_match["coverage"] >= comp_other["coverage"]
    assert 0.0 <= score_match <= 1.0
