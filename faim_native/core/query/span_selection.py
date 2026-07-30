"""Deterministic extractive span selection for Phase 9."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Sequence

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


@dataclass(frozen=True)
class CandidateSpan:
    node_id: str
    raw_id: str
    block_id: str
    anchor: Dict[str, object] | None
    text: str
    span_score: float
    source_rank: int
    temporal_status: str | None
    score: float


def _tokenize(text: str) -> List[str]:
    return [token for token in re.findall(r"[A-Za-z0-9_:-]+", text.lower()) if token]


def _split_sentences(text: str) -> List[str]:
    chunks = [
        chunk.strip() for chunk in _SENTENCE_SPLIT_RE.split(text or "") if chunk.strip()
    ]
    if not chunks and text.strip():
        return [text.strip()]
    return chunks


def _jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def _score_span(
    query_text: str, span_text: str, source_rank: int, temporal_status: str | None
) -> float:
    query_tokens = _tokenize(query_text)
    span_tokens = _tokenize(span_text)
    query_overlap = _jaccard(query_tokens, span_tokens)
    source_rank_score = max(0.0, 1.0 - 0.1 * source_rank)
    temporal_consistency = 1.0 if temporal_status != "HISTORICAL" else 0.35
    score = min(
        1.0,
        0.45 * query_overlap + 0.30 * source_rank_score + 0.25 * temporal_consistency,
    )
    return round(score, 6)


def select_supporting_spans(
    *,
    query_text: str,
    ranked_results: Sequence[Dict[str, object]],
    limit: int = 5,
) -> List[CandidateSpan]:
    spans: List[CandidateSpan] = []
    for source_rank, item in enumerate(ranked_results):
        text = str(item.get("answer_text") or "").strip()
        if not text:
            continue
        for sentence in _split_sentences(text)[:4]:
            span_score = _score_span(
                query_text, sentence, source_rank, item.get("temporal_status")
            )
            if span_score <= 0.0:
                continue
            evidence = dict(item.get("evidence") or {})  # type: ignore[call-overload]
            raw_id = str(evidence.get("raw_id") or item.get("raw_id") or "")
            block_id = str(evidence.get("block_id") or item.get("block_id") or "")
            anchor = evidence.get("anchor") or item.get("anchor")
            spans.append(
                CandidateSpan(
                    node_id=str(item["node_id"]),
                    raw_id=raw_id,
                    block_id=block_id,
                    anchor=anchor,
                    text=sentence,
                    span_score=span_score,
                    source_rank=source_rank,
                    temporal_status=item.get("temporal_status"),
                    score=float(item.get("score", 0.0)),
                )
            )
    spans.sort(
        key=lambda item: (-item.span_score, item.source_rank, item.node_id, item.text)
    )
    return spans[:limit]


__all__ = ["CandidateSpan", "select_supporting_spans"]
