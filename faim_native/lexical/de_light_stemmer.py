"""Deterministic light German stemmer.

This is intentionally conservative and rule-based only.
"""

from __future__ import annotations

from typing import Iterable, List


_SUFFIXES = (
    "ern",
    "em",
    "en",
    "er",
    "es",
    "e",
    "n",
    "s",
)


def stem_de_token(token: str) -> str:
    token = (token or "").strip().lower()
    if len(token) <= 4:
        return token
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    return token


def stem_de_tokens(tokens: Iterable[str]) -> List[str]:
    return [stem_de_token(token) for token in tokens]


__all__ = ["stem_de_token", "stem_de_tokens"]
