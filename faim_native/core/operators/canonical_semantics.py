"""Deterministic canonical semantics mining and edge materialization."""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Set, Tuple
from uuid import UUID

try:
    from faim.Faim_Native.lexical.alias_miner import mine_alias_candidates
    from faim.Faim_Native.lexical.canonicalizer import canonicalize_text
    from faim.Faim_Native.lexical.phrase_patterns import extract_phrase_surface_map
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from lexical.alias_miner import mine_alias_candidates
    from lexical.canonicalizer import canonicalize_text
    from lexical.phrase_patterns import extract_phrase_surface_map


EPSILON = 1e-9
MIN_TERM_DF = 2
MIN_DISTRIBUTIONAL_SUPPORT = 1
MIN_CONTEXT_OVERLAP = 0.35
MIN_PMI = 0.10
MAX_CONTEXT_TERMS = 24
MAX_CANONICAL_EDGES_PER_NODE = 8


@dataclass(frozen=True)
class CanonicalDocument:
    """Canonical corpus document aligned to one graph node."""

    node_id: UUID
    raw_id: str
    anchor_json: Dict[str, object]
    surface_text: str
    lemma_tokens: Tuple[str, ...]
    phrase_labels: Tuple[str, ...]
    phrase_surface_map: Dict[str, str]


@dataclass(frozen=True)
class CanonicalSemanticsBuild:
    """Canonical semantics artifacts built for a graph."""

    term_stats: Tuple[Dict[str, object], ...]
    lexicon_entries: Tuple[Dict[str, object], ...]
    edge_specs: Tuple[Dict[str, object], ...]


def build_canonical_document(
    *,
    node_id: UUID,
    raw_id: str,
    anchor_json: Dict[str, object],
    text: str,
) -> CanonicalDocument:
    """Canonicalize one extracted block for mining."""
    canonical = canonicalize_text(text)
    return CanonicalDocument(
        node_id=node_id,
        raw_id=str(raw_id),
        anchor_json=dict(anchor_json or {}),
        surface_text=text,
        lemma_tokens=tuple(canonical.lemma_tokens),
        phrase_labels=tuple(canonical.phrase_labels),
        phrase_surface_map=extract_phrase_surface_map(list(canonical.surface_tokens)),
    )


def _top_context_terms(counter: Counter[str], limit: int = MAX_CONTEXT_TERMS) -> Dict[str, int]:
    pairs = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return dict(pairs[:limit])


def _choose_canonical_term(term_a: str, term_b: str, df: Mapping[str, int]) -> str:
    if df.get(term_a, 0) > df.get(term_b, 0):
        return term_a
    if df.get(term_b, 0) > df.get(term_a, 0):
        return term_b
    return min(term_a, term_b)


def _context_overlap(a_terms: Set[str], b_terms: Set[str]) -> float:
    if not a_terms and not b_terms:
        return 0.0
    return len(a_terms & b_terms) / max(len(a_terms | b_terms), 1)


def _normalized_score(*values: float) -> float:
    total = sum(max(0.0, min(1.0, value)) for value in values)
    return max(0.0, min(1.0, total / max(len(values), 1)))


