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
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

# Flexible imports
_parent = Path(__file__).parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from core.contracts.types import EventRecord  # noqa: E402
from core.query.idf_cache import apply_idf, compute_idf_weights  # noqa: E402
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
from encoding.representation_v2 import build_query_representation_v2  # noqa: E402
from encoding.text_vectorizer import vectorize_text  # noqa: E402
from orchestration.ingest_flow import FAIMProfile  # noqa: E402
from store.journal.event_journal import EventJournal  # noqa: E402

logger = logging.getLogger(__name__)

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
    metrics: Dict[str, Any]
    profile: FAIMProfile
    duration_ms: float = 0.0
    answer: Optional[Dict[str, Any]] = None
    degraded_features: List[str] = field(default_factory=list)

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
            "degraded_features": self.degraded_features,
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


def refresh_graph_diagnostics(
    session,
    tenant_id: str,
    graph_id: str,
    *,
    graph_version: Optional[int] = None,
) -> Dict[str, Any]:
    """Compute and persist one versioned diagnostics snapshot.

    This is called after graph mutations/evolution.  Query reads use the
    resulting bounded cache row and therefore do not scan nodes/edges on every
    request.  The stale-read fallback below exists only for legacy graphs that
    predate the cache migration.
    """
    from sqlalchemy import func
    from core.dynamics.evolution_native import compute_graph_diagnostics
    from store.pg.models_faim import (
        EdgeModel,
        GraphDiagnosticsCacheModel,
        NodeModel,
    )
    from store.pg.repos.graph_version_repo import GraphVersionRepo

    if graph_version is None:
        graph_version = GraphVersionRepo(tenant_id=tenant_id).get_version(
            session, graph_id
        )

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

    node_count = int(stats[0] or 0)
    avg_touch = float(stats[1]) if stats[1] else 1.0

    nodes = (
        session.query(NodeModel)
        .filter(NodeModel.tenant_id == tenant_id, NodeModel.graph_id == graph_id)
        .all()
    )
    edges = (
        session.query(EdgeModel)
        .filter(EdgeModel.tenant_id == tenant_id, EdgeModel.graph_id == graph_id)
        .all()
    )
    diagnostics = compute_graph_diagnostics(
        graph_id=graph_id,
        nodes=nodes,
        edges=edges,
        graph_version=graph_version,
    )
    payload: Dict[str, Any] = {
        "node_count": node_count,
        "edge_count": len(edges),
        "avg_touch": avg_touch,
        "CR": round(node_count / len(edges), 6) if edges else 0.0,
        "R": round(diagnostics.redundancy_R, 6),
        "D_hat": round(diagnostics.D_hat, 6),
        "H_hat": round(diagnostics.H_hat, 6),
        "lambda_hat": round(diagnostics.lambda_hat, 6),
        "novelty": round(diagnostics.novelty_N, 6),
        "energy": round(diagnostics.energy_E, 6),
        "diagnostics_hash": diagnostics.diagnostics_hash,
        "diagnostics_graph_version": int(graph_version or 0),
        "diagnostics_computed_at": datetime.now(timezone.utc).isoformat(),
        "diagnostics_cached": 1.0,
    }

    cached = (
        session.query(GraphDiagnosticsCacheModel)
        .filter(
            GraphDiagnosticsCacheModel.tenant_id == tenant_id,
            GraphDiagnosticsCacheModel.graph_id == graph_id,
        )
        .first()
    )
    now = datetime.now(timezone.utc)
    if cached is None:
        cached = GraphDiagnosticsCacheModel(
            tenant_id=tenant_id,
            graph_id=graph_id,
        )
        session.add(cached)
    cached.graph_version = int(graph_version or 0)
    cached.node_count = node_count
    cached.edge_count = len(edges)
    cached.cr = payload["CR"]
    cached.redundancy = payload["R"]
    cached.d_hat = payload["D_hat"]
    cached.h_hat = payload["H_hat"]
    cached.lambda_hat = payload["lambda_hat"]
    cached.novelty = payload["novelty"]
    cached.energy = payload["energy"]
    cached.diagnostics_hash = diagnostics.diagnostics_hash
    cached.computed_at = now
    session.flush()
    payload["diagnostics_computed_at"] = now.isoformat()
    return payload


