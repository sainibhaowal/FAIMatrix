"""Corpus-Learned PPMI & 2nd-Order Co-Occurrence Bridge (Zero-ML).

Discovers semantic bridges across a tenant's graph without neural models by:
1. Extracting content unigrams and 2-gram concept phrases per document.
2. Computing Shifted Positive Pointwise Mutual Information (PPMI) over document
   co-occurrences.
3. Computing 2nd-order distributional cosine similarity between unit-normalized
   PPMI vectors so terms that never co-occurred in the same document (zero-word-
   overlap paraphrases) are linked through shared context bridges.
4. Persisting top bridges into ``DomainKnowledgeRepo`` and bumping ``graph_version``
   so cached query expansion picks them up in < 0.1 ms.
"""

from __future__ import annotations

import logging
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "being",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "here",
        "him",
        "his",
        "how",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "may",
        "might",
        "more",
        "most",
        "my",
        "no",
        "not",
        "of",
        "on",
        "or",
        "our",
        "out",
        "over",
        "she",
        "should",
        "so",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "under",
        "up",
        "use",
        "used",
        "using",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
    }
)


@dataclass(frozen=True)
class CooccurrenceBridgeResult:
    """Summary of one corpus co-occurrence bridge learning pass."""

    status: str
    documents_scanned: int
    vocab_size: int
    bridges_discovered: int
    bridges_persisted: int
    graph_version: Optional[int] = None
    reason: Optional[str] = None


