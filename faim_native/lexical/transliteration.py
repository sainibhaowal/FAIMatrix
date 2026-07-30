"""Deterministic transliteration helpers for multilingual lexical support."""

from __future__ import annotations

import unicodedata

from lexical.unicode_normalizer import normalize_unicode_text

_DE_MAP = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
)


def transliterate_text(text: str, *, language: str | None = None) -> str:
    normalized = normalize_unicode_text(text)
    if language in {None, "de"}:
        normalized = normalized.translate(_DE_MAP)
    folded = unicodedata.normalize("NFKD", normalized)
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def transliterate_de(text: str) -> str:
    return transliterate_text(text, language="de")


__all__ = ["transliterate_de", "transliterate_text"]
