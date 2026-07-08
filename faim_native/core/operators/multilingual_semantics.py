"""Deterministic multilingual graph semantics."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple
from uuid import UUID

from lexical.multilingual_canonicalizer import (
    canonicalize_multilingual_text,
    load_multilingual_resources,
)

MAX_CONCEPT_EDGES_PER_NODE = 6


@dataclass(frozen=True)
class MultilingualDocument:
    node_id: UUID
    normalized_text: str
    language: str
    normalized_tokens: Tuple[str, ...]
    stemmed_tokens: Tuple[str, ...]
    expansions: Tuple[str, ...]


def concept_key_to_vector_text(concept_key: str) -> str:
    return f"concept {concept_key}"


def concept_node_hash(concept_key: str) -> str:
    return hashlib.sha256(f"concept:{concept_key}".encode("utf-8")).hexdigest()


def build_multilingual_document(node_id: UUID, text: str) -> MultilingualDocument:
    item = canonicalize_multilingual_text(text)
    return MultilingualDocument(
        node_id=node_id,
        normalized_text=item.normalized_text,
        language=item.language,
        normalized_tokens=item.tokens,
        stemmed_tokens=item.stemmed_tokens,
        expansions=item.expansions,
    )


def build_multilingual_semantics(
    docs: Sequence[MultilingualDocument],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], Dict[str, List[UUID]]]:
    lexicon, concept_surfaces, _supported_languages = load_multilingual_resources()
    concept_rows: List[Dict[str, object]] = []
    concept_members: Dict[str, List[UUID]] = {}
    lexicon_rows: Dict[Tuple[str, str, str], Dict[str, object]] = {}

    for doc in docs:
        surface_values = sorted(set(doc.normalized_tokens) | set(doc.stemmed_tokens))
        for token in surface_values:
            entry = lexicon.get(doc.language, {}).get(token)
            if entry is None:
                continue
            concept_key = entry.concept_key
            translated = entry.anchor_term
            lexicon_rows[(doc.language, token, concept_key)] = {
                "language": doc.language,
                "surface_form": token,
                "canonical_form": concept_key,
                "concept_key": concept_key,
                "score": 1.0,
                "meta": {
                    "translated_form": translated,
                    "bridge_forms": list(entry.bridge_terms),
                    "concept_surfaces": concept_surfaces.get(concept_key, {}),
                },
            }
            concept_members.setdefault(concept_key, [])
            if doc.node_id not in concept_members[concept_key]:
                if len(concept_members[concept_key]) < MAX_CONCEPT_EDGES_PER_NODE:
                    concept_members[concept_key].append(doc.node_id)

    for concept_key in sorted(concept_members):
        concept_rows.append(
            {
                "concept_key": concept_key,
                "vector_text": concept_node_hash(concept_key),
                "member_count": len(concept_members[concept_key]),
            }
        )

    return (
        concept_rows,
        [lexicon_rows[key] for key in sorted(lexicon_rows)],
        concept_members,
    )


__all__ = [
    "MultilingualDocument",
    "build_multilingual_document",
    "build_multilingual_semantics",
    "concept_key_to_vector_text",
    "concept_node_hash",
]
