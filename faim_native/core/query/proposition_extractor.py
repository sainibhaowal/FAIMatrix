"""Deterministic proposition extraction for Phase 4 reranking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

try:
    from faim.Faim_Native.encoding.porter_stemmer import STOP_WORDS
    from faim.Faim_Native.encoding.representation_v2 import (
        RepresentationV2,
        build_representation_v2,
    )
    from faim.Faim_Native.lexical.canonicalizer import canonicalize_text
except (ImportError, RuntimeError):
    from encoding.porter_stemmer import STOP_WORDS
    from encoding.representation_v2 import RepresentationV2, build_representation_v2
    from lexical.canonicalizer import canonicalize_text


@dataclass(frozen=True)
class Proposition:
    """Deterministic proposition tuple."""

    entity: str
    relation: str
    value: str
    time: str


@dataclass(frozen=True)
class PropositionAnalysis:
    """Query/doc proposition analysis bundle."""

    propositions: Tuple[Proposition, ...]
    entities: Tuple[str, ...]
    relations: Tuple[str, ...]
    values: Tuple[str, ...]
    times: Tuple[str, ...]
    content_tokens: Tuple[str, ...]


def _unique(values: Iterable[str]) -> Tuple[str, ...]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        value = str(value).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


def _fallback_entities(tokens: Sequence[str]) -> Tuple[str, ...]:
    return _unique(
        token
        for token in tokens
        if token not in STOP_WORDS
        and not token.startswith("rel:")
        and not token.startswith("date:")
        and not token.startswith("year:")
        and not token.startswith("time:")
        and not token.startswith("num:")
    )[:3]


def extract_propositions(
    text: str,
    *,
    representation: Optional[RepresentationV2] = None,
) -> PropositionAnalysis:
    """Extract deterministic propositions from normalized lexical text."""
    repr_v2 = representation or build_representation_v2(
        text,
        expand_synonyms=True,
        stem=True,
    )
    canonical = canonicalize_text(text)
    entities = _unique(repr_v2.entity_tokens)
    if not entities:
        entities = _fallback_entities(canonical.lemma_tokens)

    relations = _unique(
        list(canonical.phrase_labels)
        + [value for value in canonical.expansions if value.startswith("rel:")]
    )
    if not relations:
        relations = ("rel:about",)

    values = _unique(
        token.removeprefix("num:")
        for token in repr_v2.time_tokens
        if token.startswith("num:")
    )
    if not values and len(entities) > 1:
        values = _unique(entities[1:3])
    times = _unique(
        token
        for token in repr_v2.time_tokens
        if token.startswith("date:")
        or token.startswith("year:")
        or token.startswith("time:")
    )
    content_tokens = _unique(canonical.lemma_tokens)

    propositions: List[Proposition] = []
    entity_values = entities or ("",)
    relation_values = relations or ("rel:about",)
    scalar_values = values[:2] or ("",)
    time_values = times[:2] or ("",)

    for entity in entity_values[:2]:
        for relation in relation_values[:2]:
            if values or times:
                for value in scalar_values:
                    for time_value in time_values:
                        propositions.append(
                            Proposition(
                                entity=entity,
                                relation=relation,
                                value=value,
                                time=time_value,
                            )
                        )
            else:
                propositions.append(
                    Proposition(
                        entity=entity,
                        relation=relation,
                        value="",
                        time="",
                    )
                )

    if not propositions:
        propositions.append(Proposition("", "rel:about", "", ""))

    return PropositionAnalysis(
        propositions=tuple(propositions),
        entities=entities,
        relations=relations,
        values=values,
        times=times,
        content_tokens=content_tokens,
    )


def proposition_overlap(
    left: PropositionAnalysis,
    right: PropositionAnalysis,
) -> float:
    """Compute bounded proposition overlap."""
    if not left.propositions or not right.propositions:
        return 0.0

    best = 0.0
    for lp in left.propositions:
        for rp in right.propositions:
            score = 0.0
            if lp.entity and rp.entity and lp.entity == rp.entity:
                score += 0.35
            if lp.relation == rp.relation:
                score += 0.35
            if lp.value and rp.value and lp.value == rp.value:
                score += 0.20
            if lp.time and rp.time and lp.time == rp.time:
                score += 0.10
            best = max(best, score)
    return min(best, 1.0)


def proposition_signature(analysis: PropositionAnalysis) -> Tuple[str, str, str]:
    """Return a conservative signature for duplicate/conflict grouping."""
    entity = analysis.entities[0] if analysis.entities else ""
    relation = analysis.relations[0] if analysis.relations else "rel:about"
    time = analysis.times[0] if analysis.times else ""
    return entity, relation, time


__all__ = [
    "Proposition",
    "PropositionAnalysis",
    "extract_propositions",
    "proposition_overlap",
    "proposition_signature",
]
