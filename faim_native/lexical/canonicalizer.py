"""Deterministic query-time canonicalization for Phase 2."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

try:
    from faim.Faim_Native.encoding.porter_stemmer import STOP_WORDS
    from faim.Faim_Native.encoding.text_vectorizer import normalize_text
    from faim.Faim_Native.lexical.lemmatizer_rules import lemmatize_tokens
    from faim.Faim_Native.lexical.phrase_patterns import (
        extract_phrase_labels,
        extract_phrase_surface_map,
    )
    from faim.Faim_Native.lexical.synonym_expander import (
        WeightedExpansion,
        merge_weighted_expansions,
    )
except (ImportError, RuntimeError):
    from encoding.porter_stemmer import STOP_WORDS
    from encoding.text_vectorizer import normalize_text

    from lexical.lemmatizer_rules import lemmatize_tokens
    from lexical.phrase_patterns import (
        extract_phrase_labels,
        extract_phrase_surface_map,
    )
    from lexical.synonym_expander import WeightedExpansion, merge_weighted_expansions


_WORD_RE = re.compile(r"[a-z0-9]+(?:[._:/-][a-z0-9]+)*")


@dataclass(frozen=True)
class CanonicalText:
    """Canonicalized lexical form used for query-time expansion and mining."""

    normalized_text: str
    surface_tokens: Tuple[str, ...]
    lemma_tokens: Tuple[str, ...]
    phrase_labels: Tuple[str, ...]
    expansions: Tuple[str, ...]
    canonical_text: str
    weighted_expansions: Tuple[WeightedExpansion, ...] = ()


def tokenize_words(text: str) -> List[str]:
    """Tokenize lowercased normalized text into deterministic tokens."""
    return _WORD_RE.findall(text)


def canonicalize_text(
    text: str,
    *,
    canonical_map: Mapping[str, Sequence[str]] | None = None,
) -> CanonicalText:
    """Canonicalize text additively without changing base ingest contracts."""
    normalized = normalize_text(
        text,
        lowercase=True,
        stem=False,
        remove_stopwords=False,
        expand_synonyms=False,
    )
    surface_tokens = tokenize_words(normalized)
    filtered = [token for token in surface_tokens if token not in STOP_WORDS]
    lemmas = lemmatize_tokens(filtered)
    phrase_labels = extract_phrase_labels(surface_tokens)
    phrase_map = extract_phrase_surface_map(surface_tokens)

    weighted_rows: List[WeightedExpansion] = []
    lexicon = canonical_map or {}
    for token in lemmas:
        for value in lexicon.get(token, ()):
            if value:
                weighted_rows.append(
                    WeightedExpansion(
                        term=str(value),
                        weight=0.9,
                        sources=("canonical_lemma",),
                        origins=(token,),
                    )
                )
    for surface, canonical in sorted(
        phrase_map.items(), key=lambda item: (item[0], item[1])
    ):
        for value in lexicon.get(surface, (canonical,)):
            if value:
                weighted_rows.append(
                    WeightedExpansion(
                        term=str(value),
                        weight=0.96 if value == canonical else 0.92,
                        sources=(
                            "canonical_phrase"
                            if value == canonical
                            else "canonical_phrase_lexicon",
                        ),
                        origins=(surface,),
                    )
                )
        weighted_rows.append(
            WeightedExpansion(
                term=str(canonical),
                weight=0.88,
                sources=("phrase_pattern",),
                origins=(surface,),
            )
        )

    weighted_expansions = merge_weighted_expansions(weighted_rows)
    expansions = [item.term for item in weighted_expansions]

    canonical_tokens: List[str] = list(lemmas)
    for label in phrase_labels:
        if label not in canonical_tokens:
            canonical_tokens.append(label)
    for value in expansions:
        if value not in canonical_tokens:
            canonical_tokens.append(value)

    return CanonicalText(
        normalized_text=normalized,
        surface_tokens=tuple(surface_tokens),
        lemma_tokens=tuple(lemmas),
        phrase_labels=tuple(phrase_labels),
        expansions=tuple(expansions),
        weighted_expansions=weighted_expansions,
        canonical_text=" ".join(canonical_tokens),
    )


def canonical_map_from_entries(
    rows: Iterable[Tuple[str, str]],
) -> Dict[str, Tuple[str, ...]]:
    """Build stable surface->canonical map from row tuples."""
    mapped: Dict[str, List[str]] = {}
    for surface, canonical in rows:
        if not surface or not canonical:
            continue
        values = mapped.setdefault(surface, [])
        if canonical not in values:
            values.append(canonical)
    return {k: tuple(v) for k, v in sorted(mapped.items(), key=lambda item: item[0])}


__all__ = [
    "CanonicalText",
    "canonical_map_from_entries",
    "canonicalize_text",
    "tokenize_words",
]
