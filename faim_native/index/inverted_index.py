"""Deterministic sparse inverted index for Representation V2.

This is an additive acceleration layer over graph-scoped Representation V2 rows.
It never becomes the source of truth; callers can always fall back to exact repo
scans. Posting order is stable by node_id to preserve deterministic behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple
from uuid import UUID

try:
    from faim.Faim_Native.core.query.lexical_scorer import compute_lexical_score
    from faim.Faim_Native.encoding.representation_v2 import RepresentationV2
except (ImportError, RuntimeError):
    from core.query.lexical_scorer import compute_lexical_score
    from encoding.representation_v2 import RepresentationV2


CHANNELS: Tuple[str, ...] = ("word", "phrase", "skip", "entity", "time", "layout")


@dataclass(frozen=True)
class Posting:
    """Sparse posting entry for a graph-local term."""

    node_id: UUID
    tf: int


@dataclass(frozen=True)
class IndexedDocument:
    """In-memory sparse representation for index scoring."""

    node_id: UUID
    representation: RepresentationV2


class InvertedIndex:
    """Deterministic sparse inverted index over Representation V2 rows."""

    def __init__(
        self,
        documents: Mapping[UUID, RepresentationV2],
        postings: Mapping[str, Mapping[str, Sequence[Posting]]],
    ) -> None:
        self._documents = dict(documents)
        self._postings = {
            str(channel): {
                str(term): tuple(sorted(entries, key=lambda item: str(item.node_id)))
                for term, entries in dict(channel_postings).items()
            }
            for channel, channel_postings in dict(postings).items()
        }

    @classmethod
    def build(
        cls,
        rows: Iterable[object],
    ) -> "InvertedIndex":
        documents: Dict[UUID, RepresentationV2] = {}
        postings: Dict[str, Dict[str, List[Posting]]] = {channel: {} for channel in CHANNELS}

        for row in rows:
            repr_data = RepresentationV2.from_dict(
                {
                    "repr_hash": getattr(row, "repr_hash", ""),
                    "normalized_text": getattr(row, "normalized_text", "") or "",
                    "word_counts": getattr(row, "word_counts", {}) or {},
                    "phrase_counts": getattr(row, "phrase_counts", {}) or {},
                    "skip_counts": getattr(row, "skip_counts", {}) or {},
                    "entity_tokens": getattr(row, "entity_tokens", []) or [],
                    "time_tokens": getattr(row, "time_tokens", []) or [],
                    "layout_tokens": getattr(row, "layout_tokens", []) or [],
                    "channel_lengths": getattr(row, "channel_lengths", {}) or {},
                }
            )
            node_id = getattr(row, "node_id")
            documents[node_id] = repr_data

            for term, tf in repr_data.word_counts.items():
                postings["word"].setdefault(term, []).append(Posting(node_id=node_id, tf=int(tf)))
            for term, tf in repr_data.phrase_counts.items():
                postings["phrase"].setdefault(term, []).append(
                    Posting(node_id=node_id, tf=int(tf))
                )
            for term, tf in repr_data.skip_counts.items():
                postings["skip"].setdefault(term, []).append(Posting(node_id=node_id, tf=int(tf)))
            for term in repr_data.entity_tokens:
                postings["entity"].setdefault(str(term), []).append(
                    Posting(node_id=node_id, tf=1)
                )
            for term in repr_data.time_tokens:
                postings["time"].setdefault(str(term), []).append(Posting(node_id=node_id, tf=1))
            for term in repr_data.layout_tokens:
                postings["layout"].setdefault(str(term), []).append(
                    Posting(node_id=node_id, tf=1)
                )

        return cls(documents=documents, postings=postings)

    @property
    def documents(self) -> Mapping[UUID, RepresentationV2]:
        return self._documents

    def postings_for(self, channel: str, term: str) -> Sequence[Posting]:
        return self._postings.get(channel, {}).get(term, ())

    def matching_node_ids(self, query_repr: RepresentationV2) -> List[UUID]:
        seen = set()
        matched: List[UUID] = []
        channel_terms = {
            "word": sorted(query_repr.word_counts.keys()),
            "phrase": sorted(query_repr.phrase_counts.keys()),
            "skip": sorted(query_repr.skip_counts.keys()),
            "entity": sorted(set(query_repr.entity_tokens)),
            "time": sorted(set(query_repr.time_tokens)),
            "layout": sorted(set(query_repr.layout_tokens)),
        }

        for channel in CHANNELS:
            for term in channel_terms[channel]:
                for posting in self.postings_for(channel, term):
                    if posting.node_id in seen:
                        continue
                    seen.add(posting.node_id)
                    matched.append(posting.node_id)

        matched.sort(key=str)
        return matched

    def score_matching(
        self,
        query_repr: RepresentationV2,
        stats_by_channel: Mapping[str, Mapping[str, object]],
    ) -> Dict[UUID, float]:
        node_ids = self.matching_node_ids(query_repr)
        scores: Dict[UUID, float] = {}
        for node_id in node_ids:
            doc_repr = self._documents[node_id]
            score, _components = compute_lexical_score(query_repr, doc_repr, stats_by_channel)
            scores[node_id] = score
        return scores

    def top_k(
        self,
        query_repr: RepresentationV2,
        stats_by_channel: Mapping[str, Mapping[str, object]],
        k: int = 200,
    ) -> List[Tuple[UUID, float]]:
        scores = self.score_matching(query_repr, stats_by_channel)
        ranked = sorted(scores.items(), key=lambda item: (-item[1], str(item[0])))
        return ranked[:k]


__all__ = ["Posting", "IndexedDocument", "InvertedIndex", "CHANNELS"]