def persist_graph_diagnostics_snapshot(
    session,
    tenant_id: str,
    graph_id: str,
    diagnostics: Any,
    *,
    graph_version: int,
) -> Dict[str, Any]:
    """Persist diagnostics already computed by evolution without rescanning."""
    from sqlalchemy import func
    from store.pg.models_faim import EdgeModel, GraphDiagnosticsCacheModel, NodeModel

    node_count = int(
        session.query(func.count(NodeModel.node_id))
        .filter(NodeModel.tenant_id == tenant_id, NodeModel.graph_id == graph_id)
        .scalar()
        or 0
    )
    edge_count = int(
        session.query(func.count(EdgeModel.edge_id))
        .filter(EdgeModel.tenant_id == tenant_id, EdgeModel.graph_id == graph_id)
        .scalar()
        or 0
    )
    now = datetime.now(timezone.utc)
    cached = (
        session.query(GraphDiagnosticsCacheModel)
        .filter(
            GraphDiagnosticsCacheModel.tenant_id == tenant_id,
            GraphDiagnosticsCacheModel.graph_id == graph_id,
        )
        .first()
    )
    if cached is None:
        cached = GraphDiagnosticsCacheModel(tenant_id=tenant_id, graph_id=graph_id)
        session.add(cached)
    cached.graph_version = int(graph_version or 0)
    cached.node_count = node_count
    cached.edge_count = edge_count
    cached.cr = round(node_count / edge_count, 6) if edge_count else 0.0
    cached.redundancy = round(float(getattr(diagnostics, "redundancy_R", 0.0) or 0.0), 6)
    cached.d_hat = round(float(getattr(diagnostics, "D_hat", 0.0) or 0.0), 6)
    cached.h_hat = round(float(getattr(diagnostics, "H_hat", 0.0) or 0.0), 6)
    cached.lambda_hat = round(float(getattr(diagnostics, "lambda_hat", 0.0) or 0.0), 6)
    cached.novelty = round(float(getattr(diagnostics, "novelty_N", 0.0) or 0.0), 6)
    cached.energy = round(float(getattr(diagnostics, "energy_E", 0.0) or 0.0), 6)
    cached.diagnostics_hash = str(getattr(diagnostics, "diagnostics_hash", "") or "")
    cached.computed_at = now
    session.flush()
    return cached.to_metrics()


def get_graph_metrics(session, tenant_id: str, graph_id: str) -> Dict[str, Any]:
    """Read bounded cached diagnostics; refresh only on a stale/missing row."""
    from sqlalchemy import func
    from store.pg.models_faim import GraphDiagnosticsCacheModel, NodeModel
    from store.pg.repos.graph_version_repo import GraphVersionRepo

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
    node_count = int(stats[0] or 0)
    avg_touch = float(stats[1]) if stats[1] else 1.0
    graph_version = GraphVersionRepo(tenant_id=tenant_id).get_version(session, graph_id)
    cached = (
        session.query(GraphDiagnosticsCacheModel)
        .filter(
            GraphDiagnosticsCacheModel.tenant_id == tenant_id,
            GraphDiagnosticsCacheModel.graph_id == graph_id,
        )
        .first()
    )
    if cached is None or int(cached.graph_version or 0) < int(graph_version or 0):
        # Compatibility backfill for graphs created before migration 0041.  It
        # runs once per version, then every query is a bounded cache read.
        return refresh_graph_diagnostics(
            session,
            tenant_id,
            graph_id,
            graph_version=graph_version,
        )
    metrics = cached.to_metrics(avg_touch=avg_touch)
    metrics["node_count"] = node_count
    return metrics


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


