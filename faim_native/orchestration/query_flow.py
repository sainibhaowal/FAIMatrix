"""FAIM-Native Query Flow (Stage-8).

Orchestrates query execution with:
- Event emission (QUERY_START → QUERY_COMPLETE)
- Candidate recall
- FAIM re-ranking
- Usage tracking (touch_count, last_access)
- Metrics computation

NOT RAG: No chunking, no ST, uses EvidenceBlocks only.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

# Flexible imports
_parent = Path(__file__).parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from core.contracts.types import EventRecord  # noqa: E402
from core.query.query_engine import (  # noqa: E402
    DEFAULT_WEIGHTS,
    STRICT_WEIGHTS,
    build_explain_payload,
    compute_query_hash,
    inheritance_weighted_expansion,
    recall_candidates_brute_force,
    recall_with_graph_expansion,
    rerank_faim,
)
from core.query.idf_cache import apply_idf, compute_idf_weights  # noqa: E402
from encoding.representation_v2 import build_query_representation_v2  # noqa: E402
from encoding.text_vectorizer import vectorize_text  # noqa: E402
from orchestration.ingest_flow import FAIMProfile  # noqa: E402
from store.journal.event_journal import EventJournal  # noqa: E402

# =============================================================================
# Query Result
# =============================================================================


@dataclass
class QueryResult:
    """Result of a query execution."""

    tenant_id: str
    graph_id: str
    graph_version: int
    graph_hash: str
    query_hash: str
    k: int
    results: List[Dict[str, Any]]
    metrics: Dict[str, float]
    profile: FAIMProfile
    duration_ms: float = 0.0
    answer: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response dict."""
        return {
            "tenant_id": self.tenant_id,
            "graph_id": self.graph_id,
            "graph_version": self.graph_version,
            "graph_hash": self.graph_hash,
            "query_hash": self.query_hash,
            "k": self.k,
            "profile": (
                self.profile.name
                if isinstance(self.profile, FAIMProfile)
                else str(self.profile)
            ),
            "results": self.results,
            "answer": self.answer,
            "metrics": self.metrics,
            "duration_ms": self.duration_ms,
        }


# =============================================================================
# Query Events
# =============================================================================


def emit_query_start(
    journal: EventJournal,
    graph_id: str,
    query_hash: str,
    k: int,
    profile: str,
) -> EventRecord:
    """Emit QUERY_START event."""
    event = EventRecord.create(
        graph_id=graph_id,
        kind="QUERY_START",
        payload={
            "query_hash": query_hash[:16],  # Truncate for SSE
            "k": k,
            "profile": profile,
        },
    )
    return journal.append(event)


def emit_query_reranked(
    journal: EventJournal,
    graph_id: str,
    query_hash: str,
    top_ids: List[str],
) -> EventRecord:
    """Emit QUERY_RERANKED event."""
    event = EventRecord.create(
        graph_id=graph_id,
        kind="QUERY_RERANKED",
        payload={
            "query_hash": query_hash[:16],
            "top_count": len(top_ids),
            "top_ids": top_ids[:5],  # Bounded for SSE
        },
    )
    return journal.append(event)


def emit_query_touch(
    journal: EventJournal,
    graph_id: str,
    node_id: str,
    touch_count: int,
) -> EventRecord:
    """Emit QUERY_TOUCH event for each touched node."""
    event = EventRecord.create(
        graph_id=graph_id,
        kind="QUERY_TOUCH",
        payload={
            "node_id": node_id,
            "touch_count": touch_count,
        },
    )
    return journal.append(event)


def emit_query_complete(
    journal: EventJournal,
    graph_id: str,
    query_hash: str,
    result_count: int,
    duration_ms: float,
    diagnostics_hash: Optional[str] = None,
) -> EventRecord:
    """Emit QUERY_COMPLETE event."""
    event = EventRecord.create(
        graph_id=graph_id,
        kind="QUERY_COMPLETE",
        payload={
            "query_hash": query_hash[:16],
            "result_count": result_count,
            "duration_ms": round(duration_ms, 2),
            "diagnostics_hash": diagnostics_hash[:16] if diagnostics_hash else None,
        },
    )
    return journal.append(event)


# =============================================================================
# Graph Metrics (quick fetch)
# =============================================================================


