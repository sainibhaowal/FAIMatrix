"""Deterministic extractive answer synthesis for Phase 9."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

from core.query.confidence_scoring import compute_confidence
from core.query.quote_extraction import extract_quotes
from core.query.span_selection import CandidateSpan, select_supporting_spans


@dataclass(frozen=True)
class SynthesizedAnswer:
    direct_answer: str
    supporting_spans: List[Dict[str, object]]
    citations: List[Dict[str, object]]
    contradiction_notes: List[str]
    confidence: float
    provenance: Dict[str, object]
    quotes: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "direct_answer": self.direct_answer,
            "supporting_spans": self.supporting_spans,
            "citations": self.citations,
            "contradiction_notes": self.contradiction_notes,
            "confidence": self.confidence,
            "provenance": self.provenance,
            "quotes": self.quotes,
        }


def _build_direct_answer(spans: Sequence[CandidateSpan]) -> str:
    if not spans:
        return ""
    return spans[0].text


def _collect_contradictions(ranked_results: Sequence[Dict[str, object]]) -> List[str]:
    notes: List[str] = []
    signatures = []
    for item in ranked_results[:5]:
        explain = dict(item.get("phase4_explain") or {})  # type: ignore[call-overload]
        doc_props = explain.get("doc_propositions") or []
        if not doc_props:
            continue
        first = doc_props[0]
        signatures.append(
            (
                str(first.get("entity", "")),
                str(first.get("relation", "")),
                str(first.get("value", "")),
                str(first.get("time", "")),
                str(item.get("temporal_status") or ""),
            )
        )
    seen = {}
    for entity, relation, value, time_value, temporal in signatures:
        key = (entity, relation)
        bucket = seen.setdefault(key, set())
        if value or time_value:
            bucket.add((value, time_value, temporal))
    for key, values in sorted(seen.items()):
        if len(values) > 1:
            entity, relation = key
            notes.append(
                f"Conflicting evidence for {entity or 'entity'} / {relation or 'relation'}"
            )
    return notes


def synthesize_answer(
    *,
    query_text: str,
    ranked_results: Sequence[Dict[str, object]],
    query_hash: str,
    graph_id: str,
) -> Dict[str, object]:
    spans = select_supporting_spans(
        query_text=query_text, ranked_results=ranked_results, limit=5
    )
    contradiction_notes = _collect_contradictions(ranked_results)
    citations = [
        {
            "node_id": span.node_id,
            "raw_id": span.raw_id,
            "block_id": span.block_id,
            "anchor": span.anchor,
            "score": span.span_score,
        }
        for span in spans
    ]
    supporting_spans = [
        {
            "node_id": span.node_id,
            "text": span.text,
            "score": span.span_score,
            "temporal_status": span.temporal_status,
        }
        for span in spans
    ]
    confidence = compute_confidence(
        spans=spans, contradiction_count=len(contradiction_notes)
    )
    quotes = extract_quotes(spans)
    answer = SynthesizedAnswer(
        direct_answer=_build_direct_answer(spans),
        supporting_spans=supporting_spans,
        citations=citations,
        contradiction_notes=contradiction_notes,
        confidence=confidence,
        provenance={
            "query_hash": query_hash,
            "graph_id": graph_id,
            "span_count": len(spans),
        },
        quotes=quotes,
    )
    return answer.to_dict()


__all__ = ["SynthesizedAnswer", "synthesize_answer"]