def _source_count_map(expansions: Sequence[object]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in expansions:
        for source in getattr(item, "sources", ()) or ():
            counts[source] = counts.get(source, 0) + 1
    return dict(sorted(counts.items(), key=lambda row: row[0]))


def _build_query_fusion_summary(
    *,
    candidate_ids: Sequence[UUID],
    lexical_scores: Dict[UUID, Any],
    domain_candidate_ids: Sequence[UUID],
    graph_scores: Dict[UUID, Dict[str, float]],
    phaseb_expansion_info: Dict[str, Any],
    ranked_item: Optional[Dict[str, Any]],
    graph_options: Dict[str, Any],
) -> Dict[str, Any]:
    top_explain = dict((ranked_item or {}).get("fusion_summary", {}) or {})
    top_layers = list(top_explain.get("active_layers", []) or [])
    return {
        "candidate_pool": {
            "total": len(candidate_ids),
            "lexical_scored": len(lexical_scores),
            "domain_candidates": len(domain_candidate_ids),
            "graph_candidates": len(graph_scores),
        },
        "query_expansion": {
            "source_counts": dict(phaseb_expansion_info.get("source_counts", {}) or {}),
            "expansion_count": len(list(phaseb_expansion_info.get("expansions", []) or [])),
        },
        "graph_runtime": {
            "max_hops": int(graph_options.get("graph_max_hops", 0) or 0),
            "max_neighbors": int(graph_options.get("graph_max_neighbors", 0) or 0),
            "diffusion_steps": int(graph_options.get("graph_diffusion_steps", 0) or 0),
            "decay": float(graph_options.get("graph_decay", 0.0) or 0.0),
            "alpha": float(graph_options.get("graph_alpha", 0.0) or 0.0),
        },
        "top_result": {
            "node_id": str((ranked_item or {}).get("node_id")) if ranked_item else None,
            "active_layers": top_layers,
            "strongest_layers": list(top_explain.get("strongest_layers", []) or []),
            "strongest_signals": list(top_explain.get("strongest_signals", []) or []),
        },
    }


def _domain_weighted_expansions(query_text: str, rows: Sequence[object]):
    from lexical.synonym_expander import WeightedExpansion, merge_weighted_expansions

    normalized = " ".join(str(query_text).lower().split())
    terms = set(normalized.split())
    weighted: List[WeightedExpansion] = []
    for row in rows:
        surface = str(getattr(row, "surface_form", "") or "").strip().lower()
        canonical = str(getattr(row, "canonical_form", "") or "").strip().lower()
        kind = str(getattr(row, "kind", "") or "domain_term").strip().lower()
        meta = dict(getattr(row, "meta", {}) or {})
        if not surface or not canonical or canonical == surface:
            bundle_members = [
                " ".join(str(item).strip().lower().split())
                for item in list(meta.get("bundle_members") or [])
                if str(item).strip()
            ]
            if kind != "concept_bundle" or not surface or not bundle_members:
                continue
            matched = surface in normalized if " " in surface else surface in terms
            if not matched:
                continue
            score = float(getattr(row, "score", 0.0) or 0.0)
            for member in bundle_members:
                if not member or member == surface:
                    continue
                weighted.append(
                    WeightedExpansion(
                        term=member,
                        weight=min(0.96, max(0.76, 0.74 + (score * 0.18))),
                        sources=(f"domain_{kind}",),
                        origins=(surface,),
                    )
                )
            continue
        matched = surface in normalized if " " in surface else surface in terms
        if not matched:
            continue
        score = float(getattr(row, "score", 0.0) or 0.0)
        weighted.append(
            WeightedExpansion(
                term=canonical,
                weight=min(0.95, max(0.7, 0.72 + (score * 0.22))),
                sources=(f"domain_{kind}",),
                origins=(surface,),
            )
        )
        for member in [
            " ".join(str(item).strip().lower().split())
            for item in list(meta.get("bundle_members") or [])
            if str(item).strip()
        ]:
            if not member or member in {surface, canonical}:
                continue
            weighted.append(
                WeightedExpansion(
                    term=member,
                    weight=min(0.94, max(0.72, 0.7 + (score * 0.18))),
                    sources=(f"domain_{kind}", "domain_bundle"),
                    origins=(surface, canonical),
                )
            )
    return merge_weighted_expansions(weighted, max_total=16)


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
    include_historical: bool = True,
    as_of: Optional[datetime] = None,
    graph_max_hops: Optional[int] = None,
    graph_max_neighbors: Optional[int] = None,
    graph_decay: Optional[float] = None,
    graph_alpha: Optional[float] = None,
    graph_diffusion_steps: Optional[int] = None,
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
    degraded_features: List[str] = []

    def _degraded(feature: str, exc: Exception) -> None:
        """Expose non-fatal retrieval degradation without leaking internals."""
        if feature not in degraded_features:
            degraded_features.append(feature)
        logger.warning("Query feature degraded: %s", feature, exc_info=exc)

    # Initialize journal
    journal = EventJournal(session, tenant_id=tenant_id)

    # Compute query hash
    query_hash = compute_query_hash(query_text, graph_id)
    profile_name = profile.name if isinstance(profile, FAIMProfile) else str(profile)

    # 1. Emit QUERY_START
    emit_query_start(journal, graph_id, query_hash, k, profile_name)

    # 2. Canonicalize and expand query text with deterministic weighted sources.
    canonical_query_text = query_text
    expanded_query_text = query_text
    phaseb_expansions: Sequence[object] = ()
    phaseb_expansion_info: Dict[str, Any] = {
        "base_query_text": query_text,
        "canonical_query_text": query_text,
        "expanded_query_text": query_text,
        "source_counts": {},
        "expansions": [],
    }
    canonicalized = None
    canonical_map: Dict[str, Sequence[str]] = {}
    try:
        from lexical.canonicalizer import canonicalize_text
        from lexical.synonym_expander import (
            build_weighted_synonym_expansions,
            merge_weighted_expansions,
            render_weighted_expansion_text,
        )
        from store.pg.repos.canonical_semantics_repo import CanonicalSemanticsRepo

        canonical_repo = CanonicalSemanticsRepo(session=session, tenant_id=tenant_id)
        canonical_map = canonical_repo.get_canonical_map(graph_id)
        canonicalized = canonicalize_text(query_text, canonical_map=canonical_map)
        if canonicalized.canonical_text:
            canonical_query_text = canonicalized.canonical_text
        synonym_expansions = build_weighted_synonym_expansions(
            canonicalized.normalized_text,
            max_synonyms_per_term=4,
            max_total=20,
            max_phrase_terms=8,
        )
        phaseb_expansions = merge_weighted_expansions(
            list(canonicalized.weighted_expansions) + list(synonym_expansions),
            max_total=28,
        )
        expanded_query_text = render_weighted_expansion_text(
            canonical_query_text,
            phaseb_expansions,
            max_total_terms=36,
        )
    except Exception as exc:
        _degraded("canonical_query_expansion", exc)
        canonical_query_text = query_text
        expanded_query_text = query_text
        canonicalized = None

    multilingualized = None
    multilingual_map: Dict[str, Sequence[str]] = {}
    try:
        from lexical.multilingual_canonicalizer import canonicalize_multilingual_text
        from lexical.synonym_expander import (
            merge_weighted_expansions,
            render_weighted_expansion_text,
        )
        from store.pg.repos.multilingual_repo import MultilingualRepo

        multilingual_repo = MultilingualRepo(session=session, tenant_id=tenant_id)
        multilingual_map = multilingual_repo.get_language_map(graph_id)
        multilingualized = canonicalize_multilingual_text(
            canonicalized.normalized_text if canonicalized else canonical_query_text,
            graph_map=multilingual_map,
        )
        phaseb_expansions = merge_weighted_expansions(
            list(phaseb_expansions) + list(multilingualized.weighted_expansions),
            max_total=32,
        )
        expanded_query_text = render_weighted_expansion_text(
            canonical_query_text,
            phaseb_expansions,
            max_total_terms=40,
        )
    except Exception as exc:
        _degraded("domain_entity_linking", exc)
        pass

    domain_candidate_ids: List[UUID] = []
    domain_scores: Dict[UUID, Dict[str, float]] = {}
    domain_linked_terms: List[Dict[str, Any]] = []
    domain_rows: List[Any] = []
    domain_map: Dict[str, Sequence[str]] = {}
    try:
        from core.operators.entity_linking import (
            build_domain_candidate_scores,
            resolve_query_links,
        )
        from store.pg.repos.domain_knowledge_repo import DomainKnowledgeRepo
        from store.pg.repos.edge_repo import EdgeRepo

        domain_repo = DomainKnowledgeRepo(session=session, tenant_id=tenant_id)
        domain_rows = domain_repo.list_lexicon_entries(graph_id)
        domain_map = domain_repo.get_domain_map(graph_id)
        linked_terms = resolve_query_links(expanded_query_text, domain_rows)
        domain_linked_terms = [
            {
                "surface_form": term.surface_form,
                "canonical_form": term.canonical_form,
                "kind": term.kind,
                "node_id": str(term.node_id),
                "score": term.score,
            }
            for term in linked_terms
        ]
        domain_candidate_ids, domain_scores = build_domain_candidate_scores(
            edge_repo=EdgeRepo(session=session, tenant_id=tenant_id),
            graph_id=graph_id,
            linked_terms=linked_terms,
        )
    except Exception as exc:
        _degraded("domain_knowledge_expansion", exc)
        domain_candidate_ids = []
        domain_scores = {}

    try:
        from lexical.synonym_expander import (
            merge_weighted_expansions,
            render_weighted_expansion_text,
        )

        domain_expansions = _domain_weighted_expansions(expanded_query_text, domain_rows)
        phaseb_expansions = merge_weighted_expansions(
            list(phaseb_expansions) + list(domain_expansions),
            max_total=36,
        )
        expanded_query_text = render_weighted_expansion_text(
            canonical_query_text,
            phaseb_expansions,
            max_total_terms=44,
        )
    except Exception as exc:
        _degraded("semantic_registry_expansion", exc)
        pass

    semantic_registry_info: Dict[str, Any] = {}
    try:
        from lexical.semantic_registry import (
            load_semantic_registry_snapshot,
            resolve_semantic_registry_expansions,
        )
        from lexical.synonym_expander import (
            merge_weighted_expansions,
            render_weighted_expansion_text,
        )

        registry_expansions, semantic_registry_info = resolve_semantic_registry_expansions(
            query_text=expanded_query_text,
            canonical_map=canonical_map,
            multilingual_map=multilingual_map,
            domain_map=domain_map,
            max_total=20,
        )
        phaseb_expansions = merge_weighted_expansions(
            list(phaseb_expansions) + list(registry_expansions),
            max_total=40,
        )
        expanded_query_text = render_weighted_expansion_text(
            canonical_query_text,
            phaseb_expansions,
            max_total_terms=52,
        )
        snapshot = load_semantic_registry_snapshot()
        semantic_registry_info["registry_term_count"] = snapshot.total_terms
    except Exception as exc:
        _degraded("idf_weighting", exc)
        semantic_registry_info = {}

    phaseb_expansion_info = {
        "base_query_text": query_text,
        "canonical_query_text": canonical_query_text,
        "expanded_query_text": expanded_query_text,
        "source_counts": _source_count_map(phaseb_expansions),
        "semantic_registry": semantic_registry_info,
        "expansions": [
            {
                "term": getattr(item, "term", ""),
                "weight": round(float(getattr(item, "weight", 0.0)), 4),
                "sources": list(getattr(item, "sources", ()) or ()),
                "origins": list(getattr(item, "origins", ()) or ()),
            }
            for item in list(phaseb_expansions)[:36]
        ],
    }

    # 2b. Encode query → q_vec (same vectorizer as ingest, with synonym expansion enabled for recall)
    q_result = vectorize_text(
        expanded_query_text,
        expand_synonyms=False,
        remove_stopwords=_phase4_stopwords_enabled(),
    )
    q_vec = q_result.v_native
    query_repr_v2 = build_query_representation_v2(expanded_query_text)
    lexical_scores: Dict[UUID, Any] = {}
    graph_scores: Dict[UUID, Dict[str, float]] = {}
    graph_paths: Dict[UUID, List[Dict[str, object]]] = {}
    effective_graph_max_hops = max(1, int(graph_max_hops or 2))
    effective_graph_max_neighbors = max(2, int(graph_max_neighbors or 8))
    effective_graph_decay = float(graph_decay if graph_decay is not None else 0.6)
    effective_graph_alpha = float(graph_alpha if graph_alpha is not None else 0.2)
    effective_graph_diffusion_steps = max(1, int(graph_diffusion_steps or 3))

    # 2b. Apply IDF weighting (Phase 3C)
    try:
        _idf = compute_idf_weights(session, tenant_id, graph_id)
        q_vec = apply_idf(tuple(q_vec), _idf)
    except Exception as exc:
        _degraded("inheritance_query_expansion", exc)
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
        except Exception as exc:
            _degraded("query_cache", exc)
            cache_hit = False

    if not candidates:
        if _phase5_enabled() and _repr_v2_enabled():
            try:
                from index.deterministic_ann import search_vptree
                from index.wand import block_max_wand_shortlist
                from orchestration.perf.index_rebuild import (
                    get_graph_index_artifacts,
                )
                from store.pg.repos.representation_repo import RepresentationRepo

                artifacts = get_graph_index_artifacts(
                    session=session,
                    tenant_id=tenant_id,
                    graph_id=graph_id,
                    graph_version=graph_version,
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
            except Exception as exc:
                _degraded("phase5_hybrid_recall", exc)
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
                    results=[
                        (str(node_id), float(score)) for node_id, score in candidates
                    ],
                )
            except Exception as exc:
                _degraded("index_candidate_recall", exc)
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
        except Exception as exc:
            _degraded("lexical_scoring", exc)
            lexical_scores = {}

    if domain_candidate_ids:
        candidate_ids = _stable_union_ids(candidate_ids, domain_candidate_ids)

    # Phase 3: bounded multi-hop graph semantics and diffusion
    try:
        from core.operators.semantic_typing import KNOWN_SEMANTIC_KINDS
        from core.query.graph_semantics import build_graph_semantic_scores
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
            max_hops=effective_graph_max_hops,
            max_neighbors=effective_graph_max_neighbors,
            decay=effective_graph_decay,
            alpha=effective_graph_alpha,
            steps=effective_graph_diffusion_steps,
        )
        candidate_ids = _stable_union_ids(candidate_ids, graph_candidate_ids)
    except Exception as exc:
        _degraded("graph_semantic_expansion", exc)
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
        include_historical=include_historical,
        as_of=as_of,
    )
    query_fusion_summary = _build_query_fusion_summary(
        candidate_ids=candidate_ids,
        lexical_scores=lexical_scores,
        domain_candidate_ids=domain_candidate_ids,
        graph_scores=graph_scores,
        phaseb_expansion_info=phaseb_expansion_info,
        ranked_item=ranked[0] if ranked else None,
        graph_options={
            "graph_max_hops": effective_graph_max_hops,
            "graph_max_neighbors": effective_graph_max_neighbors,
            "graph_diffusion_steps": effective_graph_diffusion_steps,
            "graph_decay": effective_graph_decay,
            "graph_alpha": effective_graph_alpha,
        },
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
            "supersedes": [str(x) for x in r.get("supersedes", [])],
            "superseded_by": str(r["superseded_by"]) if r.get("superseded_by") else None,
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
            explain_payload["phaseB_query_expansion"] = phaseb_expansion_info
            explain_payload["domain_relevance"] = {
                "query_links": domain_linked_terms[:20],
                "candidate_count": len(domain_candidate_ids),
                "node_scores": domain_scores.get(r["node_id"], {}),
            }
            explain_payload["phase3_graph_paths"] = r.get("graph_paths", [])
            explain_payload["phase3_graph_score"] = {
                "total": r["score_components"].get("graph", 0.0),
                "path": r["score_components"].get("graph_path", 0.0),
                "diffusion": r["score_components"].get("graph_diffusion", 0.0),
                "neighborhood": r["score_components"].get("graph_neighborhood", 0.0),
                "contradiction": r["score_components"].get("graph_contradiction", 0.0),
            }
            explain_payload["phase4_reranker"] = r.get("phase4_explain", {})
            explain_payload["phaseC_late_interaction"] = r.get("phasec_explain", {})
            explain_payload["fusion_summary"] = r.get("fusion_summary", {})
            explain_payload["query_fusion_summary"] = query_fusion_summary
            try:
                from core.query.pulse_protocol import build_node_reason_ledger

                reason_ledger = build_node_reason_ledger(
                    graph_id=graph_id,
                    query_hash=query_hash,
                    node_id=str(r["node_id"]),
                    score=float(r["score"]),
                    score_components=r.get("score_components", {}),
                    explain_payload=explain_payload,
                )
            except Exception as exc:
                _degraded("reason_ledger", exc)
                reason_ledger = {
                    "protocol": "pulse-v2",
                    "trace_id": None,
                    "node_id": str(r["node_id"]),
                    "confidence": 0.0,
                    "event_count": 0,
                    "active_layers": [],
                    "strongest_layers": [],
                    "source_summary": {},
                    "why_glowing": {},
                    "events": [],
                }
            explain_payload["reason_source_ledger"] = reason_ledger
            explain_payload["pulse_event_stream"] = reason_ledger.get("events", [])
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
    except Exception as exc:
        _degraded("answer_synthesis", exc)
        answer = None

    metrics["cache_hit"] = 1.0 if cache_hit else 0.0
    metrics["degraded_feature_count"] = float(len(degraded_features))
    metrics["phaseb_expansion_terms"] = float(len(phaseb_expansions))
    metrics["phaseb_expansion_sources"] = float(
        len(phaseb_expansion_info.get("source_counts", {}))
    )
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
        degraded_features=degraded_features,
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
