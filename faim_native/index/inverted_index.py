"""Deterministic sparse inverted index for Representation V2.

This is an additive acceleration layer over graph-scoped Representation V2 rows.
It never becomes the source of truth; callers can always fall back to exact repo
scans. Posting order is stable by node_id to preserve deterministic behavior.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from uuid import UUID

try:
    from faim.Faim_Native.core.query.lexical_scorer import compute_lexical_score
    from faim.Faim_Native.encoding.porter_stemmer import stem as _porter_stem
    from faim.Faim_Native.encoding.representation_v2 import RepresentationV2
except (ImportError, RuntimeError):
    from core.query.lexical_scorer import compute_lexical_score
    from encoding.porter_stemmer import stem as _porter_stem
    from encoding.representation_v2 import RepresentationV2


CHANNELS: Tuple[str, ...] = ("word", "phrase", "skip", "entity", "time", "layout")

_STOPWORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can", "that", "this",
        "these", "those", "it", "its", "they", "their", "them", "we", "our",
        "he", "she", "his", "her", "not", "no", "nor", "so", "than", "too",
        "very", "if", "into", "about", "over", "after", "before", "between",
        "through", "during", "above", "below", "up", "down", "out", "off",
        "such", "only", "also", "more", "most", "other", "some", "any", "all",
        "each", "both", "few", "many", "much", "own", "same",
    }
)
_EXACT_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize_exact(text: str) -> List[str]:
    return [w for w in _EXACT_TOKEN_RE.findall((text or "").lower()) if w not in _STOPWORDS]


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
        self._build_exact_bm25_index()

    def _build_exact_bm25_index(self) -> None:
        """Build collision-free stemmed + raw + bigram BM25+ postings in RAM."""
        self._stem_postings: Dict[str, List[Tuple[UUID, int]]] = defaultdict(list)
        self._raw_postings: Dict[str, List[Tuple[UUID, int]]] = defaultdict(list)
        self._bi_postings: Dict[str, List[Tuple[UUID, int]]] = defaultdict(list)
        self._stem_dl: Dict[UUID, int] = {}
        self._raw_dl: Dict[UUID, int] = {}
        self._bi_dl: Dict[UUID, int] = {}

        for node_id, repr_data in self._documents.items():
            text = (repr_data.normalized_text or "").strip()
            if not text:
                continue
            raw_toks = _tokenize_exact(text)
            if not raw_toks:
                continue
            stem_toks = [_porter_stem(w) for w in raw_toks]
            bi_toks = [
                f"{stem_toks[i]}_{stem_toks[i + 1]}" for i in range(len(stem_toks) - 1)
            ]
            self._raw_dl[node_id] = len(raw_toks)
            self._stem_dl[node_id] = len(stem_toks)
            self._bi_dl[node_id] = len(bi_toks)
            for term, tf in Counter(stem_toks).items():
                self._stem_postings[term].append((node_id, tf))
            for term, tf in Counter(raw_toks).items():
                self._raw_postings[term].append((node_id, tf))
            for term, tf in Counter(bi_toks).items():
                self._bi_postings[term].append((node_id, tf))

        n_docs = len(self._stem_dl)
        self._exact_doc_count = n_docs
        self._avg_stem_dl = sum(self._stem_dl.values()) / n_docs if n_docs else 1.0
        self._avg_raw_dl = sum(self._raw_dl.values()) / n_docs if n_docs else 1.0
        self._avg_bi_dl = sum(self._bi_dl.values()) / n_docs if n_docs else 1.0

    def has_exact_bm25(self) -> bool:
        return self._exact_doc_count > 0

    def _score_bm25_channel(
        self,
        q_tokens: Sequence[str],
        postings_map: Mapping[str, List[Tuple[UUID, int]]],
        doc_lens: Mapping[UUID, int],
        avg_dl: float,
        *,
        k1: float = 1.2,
        b: float = 0.75,
        delta: float = 0.5,
    ) -> Dict[UUID, float]:
        n_docs = self._exact_doc_count
        if not q_tokens or n_docs <= 0:
            return {}
        avg_len = max(avg_dl, 1.0)
        scores: Dict[UUID, float] = defaultdict(float)
        for term, q_tf in Counter(q_tokens).items():
            postings = postings_map.get(term)
            if not postings:
                continue
            df = len(postings)
            idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
            q_w = 1.0 + math.log(q_tf)
            for node_id, tf in postings:
                dl = doc_lens[node_id]
                denom = tf + k1 * (1.0 - b + b * (dl / avg_len))
                tf_norm = ((tf * (k1 + 1.0)) / max(denom, 1e-9)) + delta
                scores[node_id] += idf * tf_norm * q_w
        return scores

    def score_bm25_fast(
        self,
        query_text: str,
        expanded_terms: Optional[Mapping[str, float]] = None,
    ) -> Dict[UUID, float]:
        """Score matching documents using collision-free stemmed+raw+bigram BM25+
        plus optional concept-expanded bridge terms at decayed weight."""
        if self._exact_doc_count <= 0:
            return {}
        q_raw = _tokenize_exact(query_text)
        if not q_raw and not expanded_terms:
            return {}
        q_stem = [_porter_stem(w) for w in q_raw]
        q_bi = [f"{q_stem[i]}_{q_stem[i + 1]}" for i in range(len(q_stem) - 1)]

        s_stem = (
            self._score_bm25_channel(
                q_stem, self._stem_postings, self._stem_dl, self._avg_stem_dl, delta=0.5
            )
            if q_stem
            else {}
        )
        s_raw = (
            self._score_bm25_channel(
                q_raw, self._raw_postings, self._raw_dl, self._avg_raw_dl, delta=0.0
            )
            if q_raw
            else {}
        )
        s_bi = (
            self._score_bm25_channel(
                q_bi, self._bi_postings, self._bi_dl, self._avg_bi_dl, delta=0.0
            )
            if q_bi
            else {}
        )

        # Concept-aware candidate recall: score 1-2 hop expanded concept terms
        # at capped decayed weight so zero-overlap queries reach Stage-2 MaxSim
        # while exact literal matches still rank higher.
        s_exp: Dict[UUID, float] = defaultdict(float)
        if expanded_terms:
            q_stem_set = set(q_stem)
            exp_weights: Dict[str, float] = {}
            for raw_term, weight in expanded_terms.items():
                w_val = min(0.45, max(0.0, float(weight or 0.0)))
                if w_val <= 0.0:
                    continue
                for tok in _tokenize_exact(str(raw_term)):
                    st = _porter_stem(tok)
                    if st in q_stem_set:
                        continue
                    if w_val > exp_weights.get(st, 0.0):
                        exp_weights[st] = w_val
            if exp_weights:
                n_docs = self._exact_doc_count
                avg_len = max(self._avg_stem_dl, 1.0)
                k1, b, delta = 1.2, 0.75, 0.25
                for st, w_val in exp_weights.items():
                    postings = self._stem_postings.get(st)
                    if not postings:
                        continue
                    df = len(postings)
                    idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
                    for node_id, tf in postings:
                        dl = self._stem_dl[node_id]
                        denom = tf + k1 * (1.0 - b + b * (dl / avg_len))
                        tf_norm = ((tf * (k1 + 1.0)) / max(denom, 1e-9)) + delta
                        s_exp[node_id] += idf * tf_norm * w_val

        if not s_stem and not s_exp:
            return {}

        all_nodes = set(s_stem.keys()) | set(s_exp.keys())
        raw_scores: Dict[UUID, float] = {}
        max_raw = 0.0
        for node_id in all_nodes:
            raw_val = (
                s_stem.get(node_id, 0.0)
                + 0.35 * s_raw.get(node_id, 0.0)
                + 0.25 * s_bi.get(node_id, 0.0)
                + 0.45 * s_exp.get(node_id, 0.0)
            )
            if raw_val <= 0.0:
                continue
            raw_scores[node_id] = raw_val
            if raw_val > max_raw:
                max_raw = raw_val
        if max_raw <= 0.0:
            return {}
        return {
            node_id: round(val / max_raw, 6)
            for node_id, val in raw_scores.items()
        }

    def score_bm25_shortlist(
        self, query_text: str, *, k: int = 200
    ) -> Sequence[Tuple[UUID, float]]:
        """Return deterministic top-k candidates from collision-free BM25+."""
        scores = self.score_bm25_fast(query_text)
        if not scores:
            return ()
        ranked = sorted(scores.items(), key=lambda item: (-item[1], str(item[0])))
        return tuple(ranked[:k])

    @classmethod
    def build(
        cls,
        rows: Iterable[object],
    ) -> "InvertedIndex":
        documents: Dict[UUID, RepresentationV2] = {}
        postings: Dict[str, Dict[str, List[Posting]]] = {
            channel: {} for channel in CHANNELS
        }

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
            node_id = row.node_id
            documents[node_id] = repr_data

            for term, tf in repr_data.word_counts.items():
                postings["word"].setdefault(term, []).append(
                    Posting(node_id=node_id, tf=int(tf))
                )
            for term, tf in repr_data.phrase_counts.items():
                postings["phrase"].setdefault(term, []).append(
                    Posting(node_id=node_id, tf=int(tf))
                )
            for term, tf in repr_data.skip_counts.items():
                postings["skip"].setdefault(term, []).append(
                    Posting(node_id=node_id, tf=int(tf))
                )
            for term in repr_data.entity_tokens:
                postings["entity"].setdefault(str(term), []).append(
                    Posting(node_id=node_id, tf=1)
                )
            for term in repr_data.time_tokens:
                postings["time"].setdefault(str(term), []).append(
                    Posting(node_id=node_id, tf=1)
                )
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
            score, _components = compute_lexical_score(
                query_repr, doc_repr, stats_by_channel
            )
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
