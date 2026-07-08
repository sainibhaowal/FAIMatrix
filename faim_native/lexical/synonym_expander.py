"""Deterministic weighted query expansion using embedded ConceptNet data.

This module keeps the original zero-dependency ConceptNet loader, but upgrades
query expansion from flat token appending to a weighted, capped, source-tagged
expansion surface that other FAIM-native lexical components can reuse.
"""

from __future__ import annotations

import gzip
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Set, Tuple

# Path to embedded synonym data
_DATA_PATH = Path(__file__).parent / "data" / "conceptnet_synonyms.json.gz"

# Singleton state (thread-safe)
_synonyms: Optional[Dict[str, list]] = None
_lock = threading.Lock()
_AVAILABLE: Optional[bool] = None


@dataclass(frozen=True)
class WeightedExpansion:
    """Deterministic weighted lexical expansion term."""

    term: str
    weight: float
    sources: Tuple[str, ...]
    origins: Tuple[str, ...] = ()


def _normalize_term(term: str) -> str:
    return " ".join(str(term).strip().lower().split())


def _load() -> bool:
    """Lazy-load synonym data. Thread-safe."""
    global _synonyms, _AVAILABLE

    if _AVAILABLE is not None:
        return _AVAILABLE

    with _lock:
        if _AVAILABLE is not None:
            return _AVAILABLE

        try:
            with gzip.open(_DATA_PATH, "rt", encoding="utf-8") as f:
                _synonyms = json.load(f)
            _AVAILABLE = True
        except (FileNotFoundError, gzip.BadGzipFile, json.JSONDecodeError, OSError):
            _synonyms = {}
            _AVAILABLE = False

    return _AVAILABLE


def is_available() -> bool:
    """Check if ConceptNet synonym data is available."""
    return _load()


def get_synonyms(word: str) -> Set[str]:
    """Return set of synonyms for a word."""
    if not _load():
        return set()
    return set(_synonyms.get(_normalize_term(word), []))


def merge_weighted_expansions(
    rows: Iterable[WeightedExpansion],
    *,
    max_total: int | None = None,
) -> Tuple[WeightedExpansion, ...]:
    """Merge duplicate weighted expansions deterministically."""
    merged: Dict[str, Dict[str, object]] = {}
    for row in rows:
        term = _normalize_term(row.term)
        if not term:
            continue
        weight = max(0.0, min(1.0, float(row.weight)))
        existing = merged.get(term)
        if existing is None:
            merged[term] = {
                "weight": weight,
                "sources": set(row.sources),
                "origins": set(_normalize_term(item) for item in row.origins if item),
            }
            continue
        existing["weight"] = max(float(existing["weight"]), weight)
        existing["sources"].update(row.sources)  # type: ignore[union-attr]
        existing["origins"].update(  # type: ignore[union-attr]
            _normalize_term(item) for item in row.origins if item
        )

    ordered = [
        WeightedExpansion(
            term=term,
            weight=float(payload["weight"]),
            sources=tuple(sorted(payload["sources"])),  # type: ignore[arg-type]
            origins=tuple(sorted(payload["origins"])),  # type: ignore[arg-type]
        )
        for term, payload in merged.items()
    ]
    ordered.sort(key=lambda item: (-item.weight, item.term, item.sources, item.origins))
    if max_total is not None:
        ordered = ordered[: max(0, int(max_total))]
    return tuple(ordered)


def get_weighted_synonyms(
    term: str,
    *,
    max_synonyms: int = 5,
    weight: float = 0.62,
    source: str = "conceptnet",
) -> Tuple[WeightedExpansion, ...]:
    """Return deterministic weighted synonyms for a single term."""
    normalized = _normalize_term(term)
    if not normalized or not _load() or not _synonyms:
        return ()
    synonyms = list(_synonyms.get(normalized, []))[: max(0, int(max_synonyms))]
    weighted = [
        WeightedExpansion(
            term=synonym,
            weight=weight,
            sources=(source,),
            origins=(normalized,),
        )
        for synonym in synonyms
        if _normalize_term(synonym) and _normalize_term(synonym) != normalized
    ]
    return merge_weighted_expansions(weighted)


def build_weighted_synonym_expansions(
    text: str,
    *,
    max_synonyms_per_term: int = 4,
    max_total: int = 24,
    max_phrase_terms: int = 8,
) -> Tuple[WeightedExpansion, ...]:
    """Build deterministic weighted synonym expansions for query text."""
    normalized = _normalize_term(text)
    if not normalized or not _load() or not _synonyms:
        return ()

    tokens = normalized.split()
    weighted: list[WeightedExpansion] = []

    # Phrase-first lookup helps weak paraphrase matching before token-level fallback.
    phrase_budget = max(0, int(max_phrase_terms))
    for width in (3, 2):
        if phrase_budget <= 0 or len(tokens) < width:
            continue
        for start in range(len(tokens) - width + 1):
            phrase = " ".join(tokens[start : start + width])
            matches = get_weighted_synonyms(
                phrase,
                max_synonyms=min(max_synonyms_per_term, phrase_budget),
                weight=0.74 if width == 3 else 0.7,
                source=f"conceptnet_phrase_{width}",
            )
            weighted.extend(matches)
            phrase_budget -= len(matches)
            if phrase_budget <= 0:
                break

    for token in tokens:
        weighted.extend(
            get_weighted_synonyms(
                token,
                max_synonyms=max_synonyms_per_term,
                weight=0.62,
                source="conceptnet_token",
            )
        )

    return merge_weighted_expansions(weighted, max_total=max_total)


def render_weighted_expansion_text(
    base_text: str,
    expansions: Sequence[WeightedExpansion],
    *,
    max_total_terms: int = 32,
) -> str:
    """Render weighted expansions into additive deterministic text.

    Weight is expressed through bounded repetition so the existing vector and
    lexical paths can benefit without changing their public contracts.
    """
    base = " ".join(str(base_text).split()).strip()
    if not expansions:
        return base

    rendered = [base] if base else []
    base_lower = f" {base.lower()} " if base else " "
    emitted = 0

    for item in expansions:
        if emitted >= max_total_terms:
            break
        term = _normalize_term(item.term)
        if not term:
            continue
        repeats = 3 if item.weight >= 0.95 else 2 if item.weight >= 0.8 else 1
        if f" {term} " in base_lower:
            repeats = max(0, repeats - 1)
        for _ in range(repeats):
            rendered.append(term)
            emitted += 1
            if emitted >= max_total_terms:
                break

    return " ".join(part for part in rendered if part).strip()


def expand_synonyms_text(text: str, max_synonyms_per_word: int = 5) -> str:
    """Backward-compatible flat synonym expansion text."""
    weighted = build_weighted_synonym_expansions(
        text,
        max_synonyms_per_term=max_synonyms_per_word,
        max_total=max_synonyms_per_word * max(1, len(text.split())),
    )
    return render_weighted_expansion_text(text, weighted)


__all__ = [
    "WeightedExpansion",
    "build_weighted_synonym_expansions",
    "expand_synonyms_text",
    "get_synonyms",
    "get_weighted_synonyms",
    "is_available",
    "merge_weighted_expansions",
    "render_weighted_expansion_text",
]