def get_graph_metrics(session, tenant_id: str, graph_id: str) -> Dict[str, float]:
    """Get graph metrics for query scoring."""
    from sqlalchemy import func
    from store.pg.models_faim import NodeModel

    # Quick stats
    stats = (
        session.query(
            func.count(NodeModel.node_id),
            func.avg(NodeModel.touch_count),
        )
        .filter(
            NodeModel.tenant_id == tenant_id,
            NodeModel.graph_id == graph_id,
        )
        .first()
    )

    node_count = stats[0] or 0
    avg_touch = float(stats[1]) if stats[1] else 1.0

    return {
        "node_count": node_count,
        "avg_touch": avg_touch,
        "CR": 1.0,  # Placeholder
        "R": 0.0,  # Placeholder
        "D_hat": 0.5,
        "H_hat": 0.5,
        "lambda_hat": 0.5,
        "novelty": 0.0,
        "energy": 0.0,
    }


# =============================================================================
# Usage Update
# =============================================================================


def update_usage(
    session,
    tenant_id: str,
    graph_id: str,
    node_ids: List[UUID],
) -> Dict[UUID, int]:
    """Update touch_count and last_access for touched nodes.

    Returns dict of node_id -> new touch_count.
    """
    from store.pg.models_faim import NodeModel

    now = datetime.now(timezone.utc)
    touches = {}

    for node_id in node_ids:
        node = (
            session.query(NodeModel)
            .filter(
                NodeModel.tenant_id == tenant_id,
                NodeModel.graph_id == graph_id,
                NodeModel.node_id == node_id,
            )
            .first()
        )

        if node:
            node.touch_count = (node.touch_count or 0) + 1
            node.last_access = now
            touches[node_id] = node.touch_count

    session.flush()
    return touches


