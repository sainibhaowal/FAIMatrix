"""Deterministic transliteration helpers for English/German support."""

from __future__ import annotations

from lexical.unicode_normalizer import normalize_unicode_text

_DE_MAP = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
)


def transliterate_de(text: str) -> str:
    return normalize_unicode_text(text).translate(_DE_MAP)


__all__ = ["transliterate_de"]