def _mine_term_stats(
    docs: Sequence[CanonicalDocument],
) -> Tuple[List[Dict[str, object]], Dict[str, int], Dict[str, Counter[str]], Dict[Tuple[str, str], int]]:
    doc_count = len(docs)
    df = Counter()
    cf = Counter()
    context = defaultdict(Counter)
    co_docs = Counter()
    phrase_df = Counter()
    phrase_cf = Counter()

    for doc in docs:
        unique_terms = sorted(set(doc.lemma_tokens))
        for term in unique_terms:
            df[term] += 1
        for term in doc.lemma_tokens:
            cf[term] += 1
        for idx, term in enumerate(unique_terms):
            others = unique_terms[:idx] + unique_terms[idx + 1 :]
            context[term].update(others)
        for idx, left in enumerate(unique_terms):
            for right in unique_terms[idx + 1 :]:
                co_docs[(left, right)] += 1

        unique_labels = sorted(set(doc.phrase_labels))
        for label in unique_labels:
            phrase_df[label] += 1
        for label in doc.phrase_labels:
            phrase_cf[label] += 1

    rows: List[Dict[str, object]] = []
    for term in sorted(df):
        rows.append(
            {
                "channel": "term",
                "term": term,
                "df": df[term],
                "cf": cf[term],
                "doc_count": doc_count,
                "context_terms": _top_context_terms(context[term]),
            }
        )
    for label in sorted(phrase_df):
        rows.append(
            {
                "channel": "phrase",
                "term": label,
                "df": phrase_df[label],
                "cf": phrase_cf[label],
                "doc_count": doc_count,
                "context_terms": {},
            }
        )

    return rows, dict(df), context, dict(co_docs)


def _mine_phrase_lexicon(docs: Sequence[CanonicalDocument]) -> List[Dict[str, object]]:
    support: Counter[Tuple[str, str]] = Counter()
    for doc in docs:
        for surface, canonical in doc.phrase_surface_map.items():
            support[(surface, canonical)] += 1
    rows: List[Dict[str, object]] = []
    for (surface, canonical), count in sorted(support.items(), key=lambda item: (item[0][0], item[0][1])):
        rows.append(
            {
                "surface_form": surface,
                "canonical_form": canonical,
                "kind": "phrase_pattern",
                "support_count": count,
                "score": 1.0,
                "meta": {"rule_based": True},
            }
        )
    return rows


