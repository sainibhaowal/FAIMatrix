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
except (ImportError, RuntimeError):
    from encoding.porter_stemmer import STOP_WORDS
    from encoding.text_vectorizer import normalize_text

    from lexical.lemmatizer_rules import lemmatize_tokens
    from lexical.phrase_patterns import (
        extract_phrase_labels,
        extract_phrase_surface_map,
    )


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

    expansions: List[str] = []
    lexicon = canonical_map or {}
    for token in lemmas:
        for value in lexicon.get(token, ()):
            if value and value not in expansions:
                expansions.append(value)
    for surface, canonical in sorted(
        phrase_map.items(), key=lambda item: (item[0], item[1])
    ):
        for value in lexicon.get(surface, (canonical,)):
            if value and value not in expansions:
                expansions.append(value)
        if canonical not in expansions:
            expansions.append(canonical)

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
