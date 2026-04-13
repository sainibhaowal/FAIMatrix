"""Deterministic Unicode normalization for multilingual lexical processing."""

from __future__ import annotations

import unicodedata


def normalize_unicode_text(text: str) -> str:
    """Normalize Unicode text to a stable canonical form."""
    return unicodedata.normalize("NFKC", text or "").casefold().strip()


__all__ = ["normalize_unicode_text"]