def _mine_distributional_lexicon(
    *,
    doc_count: int,
    df: Mapping[str, int],
    context: Mapping[str, Counter[str]],
    co_docs: Mapping[Tuple[str, str], int],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    vocab = [term for term in sorted(df) if df.get(term, 0) >= MIN_TERM_DF]
    for idx, left in enumerate(vocab):
        left_ctx = set(_top_context_terms(context.get(left, Counter())).keys())
        if not left_ctx:
            continue
        for right in vocab[idx + 1 :]:
            pair = (left, right)
            pair_support = int(co_docs.get(pair, 0))
            if pair_support < MIN_DISTRIBUTIONAL_SUPPORT:
                continue
            if pair_support >= min(df.get(left, 0), df.get(right, 0)):
                # Terms that always co-occur behave more like collocations than
                # interchangeable distributional variants.
                continue

            right_ctx = set(_top_context_terms(context.get(right, Counter())).keys())
            overlap = _context_overlap(left_ctx, right_ctx)
            if overlap < MIN_CONTEXT_OVERLAP:
                continue

            pmi = math.log(
                ((pair_support + EPSILON) * max(doc_count, 1))
                / ((df[left] + EPSILON) * (df[right] + EPSILON))
            )
            if pmi < MIN_PMI:
                continue

            canonical = _choose_canonical_term(left, right, df)
            surface = right if canonical == left else left
            score = _normalized_score(
                min(1.0, pmi / 1.25),
                overlap,
                min(1.0, pair_support / max(df.get(surface, 1), 1)),
            )
            rows.append(
                {
                    "surface_form": surface,
                    "canonical_form": canonical,
                    "kind": "distributional_synonym",
                    "support_count": pair_support,
                    "score": round(score, 6),
                    "meta": {
                        "pmi": round(pmi, 6),
                        "context_overlap": round(overlap, 6),
                        "surface_df": int(df.get(surface, 0)),
                        "canonical_df": int(df.get(canonical, 0)),
                    },
                }
            )
    best_by_surface: Dict[str, Dict[str, object]] = {}
    for row in rows:
        surface = str(row["surface_form"])
        existing = best_by_surface.get(surface)
        candidate_key = (
            float(row.get("score", 0.0)),
            int(row.get("support_count", 0)),
            int(dict(row.get("meta", {})).get("canonical_df", 0)),
            str(row.get("canonical_form", "")),
        )
        if existing is None:
            best_by_surface[surface] = row
            continue
        existing_key = (
            float(existing.get("score", 0.0)),
            int(existing.get("support_count", 0)),
            int(dict(existing.get("meta", {})).get("canonical_df", 0)),
            str(existing.get("canonical_form", "")),
        )
        if candidate_key > existing_key:
            best_by_surface[surface] = row
    return [best_by_surface[key] for key in sorted(best_by_surface)]


def _mine_alias_lexicon(docs: Sequence[CanonicalDocument]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for candidate in mine_alias_candidates(doc.surface_text for doc in docs):
        rows.append(
            {
                "surface_form": candidate.surface_form,
                "canonical_form": candidate.canonical_form,
                "kind": candidate.kind,
                "support_count": candidate.support_count,
                "score": candidate.score,
                "meta": dict(candidate.meta),
            }
        )
    return rows


def _build_variant_groups(lexicon_rows: Sequence[Mapping[str, object]]) -> Dict[str, Set[str]]:
    groups: Dict[str, Set[str]] = defaultdict(set)
    for row in lexicon_rows:
        kind = str(row.get("kind", ""))
        if kind not in {"distributional_synonym", "alias", "acronym"}:
            continue
        surface = str(row.get("surface_form", ""))
        canonical = str(row.get("canonical_form", ""))
        if not surface or not canonical:
            continue
        groups[canonical].add(surface)
        groups[canonical].add(canonical)
    return {key: set(sorted(values)) for key, values in sorted(groups.items(), key=lambda item: item[0])}


def _materialize_canonical_edges(
    docs: Sequence[CanonicalDocument],
    lexicon_rows: Sequence[Mapping[str, object]],
) -> List[Dict[str, object]]:
    docs_by_node = {doc.node_id: doc for doc in docs}
    variant_groups = _build_variant_groups(lexicon_rows)
    variant_postings: Dict[str, Dict[str, Set[UUID]]] = defaultdict(lambda: defaultdict(set))
    phrase_postings: Dict[str, Dict[str, Set[UUID]]] = defaultdict(lambda: defaultdict(set))

    for doc in docs:
        terms = set(doc.lemma_tokens)
        for canonical, variants in variant_groups.items():
            present = sorted(term for term in variants if term in terms)
            for variant in present:
                variant_postings[canonical][variant].add(doc.node_id)
        for surface, label in doc.phrase_surface_map.items():
            phrase_postings[label][surface].add(doc.node_id)

    pair_scores: Dict[Tuple[str, UUID, UUID], float] = defaultdict(float)
    pair_meta: Dict[Tuple[str, UUID, UUID], Dict[str, object]] = {}

    for canonical, variants in sorted(variant_postings.items(), key=lambda item: item[0]):
        variant_items = [(variant, sorted(node_ids, key=str)) for variant, node_ids in sorted(variants.items(), key=lambda item: item[0])]
        for i, (left_variant, left_nodes) in enumerate(variant_items):
            for right_variant, right_nodes in variant_items[i + 1 :]:
                for left_node in left_nodes:
                    for right_node in right_nodes:
                        a, b = sorted((left_node, right_node), key=str)
                        if a == b:
                            continue
                        key = ("distributional_synonym", a, b)
                        pair_scores[key] += 1.0
                        pair_meta[key] = {
                            "canonical_form": canonical,
                            "left_variant": left_variant,
                            "right_variant": right_variant,
                        }

    for label, surfaces in sorted(phrase_postings.items(), key=lambda item: item[0]):
        surface_items = [(surface, sorted(node_ids, key=str)) for surface, node_ids in sorted(surfaces.items(), key=lambda item: item[0])]
        for i, (left_surface, left_nodes) in enumerate(surface_items):
            for right_surface, right_nodes in surface_items[i + 1 :]:
                for left_node in left_nodes:
                    for right_node in right_nodes:
                        a, b = sorted((left_node, right_node), key=str)
                        if a == b:
                            continue
                        key = ("paraphrase", a, b)
                        pair_scores[key] += 1.0
                        pair_meta[key] = {
                            "canonical_form": label,
                            "left_surface": left_surface,
                            "right_surface": right_surface,
                        }

    per_node_rankings: Dict[Tuple[str, UUID], List[Tuple[UUID, float, Dict[str, object]]]] = defaultdict(list)
    for (kind, left_node, right_node), raw_score in sorted(pair_scores.items(), key=lambda item: (item[0][0], str(item[0][1]), str(item[0][2]))):
        if kind == "distributional_synonym":
            weight = min(0.85, 0.60 + 0.08 * raw_score)
        else:
            weight = min(0.82, 0.62 + 0.10 * raw_score)
        meta = dict(pair_meta[(kind, left_node, right_node)])
        meta["evidence_count"] = int(raw_score)
        per_node_rankings[(kind, left_node)].append((right_node, weight, meta))
        per_node_rankings[(kind, right_node)].append((left_node, weight, meta))

    allowed_pairs: Set[Tuple[str, UUID, UUID]] = set()
    for (kind, node_id), neighbors in per_node_rankings.items():
        ranked = sorted(neighbors, key=lambda item: (-item[1], str(item[0])))
        for other_node, _weight, _meta in ranked[:MAX_CANONICAL_EDGES_PER_NODE]:
            a, b = sorted((node_id, other_node), key=str)
            allowed_pairs.add((kind, a, b))

    rows: List[Dict[str, object]] = []
    for key in sorted(allowed_pairs, key=lambda item: (item[0], str(item[1]), str(item[2]))):
        kind, left_node, right_node = key
        raw_score = pair_scores.get(key, 0.0)
        if kind == "distributional_synonym":
            weight = min(0.85, 0.60 + 0.08 * raw_score)
        else:
            weight = min(0.82, 0.62 + 0.10 * raw_score)
        rows.append(
            {
                "src_node_id": left_node,
                "dst_node_id": right_node,
                "kind": kind,
                "semantic_weight": round(weight, 6),
                "meta": dict(pair_meta.get(key, {})),
            }
        )
    return rows


def build_canonical_semantics(docs: Sequence[CanonicalDocument]) -> CanonicalSemanticsBuild:
    """Build graph-scoped canonical stats, lexicon, and additive semantic edges."""
    if not docs:
        return CanonicalSemanticsBuild(term_stats=(), lexicon_entries=(), edge_specs=())

    term_stats, df, context, co_docs = _mine_term_stats(docs)
    lexicon_rows: List[Dict[str, object]] = []
    lexicon_rows.extend(_mine_alias_lexicon(docs))
    lexicon_rows.extend(_mine_phrase_lexicon(docs))
    lexicon_rows.extend(
        _mine_distributional_lexicon(
            doc_count=len(docs),
            df=df,
            context=context,
            co_docs=co_docs,
        )
    )

    deduped_lexicon: Dict[Tuple[str, str, str], Dict[str, object]] = {}
    for row in lexicon_rows:
        key = (
            str(row["surface_form"]),
            str(row["canonical_form"]),
            str(row["kind"]),
        )
        existing = deduped_lexicon.get(key)
        if existing is None or float(row.get("score", 0.0)) > float(existing.get("score", 0.0)):
            deduped_lexicon[key] = dict(row)
    ordered_lexicon = [deduped_lexicon[key] for key in sorted(deduped_lexicon)]
    edge_specs = _materialize_canonical_edges(docs, ordered_lexicon)

    return CanonicalSemanticsBuild(
        term_stats=tuple(term_stats),
        lexicon_entries=tuple(ordered_lexicon),
        edge_specs=tuple(edge_specs),
    )


__all__ = [
    "CanonicalDocument",
    "CanonicalSemanticsBuild",
    "build_canonical_document",
    "build_canonical_semantics",
]
