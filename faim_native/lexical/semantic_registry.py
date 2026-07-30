"""Deterministic FAIM semantic registry over shipped lexical resources.

This module does not invent a fake 1M concept graph. Instead, it exposes a real
runtime semantic registry layer over:

- embedded ConceptNet synonym keys
- shipped multilingual lexicon surfaces
- graph-scoped canonical lexicon rows
- graph-scoped multilingual bridge rows
- graph-scoped domain lexicon rows

The registry is additive and explainable. It produces weighted expansions and
registry diagnostics without changing the canonical FAIM vector contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Mapping, Sequence, Tuple

from lexical.multilingual_canonicalizer import load_multilingual_resources
from lexical import synonym_expander
from lexical.synonym_expander import (
    WeightedExpansion,
    _normalize_term,
    get_weighted_synonyms,
    is_available,
    merge_weighted_expansions,
)


@dataclass(frozen=True)
class SemanticRegistrySnapshot:
    conceptnet_terms: int
    static_lexicon_terms: int
    supported_languages: Tuple[str, ...]
    static_registry_terms: int

    @property
    def total_terms(self) -> int:
        return int(self.conceptnet_terms + self.static_lexicon_terms)


def _surface_windows(text: str) -> Tuple[str, ...]:
    normalized = _normalize_term(text)
    tokens = [token for token in normalized.split() if token]
    values: List[str] = []
    for width in (3, 2, 1):
        if len(tokens) < width:
            continue
        for idx in range(len(tokens) - width + 1):
            candidate = " ".join(tokens[idx : idx + width])
            if candidate and candidate not in values:
                values.append(candidate)
    return tuple(values)


@lru_cache(maxsize=1)
def load_semantic_registry_snapshot() -> SemanticRegistrySnapshot:
    multilingual_by_language, _concept_surfaces, supported_languages = (
        load_multilingual_resources()
    )
    static_lexicon_terms = sum(
        len(language_map) for language_map in multilingual_by_language.values()
    )
    conceptnet_terms = 0
    if is_available() and synonym_expander._synonyms:
        conceptnet_terms = len(synonym_expander._synonyms)
    return SemanticRegistrySnapshot(
        conceptnet_terms=conceptnet_terms,
        static_lexicon_terms=static_lexicon_terms,
        supported_languages=tuple(sorted(supported_languages)),
        static_registry_terms=int(conceptnet_terms + static_lexicon_terms),
    )


def resolve_semantic_registry_expansions(
    *,
    query_text: str,
    canonical_map: Mapping[str, Sequence[str]] | None = None,
    multilingual_map: Mapping[str, Sequence[str]] | None = None,
    domain_map: Mapping[str, Sequence[str]] | None = None,
    max_total: int = 18,
) -> Tuple[Tuple[WeightedExpansion, ...], Dict[str, object]]:
    canonical_map = canonical_map or {}
    multilingual_map = multilingual_map or {}
    domain_map = domain_map or {}
    windows = _surface_windows(query_text)

    rows: List[WeightedExpansion] = []
    matched_surfaces: Dict[str, List[str]] = {
        "canonical": [],
        "multilingual": [],
        "domain": [],
        "conceptnet": [],
    }

    for surface in windows:
        for value in canonical_map.get(surface, ()):
            term = _normalize_term(value)
            if not term or term == surface:
                continue
            rows.append(
                WeightedExpansion(
                    term=term,
                    weight=0.94 if " " in surface else 0.9,
                    sources=("semantic_registry_canonical",),
                    origins=(surface,),
                )
            )
            if surface not in matched_surfaces["canonical"]:
                matched_surfaces["canonical"].append(surface)

        for value in multilingual_map.get(surface, ()):
            term = _normalize_term(value)
            if not term or term == surface:
                continue
            rows.append(
                WeightedExpansion(
                    term=term,
                    weight=0.88 if " " in surface else 0.84,
                    sources=("semantic_registry_multilingual",),
                    origins=(surface,),
                )
            )
            if surface not in matched_surfaces["multilingual"]:
                matched_surfaces["multilingual"].append(surface)

        for value in domain_map.get(surface, ()):
            term = _normalize_term(value)
            if not term or term == surface:
                continue
            rows.append(
                WeightedExpansion(
                    term=term,
                    weight=0.9 if " " in surface else 0.86,
                    sources=("semantic_registry_domain",),
                    origins=(surface,),
                )
            )
            if surface not in matched_surfaces["domain"]:
                matched_surfaces["domain"].append(surface)

        if is_available():
            conceptnet_rows = get_weighted_synonyms(
                surface,
                max_synonyms=3 if " " in surface else 2,
                weight=0.76 if " " in surface else 0.68,
                source=(
                    "semantic_registry_conceptnet_phrase"
                    if " " in surface
                    else "semantic_registry_conceptnet_token"
                ),
            )
            if conceptnet_rows:
                rows.extend(conceptnet_rows)
                if surface not in matched_surfaces["conceptnet"]:
                    matched_surfaces["conceptnet"].append(surface)

    merged = merge_weighted_expansions(rows, max_total=max_total)
    snapshot = load_semantic_registry_snapshot()
    info: Dict[str, object] = {
        "static_term_count": snapshot.static_registry_terms,
        "conceptnet_terms": snapshot.conceptnet_terms,
        "static_lexicon_terms": snapshot.static_lexicon_terms,
        "supported_languages": list(snapshot.supported_languages),
        "matched_surface_count": sum(len(items) for items in matched_surfaces.values()),
        "matched_surfaces": {
            key: values[:12] for key, values in sorted(matched_surfaces.items())
        },
        "expansion_count": len(merged),
    }
    return merged, info


__all__ = [
    "SemanticRegistrySnapshot",
    "load_semantic_registry_snapshot",
    "resolve_semantic_registry_expansions",
]
