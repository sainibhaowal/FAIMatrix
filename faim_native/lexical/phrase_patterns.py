"""Deterministic phrase rewrite templates for canonical semantics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class PhraseMatch:
    """One matched surface phrase and its canonical label."""

    start: int
    end: int
    surface: str
    canonical: str


_PHRASE_PATTERNS: Tuple[Tuple[Tuple[str, ...], str], ...] = (
    (("lives", "in"), "rel:located_in"),
    (("live", "in"), "rel:located_in"),
    (("resides", "in"), "rel:located_in"),
    (("reside", "in"), "rel:located_in"),
    (("located", "in"), "rel:located_in"),
    (("based", "in"), "rel:located_in"),
    (("headquartered", "in"), "rel:located_in"),
    (("headquarter", "in"), "rel:located_in"),
    (("works", "for"), "rel:employed_by"),
    (("work", "for"), "rel:employed_by"),
    (("works", "at"), "rel:employed_by"),
    (("work", "at"), "rel:employed_by"),
    (("employed", "by"), "rel:employed_by"),
    (("born", "in"), "rel:born_in"),
    (("founded", "in"), "rel:founded_in"),
    (("focuses", "on"), "rel:focus_on"),
    (("focus", "on"), "rel:focus_on"),
    (("specializes", "in"), "rel:focus_on"),
    (("specialize", "in"), "rel:focus_on"),
)

_SURFACE_TO_CANONICAL: Dict[Tuple[str, ...], str] = dict(_PHRASE_PATTERNS)


def match_phrase_patterns(tokens: Sequence[str]) -> List[PhraseMatch]:
    """Return ordered phrase pattern matches for a token sequence."""
    if not tokens:
        return []

    matches: List[PhraseMatch] = []
    for size in (3, 2):
        if len(tokens) < size:
            continue
        for idx in range(len(tokens) - size + 1):
            phrase = tuple(tokens[idx : idx + size])
            canonical = _SURFACE_TO_CANONICAL.get(phrase)
            if canonical is None:
                continue
            matches.append(
                PhraseMatch(
                    start=idx,
                    end=idx + size,
                    surface=" ".join(phrase),
                    canonical=canonical,
                )
            )

    matches.sort(
        key=lambda item: (item.start, -(item.end - item.start), item.canonical)
    )
    deduped: List[PhraseMatch] = []
    occupied = set()
    for match in matches:
        span = set(range(match.start, match.end))
        if occupied & span:
            continue
        occupied |= span
        deduped.append(match)
    return deduped


def extract_phrase_labels(tokens: Sequence[str]) -> List[str]:
    """Return unique canonical labels for matched phrase patterns."""
    labels = {match.canonical for match in match_phrase_patterns(tokens)}
    return sorted(labels)


def extract_phrase_surface_map(tokens: Sequence[str]) -> Dict[str, str]:
    """Return surface phrase -> canonical label mapping for matched phrases."""
    mapping = {
        match.surface: match.canonical for match in match_phrase_patterns(tokens)
    }
    return dict(sorted(mapping.items(), key=lambda item: (item[0], item[1])))


__all__ = [
    "PhraseMatch",
    "extract_phrase_labels",
    "extract_phrase_surface_map",
    "match_phrase_patterns",
]
