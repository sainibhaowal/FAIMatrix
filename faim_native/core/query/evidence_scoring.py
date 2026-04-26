"""Deterministic evidence span scoring for Phase 4 reranking."""

from __future__ import annotations

from typing import Dict, Sequence, Tuple

try:
    from faim.Faim_Native.core.query.proposition_extractor import PropositionAnalysis
except (ImportError, RuntimeError):
    from core.query.proposition_extractor import PropositionAnalysis


def _jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    left_set = {value for value in left if value}
    right_set = {value for value in right if value}
    if not left_set or not right_set:
        return 0.0
    union = left_set | right_set
    if not union:
        return 0.0
    return len(left_set & right_set) / len(union)


def _coverage(query_tokens: Sequence[str], doc_tokens: Sequence[str]) -> float:
    query = [token for token in query_tokens if token]
    if not query:
        return 0.0
    doc = set(token for token in doc_tokens if token)
    return sum(1 for token in query if token in doc) / max(len(query), 1)


def _locality(query_tokens: Sequence[str], doc_tokens: Sequence[str]) -> float:
    targets = [token for token in query_tokens if token]
    if not targets or not doc_tokens:
        return 0.0
    positions = [idx for idx, token in enumerate(doc_tokens) if token in targets]
    if not positions:
        return 0.0
    span = max(positions) - min(positions) + 1
    return max(0.0, 1.0 - (span - 1) / max(len(doc_tokens), 1))


def compute_evidence_span_score(
    query_analysis: PropositionAnalysis,
    doc_analysis: PropositionAnalysis,
) -> Tuple[float, Dict[str, float]]:
    """Compute bounded deterministic evidence score."""
    coverage = _coverage(query_analysis.content_tokens, doc_analysis.content_tokens)
    entity = _jaccard(query_analysis.entities, doc_analysis.entities)
    time = _jaccard(query_analysis.times, doc_analysis.times)
    value = _jaccard(query_analysis.values, doc_analysis.values)
    locality = _locality(query_analysis.content_tokens, doc_analysis.content_tokens)

    score = min(
        1.0,
        0.30 * coverage + 0.25 * entity + 0.15 * time + 0.15 * value + 0.15 * locality,
    )
    return round(score, 6), {
        "coverage": round(coverage, 6),
        "entity_overlap": round(entity, 6),
        "time_overlap": round(time, 6),
        "value_overlap": round(value, 6),
        "locality": round(locality, 6),
    }


__all__ = ["compute_evidence_span_score"]