def _repr_v2_enabled() -> bool:
    """Feature gate for Representation V2 query fusion."""
    raw = os.getenv("FAIM_REPR_V2_ENABLED", "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _phase5_enabled() -> bool:
    """Feature gate for Phase 5 scale pipeline."""
    raw = os.getenv("FAIM_PHASE5_ENABLED", "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _phase4_stopwords_enabled() -> bool:
    """Feature gate for Phase 4 stop-word filtering in query vectorization."""
    raw = os.getenv("FAIM_PHASE4_STOPWORDS_ENABLED", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _stable_union_ids(primary_ids: List[UUID], extra_ids: List[UUID]) -> List[UUID]:
    """Stable deterministic union preserving primary ordering."""
    seen = set()
    merged: List[UUID] = []
    for node_id in primary_ids + extra_ids:
        if node_id in seen:
            continue
        seen.add(node_id)
        merged.append(node_id)
    return merged


# =============================================================================
# Main Query Flow
# =============================================================================


def run_query(
    session,
    tenant_id: str,
    graph_id: str,
    query_text: str,
    k: int = 10,
    profile: FAIMProfile = FAIMProfile.STRICT,
    return_explain: bool = False,
    index=None,
    cache=None,
) -> QueryResult:
    """Execute a FAIM-native query.

    Steps:
    1. Emit QUERY_START
    2. Encode query text → q_vec
    3. Recall candidates
    4. Re-rank with FAIM scoring
    5. Update usage (touch_count)
    6. Emit QUERY_TOUCH for topK
    7. Emit QUERY_COMPLETE

    Args:
        session: Database session.
        tenant_id: Tenant identifier.
        graph_id: Graph identifier.
        query_text: User query.
        k: Number of results to return.
        profile: FAIM profile (STRICT, BALANCED, FAST).
        return_explain: Whether to include explain payload.
        index: Optional FAIMIndex for acceleration.

    Returns:
        QueryResult with ranked nodes and metrics.
    """
    import time

    start_time = time.perf_counter()

    # Initialize journal
    journal = EventJournal(session)

    # Compute query hash
    query_hash = compute_query_hash(query_text, graph_id)
    profile_name = profile.name if isinstance(profile, FAIMProfile) else str(profile)

    # 1. Emit QUERY_START
    emit_query_start(journal, graph_id, query_hash, k, profile_name)

    # 2. Canonicalize query text with graph-local lexicon, then encode.
    canonical_query_text = query_text
    try:
        from lexical.canonicalizer import canonicalize_text
        from store.pg.repos.canonical_semantics_repo import CanonicalSemanticsRepo

        canonical_repo = CanonicalSemanticsRepo(session=session, tenant_id=tenant_id)
        canonical_map = canonical_repo.get_canonical_map(graph_id)
        canonicalized = canonicalize_text(query_text, canonical_map=canonical_map)
        if canonicalized.canonical_text:
            canonical_query_text = canonicalized.canonical_text
    except Exception:
        canonical_query_text = query_text

    try:
        from lexical.multilingual_canonicalizer import canonicalize_multilingual_text
        from store.pg.repos.multilingual_repo import MultilingualRepo

        multilingual_repo = MultilingualRepo(session=session, tenant_id=tenant_id)
        multilingual_map = multilingual_repo.get_language_map(graph_id)
        multilingualized = canonicalize_multilingual_text(
            canonical_query_text,
            graph_map=multilingual_map,
        )
        if multilingualized.canonical_text:
            canonical_query_text = multilingualized.canonical_text
    except Exception:
        pass

    domain_candidate_ids: List[UUID] = []
    domain_scores: Dict[UUID, Dict[str, float]] = {}
    try:
        from core.operators.entity_linking import (
            build_domain_candidate_scores,
            resolve_query_links,
        )
        from store.pg.repos.domain_knowledge_repo import DomainKnowledgeRepo
        from store.pg.repos.edge_repo import EdgeRepo

        domain_repo = DomainKnowledgeRepo(session=session, tenant_id=tenant_id)
        domain_rows = domain_repo.list_lexicon_entries(graph_id)
        linked_terms = resolve_query_links(canonical_query_text, domain_rows)
        domain_candidate_ids, domain_scores = build_domain_candidate_scores(
            edge_repo=EdgeRepo(session=session, tenant_id=tenant_id),
            graph_id=graph_id,
            linked_terms=linked_terms,
        )
    except Exception:
        domain_candidate_ids = []
        domain_scores = {}

    # 2b. Encode query → q_vec (same vectorizer as ingest, with synonym expansion enabled for recall)
    q_result = vectorize_text(
        canonical_query_text,
        expand_synonyms=True,
        remove_stopwords=_phase4_stopwords_enabled(),
    )
    q_vec = q_result.v_native
    query_repr_v2 = build_query_representation_v2(canonical_query_text)
    lexical_scores: Dict[UUID, Any] = {}
    graph_scores: Dict[UUID, Dict[str, float]] = {}
    graph_paths: Dict[UUID, List[Dict[str, object]]] = {}

    # 2b. Apply IDF weighting (Phase 3C)
    try:
        _idf = compute_idf_weights(session, tenant_id, graph_id)
        q_vec = apply_idf(tuple(q_vec), _idf)
    except Exception:
        # If IDF computation fails (e.g., empty graph), continue with unweighted q_vec
        pass

    # 2c. Inheritance-weighted query expansion (Phase 7)
    try:
        _seeds = recall_candidates_brute_force(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            q_vec=tuple(q_vec),
            n=20,
        )
        if _seeds:
            _seed_ids = [node_id for node_id, _ in _seeds]
            q_vec = inheritance_weighted_expansion(
                session=session,
                tenant_id=tenant_id,
                graph_id=graph_id,
                q_vec=tuple(q_vec),
                seed_node_ids=_seed_ids,
                alpha=0.2,
            )
    except Exception:
        # Graceful fallback — continue with non-expanded q_vec
        pass

    # 3. Get graph metrics
    metrics = get_graph_metrics(session, tenant_id, graph_id)
    graph_avg_touch = metrics.get("avg_touch", 1.0)

    from store.pg.repos.graph_version_repo import GraphVersionRepo

    gv_repo = GraphVersionRepo(tenant_id=tenant_id)
    graph_version = gv_repo.get_version(session, graph_id)

    # 4. Recall candidates (cache -> index/brute-force fallback)
    cache_hit = False
    profile_name_cache = (
        profile.value if isinstance(profile, FAIMProfile) else str(profile).lower()
    )
    candidates: List[Any] = []
    phase5_sparse_candidates: List[Any] = []
    phase5_dense_candidates: List[Any] = []

    if cache is not None:
        try:
            cached = cache.get(
                graph_id=graph_id,
                graph_version=graph_version,
                query_vector=q_vec,
                profile=profile_name_cache,
                k=200,
            )
            if cached:
                parsed = []
                for node_id, score in cached:
                    try:
                        parsed.append((UUID(str(node_id)), float(score)))
                    except (ValueError, TypeError):
                        continue
                if parsed:
                    candidates = parsed
                    cache_hit = True
        except Exception:
            cache_hit = False

    if not candidates:
        if _phase5_enabled() and _repr_v2_enabled():
            try:
                from index.deterministic_ann import search_vptree
                from index.wand import block_max_wand_shortlist
                from orchestration.perf.index_rebuild import build_graph_index_artifacts
                from store.pg.repos.representation_repo import RepresentationRepo

                artifacts = build_graph_index_artifacts(
                    session=session,
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                )
                repr_repo = RepresentationRepo(session=session, tenant_id=tenant_id)
                stats_by_channel = repr_repo.get_graph_stats(graph_id)
                phase5_sparse_candidates = list(
                    block_max_wand_shortlist(
                        artifacts.sparse_index,
                        query_repr_v2,
                        stats_by_channel,
                        k=max(200, k * 20),
                        max_candidates=max(400, k * 40),
                    )
                )
                phase5_dense_candidates = list(
                    search_vptree(
                        artifacts.ann_root,
                        tuple(q_vec),
                        max(200, k * 20),
                    )
                )
                candidates = phase5_sparse_candidates or []
                candidate_ids = [node_id for node_id, _score in candidates]
                dense_ids = [node_id for node_id, _score in phase5_dense_candidates]
                merged_ids = _stable_union_ids(candidate_ids, dense_ids)
                dense_score_map = {
                    node_id: float(score) for node_id, score in phase5_dense_candidates
                }
                sparse_score_map = {
                    node_id: float(score) for node_id, score in phase5_sparse_candidates
                }
                merged_candidates = []
                for node_id in merged_ids:
                    merged_candidates.append(
                        (
                            node_id,
                            max(
                                sparse_score_map.get(node_id, 0.0),
                                dense_score_map.get(node_id, 0.0),
                            ),
                        )
                    )
                candidates = sorted(
                    merged_candidates,
                    key=lambda item: (-item[1], str(item[0])),
                )[: max(200, k * 20)]
            except Exception:
                phase5_sparse_candidates = []
                phase5_dense_candidates = []
                candidates = []

    if not candidates:
        # STRICT mode: always use graph-expanded recall
        if profile == FAIMProfile.STRICT or index is None:
            candidates = recall_with_graph_expansion(
                session=session,
                tenant_id=tenant_id,
                graph_id=graph_id,
                q_vec=q_vec,
                n=200,
            )
        else:
            # Use index for acceleration
            from core.query.query_engine import recall_candidates_index

            candidates = recall_candidates_index(
                index=index,
                tenant_id=tenant_id,
                graph_id=graph_id,
                q_vec=q_vec,
                n=200,
            )
            # If index fails, fall back to graph-expanded recall
            if not candidates:
                candidates = recall_with_graph_expansion(
                    session=session,
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    q_vec=q_vec,
                    n=200,
                )

        if cache is not None and candidates:
            try:
                cache.set(
                    graph_id=graph_id,
                    graph_version=graph_version,
                    query_vector=q_vec,
                    profile=profile_name_cache,
                    k=200,
                    results=[(str(node_id), float(score)) for node_id, score in candidates],
                )
            except Exception:
                pass

    candidate_ids = [c[0] for c in candidates]

    if _repr_v2_enabled():
        try:
            from store.pg.repos.representation_repo import RepresentationRepo

            repr_repo = RepresentationRepo(session=session, tenant_id=tenant_id)
            lexical_candidates = repr_repo.top_k_lexical(
                graph_id=graph_id,
                query_repr=query_repr_v2,
                k=max(200, k * 20),
            )
            lexical_candidate_ids = [node_id for node_id, _score in lexical_candidates]
            candidate_ids = _stable_union_ids(candidate_ids, lexical_candidate_ids)
            lexical_scores = repr_repo.score_node_ids(
                graph_id=graph_id,
                query_repr=query_repr_v2,
                node_ids=candidate_ids,
            )
        except Exception:
            lexical_scores = {}

    if domain_candidate_ids:
        candidate_ids = _stable_union_ids(candidate_ids, domain_candidate_ids)

    # Phase 3: bounded multi-hop graph semantics and diffusion
    try:
        from core.query.graph_semantics import build_graph_semantic_scores
        from core.operators.semantic_typing import KNOWN_SEMANTIC_KINDS
        from store.pg.repos.edge_repo import EdgeRepo
        from store.pg.repos.node_repo import NodeRepo

        seed_pairs = recall_candidates_brute_force(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            q_vec=tuple(q_vec),
            n=30,
        )
        seed_score_map = {node_id: max(0.0, score) for node_id, score in seed_pairs}
        graph_candidate_ids, graph_scores, graph_paths = build_graph_semantic_scores(
            edge_repo=EdgeRepo(session=session, tenant_id=tenant_id),
            node_repo=NodeRepo(session=session, tenant_id=tenant_id),
            graph_id=graph_id,
            seed_scores=seed_score_map,
            base_candidate_ids=candidate_ids,
            allowed_kinds={"inheritance"} | KNOWN_SEMANTIC_KINDS | {"opposition"},
            max_hops=2,
            max_neighbors=8,
            decay=0.6,
            alpha=0.2,
            steps=3,
        )
        candidate_ids = _stable_union_ids(candidate_ids, graph_candidate_ids)
    except Exception:
        graph_scores = {}
        graph_paths = {}

    # 5. Re-rank with FAIM scoring
    weights = STRICT_WEIGHTS if profile == FAIMProfile.STRICT else DEFAULT_WEIGHTS
    ranked = rerank_faim(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        q_vec=q_vec,
        candidate_ids=candidate_ids,
        graph_avg_touch=graph_avg_touch,
        weights=weights,
        k=k,
        lexical_scores=lexical_scores,
        graph_scores=graph_scores,
        graph_paths=graph_paths,
        domain_scores=domain_scores,
        query_text=canonical_query_text,
        query_repr_v2=query_repr_v2,
    )

    # Emit QUERY_RERANKED
    top_ids = [str(r["node_id"]) for r in ranked]
    emit_query_reranked(journal, graph_id, query_hash, top_ids)

    # 6. Update usage for top results
    result_node_ids = [r["node_id"] for r in ranked]
    touches = update_usage(session, tenant_id, graph_id, result_node_ids)

    # 7. Emit QUERY_TOUCH for each touched node
    for node_id, touch_count in touches.items():
        emit_query_touch(journal, graph_id, str(node_id), touch_count)

    # 8. Build results
    results = []
    for r in ranked:
        result_item = {
            "node_id": str(r["node_id"]),
            "vector_hash": r["vector_hash"],
            "score": r["score"],
            "score_components": r["score_components"],
            "level": r["level"],
            "touch_count": r["touch_count"],
            "temporal_status": r.get("temporal_status"),
        }

        # Add evidence info
        if r.get("raw_id"):
            result_item["evidence"] = {
                "raw_id": r["raw_id"],
                "block_id": r.get("block_id"),
                "anchor": r.get("anchor"),
            }

        # Add explain if requested
        if return_explain:
            explain_payload = build_explain_payload(
                session, tenant_id, graph_id, r["node_id"]
            )
            explain_payload["phase3_graph_paths"] = r.get("graph_paths", [])
            explain_payload["phase3_graph_score"] = {
                "total": r["score_components"].get("graph", 0.0),
                "path": r["score_components"].get("graph_path", 0.0),
                "diffusion": r["score_components"].get("graph_diffusion", 0.0),
                "neighborhood": r["score_components"].get("graph_neighborhood", 0.0),
                "contradiction": r["score_components"].get("graph_contradiction", 0.0),
            }
            explain_payload["phase4_reranker"] = r.get("phase4_explain", {})
            result_item["explain"] = explain_payload

        results.append(result_item)

    answer = None
    try:
        from core.query.answer_synthesis import synthesize_answer

        answer = synthesize_answer(
            query_text=canonical_query_text,
            ranked_results=ranked,
            query_hash=query_hash,
            graph_id=graph_id,
        )
    except Exception:
        answer = None

    metrics["cache_hit"] = 1.0 if cache_hit else 0.0
    if phase5_sparse_candidates or phase5_dense_candidates:
        metrics["phase5_sparse_candidates"] = float(len(phase5_sparse_candidates))
        metrics["phase5_dense_candidates"] = float(len(phase5_dense_candidates))

    # Compute result
    duration_ms = (time.perf_counter() - start_time) * 1000

    # 9. Emit QUERY_COMPLETE
    emit_query_complete(
        journal, graph_id, query_hash, len(results), duration_ms, query_hash
    )

    return QueryResult(
        tenant_id=tenant_id,
        graph_id=graph_id,
        graph_version=graph_version,
        graph_hash=query_hash,  # Using query_hash as placeholder
        query_hash=query_hash,
        k=k,
        results=results,
        answer=answer,
        metrics=metrics,
        profile=profile,
        duration_ms=duration_ms,
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "QueryResult",
    "run_query",
    "emit_query_start",
    "emit_query_reranked",
    "emit_query_touch",
    "emit_query_complete",
]
