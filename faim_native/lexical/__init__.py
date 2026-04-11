"""FAIM Native Lexical Module — pure FAIM synonym and semantic expansion.

This module provides deterministic, zero-dependency synonym expansion using
embedded WordNet data (built once, shipped as part of FAIM).

At runtime: only Python stdlib (json, gzip) — no external ML or NLP libraries.
"""

from .synonym_expander import (
    expand_synonyms_text,
    get_synonyms,
    is_available,
)

__all__ = ["expand_synonyms_text", "get_synonyms", "is_available"]
