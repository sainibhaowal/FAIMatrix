"""Deterministic acronym and alias mining from corpus text."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

try:
    from faim.Faim_Native.encoding.text_vectorizer import normalize_text
except (ImportError, RuntimeError):
    from encoding.text_vectorizer import normalize_text


_LONG_ACRONYM_RE = re.compile(
    r"\b([A-Za-z][A-Za-z0-9][A-Za-z0-9/&,\- ]{2,80}?)\s*\(([A-Z][A-Z0-9]{1,12})\)"
)
_ACRONYM_LONG_RE = re.compile(
    r"\b([A-Z][A-Z0-9]{1,12})\s*\(([A-Za-z][A-Za-z0-9][A-Za-z0-9/&,\- ]{2,80}?)\)"
)
_AKA_RE = re.compile(
    r"\b([A-Za-z][A-Za-z0-9][A-Za-z0-9/&,\- ]{1,80}?)\s+(?:aka|also known as)\s+([A-Za-z][A-Za-z0-9][A-Za-z0-9/&,\- ]{1,80}?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AliasCandidate:
    """One mined alias/acroynm mapping."""

    surface_form: str
    canonical_form: str
    kind: str
    support_count: int
    score: float
    meta: Dict[str, object]


def _normalize_phrase(text: str) -> str:
    return normalize_text(
        text,
        lowercase=True,
        stem=False,
        remove_stopwords=False,
        expand_synonyms=False,
    )


def _acronym_for(surface: str) -> str:
    parts = [part for part in re.findall(r"[A-Za-z0-9]+", surface) if part]
    return "".join(part[0] for part in parts).upper()


def mine_alias_candidates(
    texts: Iterable[str],
    *,
    min_support: int = 1,
) -> List[AliasCandidate]:
    """Mine deterministic acronym and alias mappings from raw texts."""
    counts: Counter[Tuple[str, str, str]] = Counter()

    for raw_text in texts:
        if not raw_text:
            continue

        for long_form, acronym in _LONG_ACRONYM_RE.findall(raw_text):
            long_norm = _normalize_phrase(long_form)
            acronym_norm = acronym.lower()
            if long_norm and acronym_norm and _acronym_for(long_norm) == acronym:
                counts[(acronym_norm, long_norm, "acronym")] += 1

        for acronym, long_form in _ACRONYM_LONG_RE.findall(raw_text):
            long_norm = _normalize_phrase(long_form)
            acronym_norm = acronym.lower()
            if long_norm and acronym_norm and _acronym_for(long_norm) == acronym:
                counts[(acronym_norm, long_norm, "acronym")] += 1

        for left, right in _AKA_RE.findall(raw_text):
            left_norm = _normalize_phrase(left)
            right_norm = _normalize_phrase(right)
            if not left_norm or not right_norm or left_norm == right_norm:
                continue
            canonical = max((left_norm, right_norm), key=lambda item: (len(item), item))
            surface = right_norm if canonical == left_norm else left_norm
            counts[(surface, canonical, "alias")] += 1

    candidates: List[AliasCandidate] = []
    for (surface, canonical, kind), support in sorted(
        counts.items(), key=lambda item: (item[0][2], item[0][0], item[0][1])
    ):
        if support < min_support:
            continue
        score = min(1.0, 0.6 + 0.1 * support)
        candidates.append(
            AliasCandidate(
                surface_form=surface,
                canonical_form=canonical,
                kind=kind,
                support_count=support,
                score=round(score, 6),
                meta={
                    "support_count": support,
                    "canonical_len": len(canonical.split()),
                },
            )
        )
    return candidates


__all__ = ["AliasCandidate", "mine_alias_candidates"]
