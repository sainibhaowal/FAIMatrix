"""FAIM Native Lexical Module — pure FAIM synonym and semantic expansion.

This module provides deterministic, zero-dependency synonym expansion using
embedded WordNet data (built once, shipped as part of FAIM).

At runtime: only Python stdlib (json, gzip) — no external ML or NLP libraries.
"""

from .synonym_expander import (
    WeightedExpansion,
    build_weighted_synonym_expansions,
    expand_synonyms_text,
    get_synonyms,
    get_weighted_synonyms,
    is_available,
    merge_weighted_expansions,
    render_weighted_expansion_text,
)
from .semantic_registry import (
    load_semantic_registry_snapshot,
    resolve_semantic_registry_expansions,
)

__all__ = [
    "WeightedExpansion",
    "build_weighted_synonym_expansions",
    "expand_synonyms_text",
    "get_synonyms",
    "get_weighted_synonyms",
    "is_available",
    "load_semantic_registry_snapshot",
    "merge_weighted_expansions",
    "resolve_semantic_registry_expansions",
    "render_weighted_expansion_text",
]
