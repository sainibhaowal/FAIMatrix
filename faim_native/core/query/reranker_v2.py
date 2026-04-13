"""Deterministic Reranker V2 utilities for Phase 4."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Set, Tuple
from uuid import UUID

try:
    from faim.Faim_Native.core.query.evidence_scoring import compute_evidence_span_score
    from faim.Faim_Native.core.query.proposition_extractor import (
        PropositionAnalysis,
        extract_propositions,
        proposition_overlap,
        proposition_signature,
    )
    from faim.Faim_Native.encoding.representation_v2 import RepresentationV2
except (ImportError, RuntimeError):
    from core.query.evidence_scoring import compute_evidence_span_score
    from core.query.proposition_extractor import (
        PropositionAnalysis,
        extract_propositions,
        proposition_overlap,
        proposition_signature,
    )
    from encoding.representation_v2 import RepresentationV2


@dataclass(frozen=True)
class RerankerV2Candidate:
    """Minimal deterministic candidate bundle."""

    node_id: UUID
    created_at: Optional[datetime]
    representation: Optional[RepresentationV2]
    base_score: float


def _utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    left_set = {value for value in left if value}
    right_set = {value for value in right if value}
    if not left_set or not right_set:
        return 0.0
    union = left_set | right_set
    if not union:
        return 0.0
    return len(left_set & right_set) / len(union)


def score_reranker_v2(
    *,
    query_text: str,
    query_repr: RepresentationV2,
    candidates: Sequence[RerankerV2Candidate],
) -> Tuple[
    Dict[UUID, float],
    Dict[UUID, Dict[str, float]],
    Dict[UUID, Dict[str, object]],
    Set[UUID],
]:
    """Score candidates with proposition/evidence/entity/time signals."""
    query_analysis = extract_propositions(
        query_text,
        representation=query_repr,
    )

    totals: Dict[UUID, float] = {}
    components: Dict[UUID, Dict[str, float]] = {}
    explain: Dict[UUID, Dict[str, object]] = {}
    doc_analysis_map: Dict[UUID, PropositionAnalysis] = {}

    for candidate in candidates:
        doc_repr = candidate.representation
        doc_text = doc_repr.normalized_text if doc_repr else ""
        doc_analysis = extract_propositions(doc_text, representation=doc_repr) if doc_text else PropositionAnalysis(
            propositions=tuple(),
            entities=tuple(),
            relations=tuple(),
            values=tuple(),
            times=tuple(),
            content_tokens=tuple(),
        )
        doc_analysis_map[candidate.node_id] = doc_analysis

        entity_score = _jaccard(query_analysis.entities, doc_analysis.entities)
        time_score = _jaccard(query_analysis.times, doc_analysis.times)
        proposition_score = proposition_overlap(query_analysis, doc_analysis)
        evidence_score, evidence_components = compute_evidence_span_score(
            query_analysis,
            doc_analysis,
        )
        contradiction = 0.0

        total = min(
            1.0,
            0.25 * entity_score
            + 0.15 * time_score
            + 0.35 * proposition_score
            + 0.25 * evidence_score,
        )
        totals[candidate.node_id] = round(total, 6)
        components[candidate.node_id] = {
            "entity": round(entity_score, 6),
            "time": round(time_score, 6),
            "proposition": round(proposition_score, 6),
            "evidence_span": round(evidence_score, 6),
            "contradiction": contradiction,
        }
        explain[candidate.node_id] = {
            "query_signature": proposition_signature(query_analysis),
            "doc_signature": proposition_signature(doc_analysis),
            "query_propositions": [prop.__dict__ for prop in query_analysis.propositions[:4]],
            "doc_propositions": [prop.__dict__ for prop in doc_analysis.propositions[:4]],
            "evidence_components": evidence_components,
        }

    suppressed: Set[UUID] = set()
    ordered = sorted(candidates, key=lambda item: (-item.base_score, str(item.node_id)))
    for i, left in enumerate(ordered):
        if left.node_id in suppressed:
            continue
        left_analysis = doc_analysis_map[left.node_id]
        left_sig = proposition_signature(left_analysis)
        for right in ordered[i + 1 :]:
            if right.node_id in suppressed:
                continue
            right_analysis = doc_analysis_map[right.node_id]
            right_sig = proposition_signature(right_analysis)
            overlap = proposition_overlap(left_analysis, right_analysis)
            if overlap < 0.70:
                continue
            if left_sig != right_sig and left_sig[:2] != right_sig[:2]:
                continue

            left_values = set(left_analysis.values or ("",))
            right_values = set(right_analysis.values or ("",))
            left_times = set(left_analysis.times or ("",))
            right_times = set(right_analysis.times or ("",))
            value_conflict = bool(left_values and right_values and left_values != right_values)
            time_conflict = bool(left_times and right_times and left_times != right_times)
            left_entity_tail = {value for value in left_analysis.entities[1:] if value}
            right_entity_tail = {value for value in right_analysis.entities[1:] if value}
            if left_sig[:2] == right_sig[:2] and left_entity_tail and right_entity_tail:
                value_conflict = value_conflict or (left_entity_tail != right_entity_tail)

            winner = left
            loser = right
            if value_conflict or time_conflict:
                left_ts = _utc(left.created_at)
                right_ts = _utc(right.created_at)
                if left_ts and right_ts and right_ts > left_ts:
                    winner = right
                    loser = left
                elif totals.get(right.node_id, 0.0) > totals.get(left.node_id, 0.0):
                    winner = right
                    loser = left

            suppressed.add(loser.node_id)
            loser_components = components.setdefault(loser.node_id, {})
            loser_components["contradiction"] = 1.0 if (value_conflict or time_conflict) else 0.5
            explain.setdefault(loser.node_id, {})["dominance"] = {
                "winner_node_id": str(winner.node_id),
                "reason": "conflict" if (value_conflict or time_conflict) else "duplicate",
            }

    return totals, components, explain, suppressed


__all__ = ["RerankerV2Candidate", "score_reranker_v2"]
