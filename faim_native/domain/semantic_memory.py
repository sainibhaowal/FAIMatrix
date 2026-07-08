"""FAIM-native semantic memory bundle learning.

This layer learns graph-local concept and paraphrase bundles directly from
uploaded graph content. It is deterministic, model-free, additive, and scoped
to the current graph only.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple
from uuid import UUID

from core.operators.terminology_mining import (
    DomainDocument,
    extract_phrase_terms,
)
from encoding.semantic_signature import build_semantic_signature
from lexical.alias_miner import mine_alias_candidates
from lexical.canonicalizer import canonicalize_text

MAX_TERMS = 96
MAX_BUNDLES = 24
MAX_BUNDLE_MEMBERS = 8
MAX_CONTEXT_TERMS = 8
MIN_CONTEXT_OVERLAP = 2
SIMILARITY_THRESHOLD = 0.72


@dataclass(frozen=True)
class SemanticEdgeProposal:
    src_node_id: UUID
    dst_node_id: UUID
    semantic_type: str
    semantic_weight: float
    meta: Dict[str, object]


@dataclass(frozen=True)
class SemanticMemoryLearningResult:
    lexicon_rows: Tuple[Dict[str, object], ...]
    source_rows: Tuple[Dict[str, object], ...]
    semantic_edges: Tuple[SemanticEdgeProposal, ...]


@dataclass
class _TermState:
    support_count: int = 0
    doc_ids: Set[UUID] = field(default_factory=set)
    contexts: Counter[str] = field(default_factory=Counter)
    node_ids: Set[UUID] = field(default_factory=set)
    lemma_tokens: Set[str] = field(default_factory=set)
    alias_families: Set[str] = field(default_factory=set)
    transliterated_tokens: Set[str] = field(default_factory=set)
    stem_roots: Set[str] = field(default_factory=set)
    relation_cues: Set[str] = field(default_factory=set)
    value_cues: Set[str] = field(default_factory=set)
    temporal_cues: Set[str] = field(default_factory=set)


class _UnionFind:
    def __init__(self, items: Iterable[str]):
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if root_left < root_right:
            self.parent[root_right] = root_left
        else:
            self.parent[root_left] = root_right


def _normalize(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _hash_payload(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        dict(sorted(payload.items())),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _top_context_terms(counter: Counter[str], *, limit: int = MAX_CONTEXT_TERMS) -> Tuple[str, ...]:
    return tuple(
        term
        for term, _ in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]
    )


def _overlap_ratio(left: Set[str], right: Set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / float(len(union))


def _term_state_for_surface(
    surface_form: str,
    *,
    contexts: Counter[str],
    support_count: int,
    doc_ids: Iterable[UUID],
    node_ids: Iterable[UUID],
) -> _TermState:
    normalized = _normalize(surface_form)
    canonicalized = canonicalize_text(normalized)
    signature = build_semantic_signature(normalized)
    stem_roots = {
        part.split("|", 1)[0].replace("stem:", "", 1)
        for part in signature.stem_families
        if "|" in part
    }
    return _TermState(
        support_count=int(support_count),
        doc_ids=set(doc_ids),
        contexts=Counter(contexts),
        node_ids=set(node_ids),
        lemma_tokens=set(canonicalized.lemma_tokens),
        alias_families=set(signature.alias_families),
        transliterated_tokens=set(signature.transliterated_tokens),
        stem_roots=stem_roots,
        relation_cues=set(signature.relation_cues),
        value_cues=set(signature.value_cues),
        temporal_cues=set(signature.temporal_cues),
    )


def _bundle_similarity(left_term: str, left: _TermState, right_term: str, right: _TermState) -> float:
    left_tokens = set(left_term.split())
    right_tokens = set(right_term.split())
    token_overlap = _overlap_ratio(left_tokens, right_tokens)
    lemma_overlap = _overlap_ratio(left.lemma_tokens, right.lemma_tokens)
    context_left = set(_top_context_terms(left.contexts))
    context_right = set(_top_context_terms(right.contexts))
    context_overlap = _overlap_ratio(context_left, context_right)
    stem_overlap = _overlap_ratio(left.stem_roots, right.stem_roots)
    translit_overlap = _overlap_ratio(
        left.transliterated_tokens | left_tokens,
        right.transliterated_tokens | right_tokens,
    )
    cue_overlap = max(
        _overlap_ratio(left.relation_cues, right.relation_cues),
        _overlap_ratio(left.value_cues, right.value_cues),
        _overlap_ratio(left.temporal_cues, right.temporal_cues),
        _overlap_ratio(left.alias_families, right.alias_families),
    )

    score = (
        token_overlap * 0.28
        + lemma_overlap * 0.18
        + context_overlap * 0.30
        + stem_overlap * 0.12
        + translit_overlap * 0.07
        + cue_overlap * 0.05
    )
    shared_context_count = len(context_left & context_right)
    if shared_context_count >= MIN_CONTEXT_OVERLAP:
        score += 0.08
    if left_tokens and right_tokens and (
        left_tokens <= right_tokens or right_tokens <= left_tokens
    ):
        score += 0.08
    if left.lemma_tokens and right.lemma_tokens and left.lemma_tokens == right.lemma_tokens:
        score += 0.12
    return min(0.98, score)


def _bundle_key(pack: str, members: Sequence[str]) -> str:
    digest = hashlib.sha256("||".join(sorted(members)).encode("utf-8")).hexdigest()[:16]
    return f"bundle:{pack}:{digest}"


def _representative_term(members: Sequence[str], term_states: Mapping[str, _TermState]) -> str:
    return sorted(
        members,
        key=lambda item: (
            -int(term_states[item].support_count),
            -len(item.split()),
            -len(item),
            item,
        ),
    )[0]


def learn_semantic_memory_bundles(
    docs: Sequence[DomainDocument],
    *,
    domain_pack: Optional[str] = None,
    support_nodes: Optional[Mapping[str, Sequence[object]]] = None,
    max_terms: int = MAX_TERMS,
    max_bundles: int = MAX_BUNDLES,
) -> SemanticMemoryLearningResult:
    """Learn graph-local semantic memory bundles from uploaded documents."""
    if not docs:
        return SemanticMemoryLearningResult((), (), ())

    term_support: Counter[str] = Counter()
    term_contexts: Dict[str, Counter[str]] = defaultdict(Counter)
    term_doc_ids: Dict[str, Set[UUID]] = defaultdict(set)
    term_node_ids: Dict[str, Set[UUID]] = defaultdict(set)

    for doc in docs:
        phrase_terms = sorted(set(extract_phrase_terms(doc.canonical_text)))[: max_terms]
        for term in phrase_terms:
            normalized = _normalize(term)
            if not normalized:
                continue
            term_support[normalized] += 1
            term_doc_ids[normalized].add(doc.node_id)
            term_node_ids[normalized].add(doc.node_id)
            token_set = set(normalized.split())
            for ctx in set(doc.lemma_tokens):
                if ctx and ctx not in token_set:
                    term_contexts[normalized][ctx] += 1

    if support_nodes:
        for term, node_ids in support_nodes.items():
            normalized = _normalize(term)
            if not normalized:
                continue
            for node_id in node_ids:
                if isinstance(node_id, UUID):
                    term_node_ids[normalized].add(node_id)
                else:
                    try:
                        term_node_ids[normalized].add(UUID(str(node_id)))
                    except Exception:
                        continue

    ranked_terms = [
        term
        for term, _ in sorted(term_support.items(), key=lambda item: (-item[1], item[0]))[:max_terms]
        if term_support[term] > 0
    ]
    if len(ranked_terms) < 2:
        return SemanticMemoryLearningResult((), (), ())

    term_states = {
        term: _term_state_for_surface(
            term,
            contexts=term_contexts[term],
            support_count=term_support[term],
            doc_ids=term_doc_ids[term],
            node_ids=term_node_ids[term],
        )
        for term in ranked_terms
    }

    alias_pairs: Dict[Tuple[str, str], float] = {}
    for candidate in mine_alias_candidates(doc.text for doc in docs):
        surface = _normalize(candidate.surface_form)
        canonical = _normalize(candidate.canonical_form)
        if surface in term_states and canonical in term_states and surface != canonical:
            pair = tuple(sorted((surface, canonical)))
            alias_pairs[pair] = max(alias_pairs.get(pair, 0.0), float(candidate.score or 0.9))

    uf = _UnionFind(ranked_terms)
    pair_scores: Dict[Tuple[str, str], float] = {}
    for left_index, left_term in enumerate(ranked_terms):
        left_state = term_states[left_term]
        for right_term in ranked_terms[left_index + 1 :]:
            right_state = term_states[right_term]
            pair = tuple(sorted((left_term, right_term)))
            alias_score = alias_pairs.get(pair)
            if alias_score is not None:
                score = max(0.9, alias_score)
            else:
                score = _bundle_similarity(left_term, left_state, right_term, right_state)
            if score < SIMILARITY_THRESHOLD:
                continue
            pair_scores[pair] = score
            uf.union(left_term, right_term)

    grouped: Dict[str, List[str]] = defaultdict(list)
    for term in ranked_terms:
        grouped[uf.find(term)].append(term)

    selected_groups = [
        sorted(set(members))
        for _root, members in sorted(grouped.items(), key=lambda item: item[0])
        if len(set(members)) >= 2
    ][:max_bundles]
    if not selected_groups:
        return SemanticMemoryLearningResult((), (), ())

    pack = _normalize(domain_pack or "") or "autonomous"
    lexicon_rows: List[Dict[str, object]] = []
    source_rows: List[Dict[str, object]] = []
    semantic_edges: List[SemanticEdgeProposal] = []

    for members in selected_groups:
        trimmed_members = members[:MAX_BUNDLE_MEMBERS]
        representative = _representative_term(trimmed_members, term_states)
        bundle_key = _bundle_key(pack, trimmed_members)
        bundle_contexts: Counter[str] = Counter()
        bundle_nodes: List[UUID] = []
        bundle_pair_scores: List[float] = []

        for term in trimmed_members:
            bundle_contexts.update(term_states[term].contexts)
            bundle_nodes.extend(sorted(term_states[term].node_ids, key=lambda item: str(item))[:2])

        for left_index, left_term in enumerate(trimmed_members):
            for right_term in trimmed_members[left_index + 1 :]:
                pair = tuple(sorted((left_term, right_term)))
                if pair in pair_scores:
                    bundle_pair_scores.append(pair_scores[pair])

        average_similarity = (
            sum(bundle_pair_scores) / len(bundle_pair_scores) if bundle_pair_scores else 0.8
        )
        shared_context_terms = list(_top_context_terms(bundle_contexts))
        bundle_score = min(
            0.98,
            0.68
            + min(0.12, 0.03 * max(0, len(trimmed_members) - 1))
            + min(0.12, average_similarity * 0.16)
            + min(0.06, len(shared_context_terms) * 0.01),
        )
        bundle_meta = {
            "source": "semantic_memory_learning",
            "bundle_key": bundle_key,
            "bundle_members": list(trimmed_members),
            "bundle_size": len(trimmed_members),
            "shared_context_terms": shared_context_terms,
            "average_similarity": round(float(average_similarity), 6),
            "learned_from": "uploads",
        }

        lexicon_rows.append(
            {
                "surface_form": representative,
                "canonical_form": representative,
                "kind": "concept_bundle",
                "domain_pack": pack,
                "support_count": sum(term_states[item].support_count for item in trimmed_members),
                "score": bundle_score,
                "meta": dict(bundle_meta),
            }
        )

        for term in trimmed_members:
            if term == representative:
                continue
            pair = tuple(sorted((term, representative)))
            member_score = pair_scores.get(pair, average_similarity)
            lexicon_rows.append(
                {
                    "surface_form": term,
                    "canonical_form": representative,
                    "kind": "semantic_paraphrase",
                    "domain_pack": pack,
                    "support_count": term_states[term].support_count,
                    "score": min(0.97, max(0.74, member_score)),
                    "meta": {
                        **bundle_meta,
                        "member_term": term,
                        "representative_term": representative,
                    },
                }
            )

        unique_nodes = []
        seen_nodes: Set[UUID] = set()
        for node_id in bundle_nodes:
            if node_id in seen_nodes:
                continue
            seen_nodes.add(node_id)
            unique_nodes.append(node_id)

        if unique_nodes:
            source_payload = {
                "bundle_key": bundle_key,
                "domain_pack": pack,
                "representative": representative,
                "members": list(trimmed_members),
                "shared_context_terms": shared_context_terms,
            }
            source_rows.append(
                {
                    "source_id": bundle_key,
                    "source_kind": "semantic_bundle",
                    "source_hash": _hash_payload(source_payload),
                    "meta": source_payload,
                }
            )

        representative_node = unique_nodes[0] if unique_nodes else None
        if representative_node is not None:
            for member_node in unique_nodes[1:]:
                if member_node == representative_node:
                    continue
                semantic_edges.append(
                    SemanticEdgeProposal(
                        src_node_id=representative_node,
                        dst_node_id=member_node,
                        semantic_type="semantic_bundle",
                        semantic_weight=min(0.9, max(0.66, bundle_score - 0.04)),
                        meta={
                            "bundle_key": bundle_key,
                            "representative_term": representative,
                            "members": list(trimmed_members),
                            "source": "semantic_memory_learning",
                        },
                    )
                )

    lexicon_rows.sort(
        key=lambda row: (
            str(row["surface_form"]),
            str(row["kind"]),
            str(row["canonical_form"]),
        )
    )
    source_rows.sort(key=lambda row: str(row["source_id"]))
    semantic_edges.sort(
        key=lambda row: (
            str(row.src_node_id),
            str(row.dst_node_id),
            row.semantic_type,
        )
    )
    return SemanticMemoryLearningResult(
        tuple(lexicon_rows),
        tuple(source_rows),
        tuple(semantic_edges),
    )


__all__ = [
    "SemanticEdgeProposal",
    "SemanticMemoryLearningResult",
    "learn_semantic_memory_bundles",
]
