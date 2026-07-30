"""Semantic Signature V1 for FAIM-native lexical-semantic enrichment.

This module stays fully deterministic and model-free. It adds semantic-style
channels that sit beside ``v_native`` and the existing Representation V2
channels without changing the canonical 256-d vector contract.
"""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

try:
    from faim.Faim_Native.encoding.porter_stemmer import stem as stem_en
    from faim.Faim_Native.lexical.de_light_stemmer import stem_de_tokens
    from faim.Faim_Native.lexical.transliteration import transliterate_de
    from faim.Faim_Native.lexical.unicode_normalizer import normalize_unicode_text
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from encoding.porter_stemmer import stem as stem_en
    from lexical.de_light_stemmer import stem_de_tokens
    from lexical.transliteration import transliterate_de
    from lexical.unicode_normalizer import normalize_unicode_text


SEMANTIC_PHRASE_BUCKETS = 4096
CONCEPT_BUCKETS = 2048
MORPHOLOGY_BUCKETS = 1024

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[._:/-][a-z0-9]+)*")
_NUMBER_RE = re.compile(r"\b[$€£]?\d+(?:,\d{3})*(?:\.\d+)?%?\b")
_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2}|2100)\b")
_DATE_RE = re.compile(r"\b\d{4}[-/]\d{2}[-/]\d{2}\b")

_RELATION_TERMS = {
    "acquired": "relation:acquire",
    "acquire": "relation:acquire",
    "acquisition": "relation:acquire",
    "owns": "relation:ownership",
    "owned": "relation:ownership",
    "causes": "relation:causation",
    "caused": "relation:causation",
    "depends": "relation:dependency",
    "depends_on": "relation:dependency",
    "supports": "relation:support",
    "supported": "relation:support",
    "blocks": "relation:block",
    "blocked": "relation:block",
    "uses": "relation:usage",
    "used": "relation:usage",
    "contains": "relation:contain",
    "contained": "relation:contain",
    "requires": "relation:require",
    "required": "relation:require",
    "runs": "relation:run",
    "running": "relation:run",
    "fails": "relation:failure",
    "failed": "relation:failure",
    "fixes": "relation:fix",
    "fixed": "relation:fix",
    "improves": "relation:improve",
    "improved": "relation:improve",
}

_ALIAS_FAMILY_MAP = {
    "ai": ("ai", "artificial_intelligence"),
    "ml": ("ml", "machine_learning"),
    "llm": ("llm", "large_language_model"),
    "rag": ("rag", "retrieval_augmented_generation"),
    "api": ("api", "application_programming_interface"),
    "db": ("db", "database"),
    "usa": ("usa", "united_states"),
    "us": ("us", "united_states"),
    "uk": ("uk", "united_kingdom"),
    "nyc": ("nyc", "new_york_city"),
    "otp": ("otp", "one_time_password"),
    "totp": ("totp", "time_based_one_time_password"),
}

_CONCEPT_FAMILY_MAP = {
    "revenue": ("concept:finance.revenue", "income", "sales"),
    "invoice": ("concept:finance.invoice", "billing", "bill"),
    "payment": ("concept:finance.payment", "paid", "transaction"),
    "tenant": ("concept:platform.tenant", "workspace", "account_scope"),
    "graph": ("concept:knowledge.graph", "knowledge_graph", "memory_graph"),
    "memory": ("concept:knowledge.memory", "recall", "state"),
    "query": ("concept:retrieval.query", "search", "ask"),
    "retrieval": ("concept:retrieval.core", "search", "recall"),
    "rerank": ("concept:retrieval.rerank", "ranking", "relevance"),
    "reasoning": ("concept:cortex.reasoning", "inference", "analysis"),
    "security": ("concept:security.core", "auth", "privacy"),
    "authentication": ("concept:security.authn", "login", "signin"),
    "authorization": ("concept:security.authz", "permissions", "scopes"),
    "encryption": ("concept:security.crypto", "cipher", "encrypted"),
    "multilingual": ("concept:language.crosslingual", "cross_lingual", "translation"),
    "translation": ("concept:language.translation", "translate", "multilingual"),
    "medical": ("concept:domain.medical", "clinical", "healthcare"),
    "legal": ("concept:domain.legal", "compliance", "policy"),
    "software": ("concept:domain.software", "code", "programming"),
    "database": ("concept:infra.database", "storage", "db"),
    "worker": ("concept:runtime.worker", "job", "scheduler"),
}

_MORPH_SUFFIXES = (
    "tion",
    "sion",
    "ment",
    "ness",
    "ity",
    "ing",
    "ed",
    "er",
    "or",
    "al",
    "ive",
    "ous",
    "able",
    "less",
    "ship",
)


@dataclass(frozen=True)
class SemanticSignature:
    semantic_phrase_counts: Dict[str, int]
    concept_counts: Dict[str, int]
    morphology_counts: Dict[str, int]
    alias_families: Tuple[str, ...]
    transliterated_tokens: Tuple[str, ...]
    stem_families: Tuple[str, ...]
    relation_cues: Tuple[str, ...]
    value_cues: Tuple[str, ...]
    temporal_cues: Tuple[str, ...]


def _hash_bucket(term: str, num_buckets: int) -> str:
    digest = hashlib.sha256(term.encode("utf-8")).digest()
    return str(int.from_bytes(digest[:4], "big", signed=False) % num_buckets)


