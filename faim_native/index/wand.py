"""Deterministic WAND-style shortlist pruning for FAIM sparse retrieval.

This is intentionally conservative: it preserves deterministic ordering and
uses graph-local sparse statistics only. It computes per-term upper bounds and
scores only documents touched by query postings, which is already sublinear
relative to a full scan over all graph documents.
"""

from __future__ import annotations

from typing import Dict, Mapping, Sequence, Tuple
from uuid import UUID

try:
    from faim.Faim_Native.encoding.representation_v2 import RepresentationV2
    from faim.Faim_Native.index.inverted_index import InvertedIndex
except (ImportError, RuntimeError):
    from encoding.representation_v2 import RepresentationV2
    from index.inverted_index import InvertedIndex


def _query_terms(query_repr: RepresentationV2) -> Dict[str, Sequence[str]]:
    return {
        "word": tuple(sorted(query_repr.word_counts.keys())),
        "phrase": tuple(sorted(query_repr.phrase_counts.keys())),
        "skip": tuple(sorted(query_repr.skip_counts.keys())),
        "entity": tuple(sorted(set(query_repr.entity_tokens))),
        "time": tuple(sorted(set(query_repr.time_tokens))),
        "layout": tuple(sorted(set(query_repr.layout_tokens))),
    }


def estimate_term_upper_bounds(
    index: InvertedIndex,
    query_repr: RepresentationV2,
    stats_by_channel: Mapping[str, Mapping[str, object]],
) -> Dict[Tuple[str, str], float]:
    """Compute deterministic upper bounds per query term."""
    bounds: Dict[Tuple[str, str], float] = {}
    for channel, terms in _query_terms(query_repr).items():
        channel_stats = stats_by_channel.get(channel, {})
        doc_count = max(int(channel_stats.get("doc_count", 0)), 1)
        df_map = dict(channel_stats.get("df_map", {}))
        for term in terms:
            postings = index.postings_for(channel, term)
            if not postings:
                continue
            max_tf = max(int(post.tf) for post in postings)
            df = max(int(df_map.get(term, 0)), 0)
            # Conservative deterministic bound in [0,1]
            idf = 1.0 if df <= 0 else min(1.0, 0.1 + ((doc_count - df) / doc_count))
            tf_bound = min(1.0, max_tf / max(max_tf, 1))
            bounds[(channel, term)] = round(min(1.0, idf * tf_bound), 6)
    return bounds


def block_max_wand_shortlist(
    index: InvertedIndex,
    query_repr: RepresentationV2,
    stats_by_channel: Mapping[str, Mapping[str, object]],
    *,
    k: int = 200,
    max_candidates: int = 1000,
) -> Sequence[Tuple[UUID, float]]:
    """Deterministic shortlist using sparse postings and conservative bounds."""
    term_bounds = estimate_term_upper_bounds(index, query_repr, stats_by_channel)
    if not term_bounds:
        return ()

    touched_scores = index.score_matching(query_repr, stats_by_channel)
    if not touched_scores:
        return ()

    bound_budget = sum(term_bounds.values())
    ranked = sorted(
        (
            (node_id, min(1.0, score), min(1.0, score + 0.05 * bound_budget))
            for node_id, score in touched_scores.items()
        ),
        key=lambda item: (-item[2], -item[1], str(item[0])),
    )
    shortlisted = [(node_id, score) for node_id, score, _bound in ranked[:max_candidates]]
    shortlisted.sort(key=lambda item: (-item[1], str(item[0])))
    return tuple(shortlisted[:k])


__all__ = ["estimate_term_upper_bounds", "block_max_wand_shortlist"]
