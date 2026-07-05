"""Deterministic lexical scorer for Representation V2."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Tuple

try:
    from faim.Faim_Native.encoding.representation_v2 import RepresentationV2
except (ImportError, RuntimeError):
    from encoding.representation_v2 import RepresentationV2


@dataclass(frozen=True)
class LexicalWeights:
    """Weights for additive lexical channels."""

    word: float = 0.35
    phrase: float = 0.20
    skip: float = 0.15
    entity: float = 0.15
    time: float = 0.10
    layout: float = 0.05
    semantic_phrase: float = 0.16
    concept: float = 0.12
    morphology: float = 0.08
    alias: float = 0.06
    translit: float = 0.05
    stem_family: float = 0.05
    relation: float = 0.04
    value: float = 0.04
    temporal: float = 0.03


DEFAULT_LEXICAL_WEIGHTS = LexicalWeights()


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _bm25_channel_score(
    query_counts: Mapping[str, int],
    doc_counts: Mapping[str, int],
    df_map: Mapping[str, int],
    *,
    doc_count: int,
    avg_len: float,
    doc_len: int,
    k1: float = 1.2,
    b: float = 0.75,
) -> float:
    if not query_counts or not doc_counts or doc_count <= 0:
        return 0.0

    denom_len = max(avg_len, 1.0)
    score = 0.0
    for term, q_tf in query_counts.items():
        f = float(doc_counts.get(term, 0))
        if f <= 0.0:
            continue
        df = float(df_map.get(term, 0))
        idf = math.log(1.0 + ((doc_count - df + 0.5) / (df + 0.5)))
        denom = f + k1 * (1.0 - b + b * (doc_len / denom_len))
        score += idf * ((f * (k1 + 1.0)) / max(denom, 1e-9)) * max(float(q_tf), 1.0)

    return score / (1.0 + score)


def _dice_score(
    query_counts: Mapping[str, int], doc_counts: Mapping[str, int]
) -> float:
    if not query_counts or not doc_counts:
        return 0.0
    q_total = sum(query_counts.values())
    d_total = sum(doc_counts.values())
    if q_total <= 0 or d_total <= 0:
        return 0.0
    overlap = 0
    for term, q_tf in query_counts.items():
        overlap += min(q_tf, int(doc_counts.get(term, 0)))
    return _clamp01((2.0 * overlap) / (q_total + d_total))


def _jaccard_score(query_terms: Iterable[str], doc_terms: Iterable[str]) -> float:
    q_set = set(query_terms)
    d_set = set(doc_terms)
    if not q_set or not d_set:
        return 0.0
    intersection = len(q_set & d_set)
    union = len(q_set | d_set)
    if union <= 0:
        return 0.0
    return _clamp01(intersection / union)


def compute_lexical_score(
    query_repr: RepresentationV2,
    doc_repr: RepresentationV2,
    stats_by_channel: Mapping[str, Mapping[str, object]],
    weights: LexicalWeights = DEFAULT_LEXICAL_WEIGHTS,
) -> Tuple[float, Dict[str, float]]:
    """Compute fused lexical score and normalized component breakdown."""
    word_stats = stats_by_channel.get("word", {})
    phrase_stats = stats_by_channel.get("phrase", {})
    skip_stats = stats_by_channel.get("skip", {})
    semantic_phrase_stats = stats_by_channel.get("semantic_phrase", {})
    concept_stats = stats_by_channel.get("concept", {})
    morphology_stats = stats_by_channel.get("morphology", {})

    word = _bm25_channel_score(
        query_repr.word_counts,
        doc_repr.word_counts,
        dict(word_stats.get("df_map", {})),  # type: ignore[call-overload]
        doc_count=int(word_stats.get("doc_count", 0)),  # type: ignore[call-overload]
        avg_len=float(word_stats.get("avg_len", 0.0)),
        doc_len=int(doc_repr.channel_lengths.get("word", 0)),
    )
    phrase_bm25 = _bm25_channel_score(
        query_repr.phrase_counts,
        doc_repr.phrase_counts,
        dict(phrase_stats.get("df_map", {})),  # type: ignore[call-overload]
        doc_count=int(phrase_stats.get("doc_count", 0)),  # type: ignore[call-overload]
        avg_len=float(phrase_stats.get("avg_len", 0.0)),
        doc_len=int(doc_repr.channel_lengths.get("phrase", 0)),
    )
    phrase_dice = _dice_score(query_repr.phrase_counts, doc_repr.phrase_counts)
    phrase = _clamp01((phrase_bm25 + phrase_dice) / 2.0)
    skip = _bm25_channel_score(
        query_repr.skip_counts,
        doc_repr.skip_counts,
        dict(skip_stats.get("df_map", {})),  # type: ignore[call-overload]
        doc_count=int(skip_stats.get("doc_count", 0)),  # type: ignore[call-overload]
        avg_len=float(skip_stats.get("avg_len", 0.0)),
        doc_len=int(doc_repr.channel_lengths.get("skip", 0)),
    )
    entity = _jaccard_score(query_repr.entity_tokens, doc_repr.entity_tokens)
    time = _jaccard_score(query_repr.time_tokens, doc_repr.time_tokens)
    layout = _jaccard_score(query_repr.layout_tokens, doc_repr.layout_tokens)
    semantic_phrase_bm25 = _bm25_channel_score(
        query_repr.semantic_phrase_counts or {},
        doc_repr.semantic_phrase_counts or {},
        dict(semantic_phrase_stats.get("df_map", {})),  # type: ignore[call-overload]
        doc_count=int(semantic_phrase_stats.get("doc_count", 0)),  # type: ignore[call-overload]
        avg_len=float(semantic_phrase_stats.get("avg_len", 0.0)),
        doc_len=int(doc_repr.channel_lengths.get("semantic_phrase", 0)),
    )
    semantic_phrase_dice = _dice_score(
        query_repr.semantic_phrase_counts or {},
        doc_repr.semantic_phrase_counts or {},
    )
    semantic_phrase = _clamp01((semantic_phrase_bm25 + semantic_phrase_dice) / 2.0)
    concept = _bm25_channel_score(
        query_repr.concept_counts or {},
        doc_repr.concept_counts or {},
        dict(concept_stats.get("df_map", {})),  # type: ignore[call-overload]
        doc_count=int(concept_stats.get("doc_count", 0)),  # type: ignore[call-overload]
        avg_len=float(concept_stats.get("avg_len", 0.0)),
        doc_len=int(doc_repr.channel_lengths.get("concept", 0)),
    )
    morphology = _bm25_channel_score(
        query_repr.morphology_counts or {},
        doc_repr.morphology_counts or {},
        dict(morphology_stats.get("df_map", {})),  # type: ignore[call-overload]
        doc_count=int(morphology_stats.get("doc_count", 0)),  # type: ignore[call-overload]
        avg_len=float(morphology_stats.get("avg_len", 0.0)),
        doc_len=int(doc_repr.channel_lengths.get("morphology", 0)),
    )
    alias = _jaccard_score(query_repr.alias_families, doc_repr.alias_families)
    translit = _jaccard_score(
        query_repr.transliterated_tokens, doc_repr.transliterated_tokens
    )
    stem_family = _jaccard_score(query_repr.stem_families, doc_repr.stem_families)
    relation = _jaccard_score(query_repr.relation_cues, doc_repr.relation_cues)
    value = _jaccard_score(query_repr.value_cues, doc_repr.value_cues)
    temporal = _jaccard_score(query_repr.temporal_cues, doc_repr.temporal_cues)

    score = (
        weights.word * word
        + weights.phrase * phrase
        + weights.skip * skip
        + weights.entity * entity
        + weights.time * time
        + weights.layout * layout
        + weights.semantic_phrase * semantic_phrase
        + weights.concept * concept
        + weights.morphology * morphology
        + weights.alias * alias
        + weights.translit * translit
        + weights.stem_family * stem_family
        + weights.relation * relation
        + weights.value * value
        + weights.temporal * temporal
    )
    components = {
        "word": round(word, 6),
        "phrase": round(phrase, 6),
        "skip": round(skip, 6),
        "entity": round(entity, 6),
        "time": round(time, 6),
        "layout": round(layout, 6),
        "semantic_phrase": round(semantic_phrase, 6),
        "concept": round(concept, 6),
        "morphology": round(morphology, 6),
        "alias": round(alias, 6),
        "translit": round(translit, 6),
        "stem_family": round(stem_family, 6),
        "relation": round(relation, 6),
        "value": round(value, 6),
        "temporal": round(temporal, 6),
    }
    return round(_clamp01(score), 6), components