def _count_bucketed(terms: Iterable[str], num_buckets: int) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for term in terms:
        bucket = _hash_bucket(term, num_buckets)
        counts[bucket] = counts.get(bucket, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def _build_semantic_phrases(tokens: Sequence[str]) -> List[str]:
    if not tokens:
        return []
    phrases: List[str] = []
    for n in (2, 3, 4):
        for i in range(len(tokens) - n + 1):
            window = tokens[i : i + n]
            phrases.append("sem:" + "|".join(window))
            if n >= 3:
                phrases.append("skipsem:" + "|".join((window[0], "*", window[-1])))
    return phrases


def _stem_token(token: str) -> str:
    if any(ch in token for ch in "äöüß"):
        return stem_de_tokens([token])[0]
    return stem_en(token)


def _build_alias_families(tokens: Sequence[str]) -> Tuple[str, ...]:
    families = set()
    for token in tokens:
        family = _ALIAS_FAMILY_MAP.get(token)
        if family:
            families.add("alias:" + "|".join(family))
    return tuple(sorted(families))


def _build_concept_terms(tokens: Sequence[str]) -> List[str]:
    concept_terms: List[str] = []
    for token in tokens:
        family = _CONCEPT_FAMILY_MAP.get(token)
        if family:
            concept_terms.extend(family)
    return sorted(concept_terms)


def _build_transliterated_tokens(raw_text: str) -> Tuple[str, ...]:
    normalized = normalize_unicode_text(raw_text)
    transliterated = transliterate_de(normalized).lower()
    source_tokens = set(_tokenize(normalized))
    translit_tokens = {
        token for token in _tokenize(transliterated) if token and token not in source_tokens
    }
    return tuple(sorted(translit_tokens))


def _build_stem_families(tokens: Sequence[str]) -> Tuple[str, ...]:
    families = set()
    for token in tokens:
        stem = _stem_token(token)
        if stem and stem != token:
            families.add(f"stem:{stem}|{token}")
    return tuple(sorted(families))


def _build_morphology_terms(tokens: Sequence[str]) -> List[str]:
    terms: List[str] = []
    for token in tokens:
        if not token:
            continue
        shape = []
        for ch in token:
            if ch.isdigit():
                shape.append("d")
            elif ch.isalpha():
                shape.append("a")
            else:
                shape.append("_")
        collapsed_shape = "".join(shape[:12])
        terms.append(f"shape:{collapsed_shape}")
        if len(token) >= 3:
            terms.append(f"pref:{token[:3]}")
            terms.append(f"suf:{token[-3:]}")
        for suffix in _MORPH_SUFFIXES:
            if token.endswith(suffix) and len(token) > len(suffix) + 1:
                terms.append(f"morph:{suffix}")
                break
    return sorted(terms)


def _build_relation_cues(tokens: Sequence[str]) -> Tuple[str, ...]:
    cues = {_RELATION_TERMS[token] for token in tokens if token in _RELATION_TERMS}
    return tuple(sorted(cues))


def _build_value_cues(raw_text: str) -> Tuple[str, ...]:
    cues = set()
    lowered = raw_text.lower()
    for match in _NUMBER_RE.findall(lowered):
        compact = match.replace(",", "")
        if "%" in compact or f"{compact}%" in lowered:
            cues.add("value:percent")
        elif compact.startswith(("$", "€", "£")):
            cues.add("value:currency")
        else:
            cues.add("value:number")
    if "more than" in lowered or "greater than" in lowered:
        cues.add("value:gt")
    if "less than" in lowered or "under " in lowered:
        cues.add("value:lt")
    if "between" in lowered:
        cues.add("value:range")
    return tuple(sorted(cues))


def _build_temporal_cues(raw_text: str) -> Tuple[str, ...]:
    lowered = raw_text.lower()
    cues = set()
    if _DATE_RE.search(lowered):
        cues.add("time:date")
    if _YEAR_RE.search(lowered):
        cues.add("time:year")
    for marker in ("before", "after", "during", "since", "until", "quarter", "month", "week"):
        if marker in lowered:
            cues.add(f"time:{marker}")
    return tuple(sorted(cues))


def build_semantic_signature(text: str) -> SemanticSignature:
    """Build a deterministic semantic signature from raw text."""
    normalized = normalize_unicode_text(text).lower()
    tokens = _tokenize(normalized)

    semantic_phrases = _build_semantic_phrases(tokens)
    concept_terms = _build_concept_terms(tokens)
    morphology_terms = _build_morphology_terms(tokens)
    alias_families = _build_alias_families(tokens)
    transliterated_tokens = _build_transliterated_tokens(text)
    stem_families = _build_stem_families(tokens)
    relation_cues = _build_relation_cues(tokens)
    value_cues = _build_value_cues(text)
    temporal_cues = _build_temporal_cues(text)

    return SemanticSignature(
        semantic_phrase_counts=_count_bucketed(
            semantic_phrases, SEMANTIC_PHRASE_BUCKETS
        ),
        concept_counts=_count_bucketed(concept_terms, CONCEPT_BUCKETS),
        morphology_counts=_count_bucketed(morphology_terms, MORPHOLOGY_BUCKETS),
        alias_families=alias_families,
        transliterated_tokens=transliterated_tokens,
        stem_families=stem_families,
        relation_cues=relation_cues,
        value_cues=value_cues,
        temporal_cues=temporal_cues,
    )


__all__ = ["SemanticSignature", "build_semantic_signature"]