def _cooccurrence_enabled() -> bool:
    raw = os.getenv("FAIM_COOCCURRENCE_BRIDGE_ENABLED", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _is_valid_token(tok: str) -> bool:
    if len(tok) < 3:
        return False
    if tok.isdigit():
        return False
    if tok in _STOPWORDS:
        return False
    return True


def extract_concept_terms(text: str) -> List[str]:
    """Extract normalized unigram and adjacent 2-gram concept terms from text."""
    if not text:
        return []
    raw_tokens = _TOKEN_RE.findall(text.lower())
    content_tokens = [tok for tok in raw_tokens if _is_valid_token(tok)]
    if not content_tokens:
        return []

    terms: List[str] = []
    seen = set()
    for tok in content_tokens:
        if tok not in seen:
            seen.add(tok)
            terms.append(tok)
    for idx in range(len(content_tokens) - 1):
        bigram = f"{content_tokens[idx]} {content_tokens[idx + 1]}"
        if bigram not in seen:
            seen.add(bigram)
            terms.append(bigram)
    return terms


def _shares_surface_or_stem(a: str, b: str) -> bool:
    """Return True if terms already overlap lexically (exact/substring/shared token)."""
    if a == b or a in b or b in a:
        return True
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if tokens_a & tokens_b:
        return True
    return False


def build_ppmi_cooccurrence_bridges(
    documents: Sequence[str],
    *,
    min_bridge_df: Optional[int] = None,
    max_vocab: int = 4096,
    min_similarity: float = 0.20,
    max_bridges_per_term: int = 4,
    max_total_bridges: int = 500,
    shift_k: float = 1.0,
) -> List[Dict[str, Any]]:
    """Compute PPMI + 2nd-order distributional cosine bridges across documents.

    Terms that never co-occurred in the same document (zero-word-overlap) are
    bridged through shared high-PPMI context terms across the corpus.
    """
    doc_terms: List[List[str]] = []
    df_counts: Counter[str] = Counter()
    for doc in documents:
        terms = extract_concept_terms(doc)
        if not terms:
            continue
        doc_terms.append(terms)
        df_counts.update(terms)

    n_docs = len(doc_terms)
    if n_docs < 2 or not df_counts:
        return []

    bridge_df_floor = (
        int(min_bridge_df)
        if min_bridge_df is not None
        else (2 if n_docs >= 2 else 1)
    )
    # Keep top max_vocab terms deterministically by (-df, term)
    vocab_items = sorted(
        df_counts.items(), key=lambda item: (-item[1], item[0])
    )[: max(1, int(max_vocab))]
    vocab = {term for term, _df in vocab_items}

    # Build document co-occurrence counts
    cooccur: Dict[str, Counter[str]] = defaultdict(Counter)
    for terms in doc_terms:
        filtered = [t for t in terms if t in vocab]
        if len(filtered) < 2:
            continue
        for i, u in enumerate(filtered):
            for j in range(i + 1, len(filtered)):
                v = filtered[j]
                if u == v:
                    continue
                cooccur[u][v] += 1
                cooccur[v][u] += 1

    # 1st-order Shifted PPMI row vectors (normalized to unit L2 norm)
    shift_log = math.log2(max(1.0, float(shift_k)))
    ppmi_rows: Dict[str, Dict[str, float]] = {}
    for u, neighbors in cooccur.items():
        df_u = df_counts[u]
        if df_u <= 0:
            continue
        weights: Dict[str, float] = {}
        norm_sq = 0.0
        for v, c_uv in neighbors.items():
            df_v = df_counts[v]
            if df_v < bridge_df_floor:
                continue
            if n_docs >= 20 and df_v > int(0.70 * n_docs):
                continue
            pmi = math.log2(
                (float(c_uv) * (float(n_docs) + 1.0)) / (float(df_u) * float(df_v))
            )
            val = pmi - shift_log
            if val > 0.0:
                weights[v] = val
                norm_sq += val * val
        if weights and norm_sq > 0.0:
            inv_norm = 1.0 / math.sqrt(norm_sq)
            ppmi_rows[u] = {v: w * inv_norm for v, w in weights.items()}

    if not ppmi_rows:
        return []

    # Inverted index over PPMI context dimensions for fast 2nd-order dot products
    context_postings: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for term, vec in ppmi_rows.items():
        for ctx_term, weight in vec.items():
            context_postings[ctx_term].append((term, weight))

    # 2nd-order cosine similarity via shared bridge contexts
    pair_dots: Dict[Tuple[str, str], float] = defaultdict(float)
    pair_bridges: Dict[Tuple[str, str], List[Tuple[str, float]]] = defaultdict(list)
    for ctx_term, postings in context_postings.items():
        if len(postings) < 2 or len(postings) > 512:
            continue
        for i in range(len(postings)):
            u, wu = postings[i]
            for j in range(i + 1, len(postings)):
                v, wv = postings[j]
                if _shares_surface_or_stem(u, v):
                    continue
                contrib = wu * wv
                pair_key = (u, v) if u < v else (v, u)
                pair_dots[pair_key] += contrib
                pair_bridges[pair_key].append((ctx_term, contrib))

    # Collect top bridges per term (bidirectional so either phrasing expands to the other)
    candidates_by_source: Dict[str, List[Tuple[float, str, int, List[str], int]]] = (
        defaultdict(list)
    )
    for (u, v), sim2 in pair_dots.items():
        if sim2 < min_similarity:
            continue
        shared = sorted(
            pair_bridges[(u, v)], key=lambda item: (-item[1], item[0])
        )
        bridge_terms = [ctx for ctx, _c in shared[:5]]
        support = len(shared)
        order = 1 if cooccur[u].get(v, 0) > 0 else 2
        calibrated_score = min(0.95, max(0.45, round(0.45 + 0.50 * min(1.0, sim2), 4)))
        candidates_by_source[u].append(
            (calibrated_score, v, support, bridge_terms, order)
        )
        candidates_by_source[v].append(
            (calibrated_score, u, support, bridge_terms, order)
        )

    rows: List[Dict[str, Any]] = []
    for source_term in sorted(candidates_by_source):
        ranked = sorted(
            candidates_by_source[source_term],
            key=lambda item: (item[4] != 2, -item[0], -item[2], item[1]),
        )[: max(1, int(max_bridges_per_term))]
        bundle_members = [target for _sc, target, _sup, _br, _ord in ranked]
        for score, target_term, support, bridge_terms, order in ranked:
            rows.append(
                {
                    "surface_form": source_term,
                    "canonical_form": target_term,
                    "kind": "cooccurrence_bridge",
                    "domain_pack": "corpus_ppmi_v1",
                    "support_count": support,
                    "score": score,
                    "meta": {
                        "source": "ppmi_cooccurrence_v1",
                        "order": order,
                        "bridges": bridge_terms,
                        "bundle_members": bundle_members,
                    },
                }
            )

    rows.sort(
        key=lambda r: (
            r["meta"]["order"] != 2,
            -float(r["score"]),
            -int(r["support_count"]),
            -len(str(r["surface_form"]).split()),
            -len(str(r["canonical_form"]).split()),
            str(r["surface_form"]),
            str(r["canonical_form"]),
        )
    )
    return rows[: max(1, int(max_total_bridges))]


def run_cooccurrence_bridge_learning(
    *,
    session,
    tenant_id: str,
    graph_id: str,
    max_documents: int = 5000,
    min_similarity: float = 0.20,
    max_bridges_per_term: int = 4,
    max_total_bridges: int = 500,
) -> CooccurrenceBridgeResult:
    """Learn and persist PPMI + 2nd-order co-occurrence bridges for a graph."""
    if not _cooccurrence_enabled():
        return CooccurrenceBridgeResult(
            status="skipped",
            documents_scanned=0,
            vocab_size=0,
            bridges_discovered=0,
            bridges_persisted=0,
            reason="cooccurrence_bridge_disabled",
        )
    if session is None:
        return CooccurrenceBridgeResult(
            status="skipped",
            documents_scanned=0,
            vocab_size=0,
            bridges_discovered=0,
            bridges_persisted=0,
            reason="no_session",
        )

    from store.pg.models_faim import NodeRepresentationV2Model
    from store.pg.repos.domain_knowledge_repo import DomainKnowledgeRepo
    from store.pg.repos.graph_version_repo import GraphVersionRepo

    rows = (
        session.query(NodeRepresentationV2Model.normalized_text)
        .filter(
            NodeRepresentationV2Model.tenant_id == tenant_id,
            NodeRepresentationV2Model.graph_id == graph_id,
        )
        .order_by(NodeRepresentationV2Model.node_id.asc())
        .limit(max(1, int(max_documents)))
        .all()
    )
    documents = [str(r[0] or "").strip() for r in rows if str(r[0] or "").strip()]
    if len(documents) < 2:
        return CooccurrenceBridgeResult(
            status="skipped",
            documents_scanned=len(documents),
            vocab_size=0,
            bridges_discovered=0,
            bridges_persisted=0,
            reason="insufficient_documents",
        )

    bridge_rows = build_ppmi_cooccurrence_bridges(
        documents,
        min_similarity=min_similarity,
        max_bridges_per_term=max_bridges_per_term,
        max_total_bridges=max_total_bridges,
    )
    if not bridge_rows:
        return CooccurrenceBridgeResult(
            status="skipped",
            documents_scanned=len(documents),
            vocab_size=0,
            bridges_discovered=0,
            bridges_persisted=0,
            reason="no_bridges_above_threshold",
        )

    domain_repo = DomainKnowledgeRepo(session=session, tenant_id=tenant_id)
    persisted = domain_repo.merge_lexicon(graph_id, bridge_rows)
    new_version: Optional[int] = None
    if persisted > 0:
        gv_repo = GraphVersionRepo(tenant_id=tenant_id)
        new_version = gv_repo.bump(
            session,
            graph_id=graph_id,
            reason=f"cooccurrence_bridge: {persisted} bridges",
        )

    return CooccurrenceBridgeResult(
        status="completed",
        documents_scanned=len(documents),
        vocab_size=len({r["surface_form"] for r in bridge_rows}),
        bridges_discovered=len(bridge_rows),
        bridges_persisted=persisted,
        graph_version=new_version,
    )


__all__ = [
    "CooccurrenceBridgeResult",
    "build_ppmi_cooccurrence_bridges",
    "extract_concept_terms",
    "run_cooccurrence_bridge_learning",
]
