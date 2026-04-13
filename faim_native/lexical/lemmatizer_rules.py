"""Deterministic rule-based lemmatization for canonical semantics.

Conservative by design: normalize common inflections without introducing
aggressive stemming drift. No ML, no external dependencies.
"""

from __future__ import annotations

from typing import Dict


IRREGULAR_LEMMAS: Dict[str, str] = {
    "am": "be",
    "are": "be",
    "been": "be",
    "being": "be",
    "is": "be",
    "was": "be",
    "were": "be",
    "did": "do",
    "does": "do",
    "done": "do",
    "has": "have",
    "had": "have",
    "having": "have",
    "men": "man",
    "women": "woman",
    "children": "child",
    "people": "person",
    "teeth": "tooth",
    "feet": "foot",
    "mice": "mouse",
    "geese": "goose",
    "indices": "index",
    "matrices": "matrix",
    "lives": "live",
}


def _has_double_tail(token: str) -> bool:
    return len(token) >= 2 and token[-1] == token[-2]


def lemmatize_token(token: str) -> str:
    """Return a conservative lemma for a lowercase token."""
    t = str(token or "").strip().lower()
    if not t:
        return ""
    if len(t) <= 2:
        return t

    irregular = IRREGULAR_LEMMAS.get(t)
    if irregular:
        return irregular

    if t.endswith("ies") and len(t) > 4:
        return t[:-3] + "y"

    if t.endswith("ves") and len(t) > 4:
        if t[:-3].endswith("i"):
            return t[:-3] + "fe"
        return t[:-3] + "f"

    if t.endswith("ing") and len(t) > 5:
        base = t[:-3]
        if _has_double_tail(base) and base[-1] not in {"s", "l", "z"}:
            base = base[:-1]
        elif base.endswith(("at", "bl", "iz")):
            base = base + "e"
        return base

    if t.endswith("ied") and len(t) > 4:
        return t[:-3] + "y"

    if t.endswith("ed") and len(t) > 4:
        base = t[:-2]
        if _has_double_tail(base) and base[-1] not in {"s", "l", "z"}:
            base = base[:-1]
        elif base.endswith(("at", "bl", "iz")):
            base = base + "e"
        return base

    if t.endswith("es") and len(t) > 4:
        if t.endswith(("sses", "shes", "ches", "xes", "zes")):
            return t[:-2]
        if t.endswith("oes"):
            return t[:-2]
        candidate = t[:-1]
        if candidate.endswith("e"):
            return candidate
        return t[:-2]

    if t.endswith("s") and len(t) > 3 and not t.endswith(("ss", "us", "is")):
        return t[:-1]

    return t


def lemmatize_tokens(tokens: list[str]) -> list[str]:
    """Lemmatize a token sequence deterministically."""
    return [lemma for lemma in (lemmatize_token(token) for token in tokens) if lemma]


__all__ = ["IRREGULAR_LEMMAS", "lemmatize_token", "lemmatize_tokens"]
