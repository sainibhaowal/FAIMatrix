"""FAIM-native symbolic late interaction scorer.

This borrows the *interaction pattern* from late-interaction retrieval:
query-side fine-grained units interact cheaply with precomputed document-side
units and aggregate via max-style matching. The implementation stays fully
deterministic and FAIM-native by using symbolic lexical-semantic units instead
of neural token embeddings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

try:
    from faim.Faim_Native.encoding.representation_v2 import RepresentationV2
    from faim.Faim_Native.lexical.transliteration import transliterate_de
except (ImportError, RuntimeError):
    from encoding.representation_v2 import RepresentationV2
    from lexical.transliteration import transliterate_de


_WORD_RE = re.compile(r"[a-z0-9]+(?:[._:/-][a-z0-9]+)*")


@dataclass(frozen=True)
class LateInteractionUnit:
    value: str
    weight: float
    channel: str


@dataclass(frozen=True)
class LateInteractionScore:
    total: float
    components: Dict[str, float]
    explain: Dict[str, object]


def _tokenize(text: str) -> Tuple[str, ...]:
    return tuple(_WORD_RE.findall((text or "").lower()))


def _phrases(tokens: Sequence[str]) -> Tuple[str, ...]:
    values: List[str] = []
    for n in (2, 3):
        for i in range(len(tokens) - n + 1):
            values.append(" ".join(tokens[i : i + n]))
    return tuple(values)


def _count_overlap_ratio(
    left: Mapping[str, int] | None,
    right: Mapping[str, int] | None,
) -> float:
    left = left or {}
    right = right or {}
    if not left or not right:
        return 0.0
    numerator = 0.0
    denominator = 0.0
    for key, q_count in left.items():
        qv = max(0, int(q_count))
        if qv <= 0:
            continue
        denominator += qv
        numerator += min(qv, max(0, int(right.get(key, 0))))
    if denominator <= 0.0:
        return 0.0
    return numerator / denominator


def _maxsim_units(
    query_units: Sequence[LateInteractionUnit],
    doc_values: Sequence[str],
    *,
    partial_word_match: bool = False,
) -> Tuple[float, List[Dict[str, object]]]:
    if not query_units or not doc_values:
        return 0.0, []
    doc_set = {value for value in doc_values if value}
    if not doc_set:
        return 0.0, []

    weighted_total = 0.0
    weight_norm = 0.0
    matched: List[Dict[str, object]] = []

    for unit in query_units:
        if not unit.value:
            continue
        weight_norm += unit.weight
        score = 0.0
        matched_value = ""

        if unit.value in doc_set:
            score = 1.0
            matched_value = unit.value
        elif partial_word_match:
            unit_parts = tuple(part for part in unit.value.split() if part)
            if unit_parts:
                for candidate in sorted(doc_set):
                    candidate_parts = tuple(part for part in candidate.split() if part)
                    if not candidate_parts:
                        continue
                    overlap = len(set(unit_parts) & set(candidate_parts))
                    if overlap <= 0:
                        continue
                    candidate_score = overlap / max(len(unit_parts), len(candidate_parts))
                    if candidate_score > score:
                        score = candidate_score
                        matched_value = candidate

        weighted_total += unit.weight * score
        if score > 0.0:
            matched.append(
                {
                    "query_unit": unit.value,
                    "matched_value": matched_value,
                    "channel": unit.channel,
                    "score": round(score, 6),
                    "weight": round(unit.weight, 6),
                }
            )

    if weight_norm <= 0.0:
        return 0.0, []
    matched.sort(
        key=lambda item: (
            -float(item["score"]),
            -float(item["weight"]),
            str(item["query_unit"]),
            str(item["matched_value"]),
        )
    )
    return weighted_total / weight_norm, matched[:12]


def _alias_values(items: Sequence[str]) -> Tuple[str, ...]:
    values = sorted({value for value in items if value})
    return tuple(values)


def _alias_bridge_values(repr_row: RepresentationV2) -> Tuple[str, ...]:
    values = set()
    for family in repr_row.alias_families:
        if not family:
            continue
        values.add(family)
        payload = family.split("alias:", 1)[-1]
        for member in payload.split("|"):
            normalized = member.replace("_", " ").strip()
            if normalized:
                values.add(normalized)
    for phrase in _phrases(_tokenize(repr_row.normalized_text)):
        values.add(phrase)
    return tuple(sorted(values))


def _translit_bridge_values(repr_row: RepresentationV2) -> Tuple[str, ...]:
    values = set(value for value in repr_row.transliterated_tokens if value)
    normalized_tokens = _tokenize(repr_row.normalized_text)
    values.update(normalized_tokens)
    transliterated_text = transliterate_de(repr_row.normalized_text).lower()
    values.update(_tokenize(transliterated_text))
    return tuple(sorted(values))


def _build_query_units(repr_row: RepresentationV2) -> Dict[str, Tuple[LateInteractionUnit, ...]]:
    tokens = _tokenize(repr_row.normalized_text)
    phrases = _phrases(tokens)
    return {
        "token": tuple(
            LateInteractionUnit(value=value, weight=1.0, channel="token")
            for value in tokens
        ),
        "phrase": tuple(
            LateInteractionUnit(value=value, weight=1.15 if len(value.split()) == 3 else 1.0, channel="phrase")
            for value in phrases
        ),
        "alias": tuple(
            LateInteractionUnit(value=value, weight=0.95, channel="alias")
            for value in _alias_bridge_values(repr_row)
        ),
        "translit": tuple(
            LateInteractionUnit(value=value, weight=0.82, channel="translit")
            for value in _translit_bridge_values(repr_row)
        ),
        "stem_family": tuple(
            LateInteractionUnit(value=value, weight=0.8, channel="stem_family")
            for value in _alias_values(repr_row.stem_families)
        ),
        "relation": tuple(
            LateInteractionUnit(value=value, weight=0.9, channel="relation")
            for value in _alias_values(repr_row.relation_cues)
        ),
        "value": tuple(
            LateInteractionUnit(value=value, weight=0.88, channel="value")
            for value in _alias_values(repr_row.value_cues)
        ),
        "temporal": tuple(
            LateInteractionUnit(value=value, weight=0.88, channel="temporal")
            for value in _alias_values(repr_row.temporal_cues)
        ),
    }


def _doc_unit_values(repr_row: RepresentationV2) -> Dict[str, Tuple[str, ...]]:
    tokens = _tokenize(repr_row.normalized_text)
    return {
        "token": tuple(sorted(set(tokens))),
        "phrase": tuple(sorted(set(_phrases(tokens)))),
        "alias": _alias_bridge_values(repr_row),
        "translit": _translit_bridge_values(repr_row),
        "stem_family": _alias_values(repr_row.stem_families),
        "relation": _alias_values(repr_row.relation_cues),
        "value": _alias_values(repr_row.value_cues),
        "temporal": _alias_values(repr_row.temporal_cues),
    }


def score_late_interaction_native(
    *,
    query_repr: RepresentationV2,
    doc_repr: RepresentationV2 | None,
) -> LateInteractionScore:
    """Compute FAIM-native symbolic late interaction score."""
    if doc_repr is None:
        return LateInteractionScore(
            total=0.0,
            components={
                "token_maxsim": 0.0,
                "phrase_maxsim": 0.0,
                "semantic_phrase_overlap": 0.0,
                "concept_overlap": 0.0,
                "morphology_overlap": 0.0,
                "alias_bridge": 0.0,
                "translit_bridge": 0.0,
                "stem_bridge": 0.0,
                "relation_alignment": 0.0,
                "value_alignment": 0.0,
                "temporal_alignment": 0.0,
            },
            explain={"matched_units": {}},
        )

    query_units = _build_query_units(query_repr)
    doc_units = _doc_unit_values(doc_repr)

    token_score, token_matches = _maxsim_units(
        query_units["token"], doc_units["token"], partial_word_match=True
    )
    phrase_score, phrase_matches = _maxsim_units(
        query_units["phrase"], doc_units["phrase"], partial_word_match=True
    )
    alias_score, alias_matches = _maxsim_units(query_units["alias"], doc_units["alias"])
    translit_score, translit_matches = _maxsim_units(
        query_units["translit"], doc_units["translit"]
    )
    stem_score, stem_matches = _maxsim_units(
        query_units["stem_family"], doc_units["stem_family"]
    )
    relation_score, relation_matches = _maxsim_units(
        query_units["relation"], doc_units["relation"]
    )
    value_score, value_matches = _maxsim_units(query_units["value"], doc_units["value"])
    temporal_score, temporal_matches = _maxsim_units(
        query_units["temporal"], doc_units["temporal"]
    )

    semantic_phrase_overlap = _count_overlap_ratio(
        query_repr.semantic_phrase_counts, doc_repr.semantic_phrase_counts
    )
    concept_overlap = _count_overlap_ratio(
        query_repr.concept_counts, doc_repr.concept_counts
    )
    morphology_overlap = _count_overlap_ratio(
        query_repr.morphology_counts, doc_repr.morphology_counts
    )

    components = {
        "token_maxsim": round(token_score, 6),
        "phrase_maxsim": round(phrase_score, 6),
        "semantic_phrase_overlap": round(semantic_phrase_overlap, 6),
        "concept_overlap": round(concept_overlap, 6),
        "morphology_overlap": round(morphology_overlap, 6),
        "alias_bridge": round(alias_score, 6),
        "translit_bridge": round(translit_score, 6),
        "stem_bridge": round(stem_score, 6),
        "relation_alignment": round(relation_score, 6),
        "value_alignment": round(value_score, 6),
        "temporal_alignment": round(temporal_score, 6),
    }

    total = min(
        1.0,
        0.16 * token_score
        + 0.19 * phrase_score
        + 0.12 * semantic_phrase_overlap
        + 0.12 * concept_overlap
        + 0.07 * morphology_overlap
        + 0.08 * alias_score
        + 0.05 * translit_score
        + 0.05 * stem_score
        + 0.06 * relation_score
        + 0.05 * value_score
        + 0.05 * temporal_score,
    )

    explain = {
        "matched_units": {
            "token": token_matches,
            "phrase": phrase_matches,
            "alias": alias_matches,
            "translit": translit_matches,
            "stem_family": stem_matches,
            "relation": relation_matches,
            "value": value_matches,
            "temporal": temporal_matches,
        },
        "query_unit_counts": {
            "token": len(query_units["token"]),
            "phrase": len(query_units["phrase"]),
            "alias": len(query_units["alias"]),
            "translit": len(query_units["translit"]),
            "stem_family": len(query_units["stem_family"]),
            "relation": len(query_units["relation"]),
            "value": len(query_units["value"]),
            "temporal": len(query_units["temporal"]),
        },
    }

    return LateInteractionScore(
        total=round(total, 6),
        components=components,
        explain=explain,
    )


__all__ = ["LateInteractionScore", "score_late_interaction_native"]
