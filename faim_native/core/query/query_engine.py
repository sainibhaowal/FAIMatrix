"""FAIM-Native Query Engine (Stage-8).

Core query components:
- QueryPlan: planning and execution context
- Candidate recall (index or brute-force)
- FAIM re-ranker with physics-based scoring
- Explain payload generation

FAIM Scoring Formula:
    score = w_sim * cosine(q, n.v_native)
          + w_novel * clamp(n.residual)
          - w_opp * opposition_penalty(q, n.opp_signature)
          - w_red * redundancy_penalty(n, graph_R)
          + w_rec * recency_boost(n.last_access)
          + w_use * log1p(n.touch_count)
          - w_lvl * level_penalty(n.level)
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

# TYPE_CHECKING import to help pyright with forward references
from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from orchestration.ingest_flow import FAIMProfile


# Delay import of FAIMProfile to avoid circular at runtime
def _get_profile_class():
    from orchestration.ingest_flow import FAIMProfile

    return FAIMProfile


# =============================================================================
# Scoring Weights (tunable)
# =============================================================================


@dataclass(frozen=True)
class ScoringWeights:
    """FAIM query scoring weights."""

    w_sim: float = 0.40  # Cosine similarity
    w_novel: float = 0.15  # Residual (novelty)
    w_opp: float = 0.10  # Opposition penalty
    w_red: float = 0.10  # Redundancy penalty
    w_rec: float = 0.10  # Recency boost
    w_use: float = 0.10  # Usage boost (log1p(touch_count))
    w_lvl: float = 0.05  # Level penalty (higher level = lower priority)


DEFAULT_WEIGHTS = ScoringWeights()
STRICT_WEIGHTS = ScoringWeights(
    w_sim=0.50,
    w_novel=0.20,
    w_opp=0.10,
    w_red=0.05,
    w_rec=0.05,
    w_use=0.05,
    w_lvl=0.05,
)


# =============================================================================
# QueryPlan - Planning and execution context
# =============================================================================


@dataclass
class QueryPlan:
    """Query execution plan and results."""

    tenant_id: str
    graph_id: str
    query_hash: str
    query_vec: Tuple[float, ...]
    profile: "FAIMProfile"  # noqa: F821
    k: int
    n_candidates: int = 200

    # Filled during execution
    candidate_ids: List[UUID] = field(default_factory=list)
    ranked_results: List[Dict[str, Any]] = field(default_factory=list)
    graph_version: int = 0
    graph_hash: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        tenant_id: str,
        graph_id: str,
        query_vec: Tuple[float, ...],
        profile: "FAIMProfile",  # noqa: F821
        k: int = 10,
        n_candidates: int = 200,
    ) -> "QueryPlan":
        """Create a query plan."""
        # Compute query hash from vector
        query_data = json.dumps(list(query_vec), sort_keys=True)
        query_hash = hashlib.sha256(query_data.encode()).hexdigest()

        return cls(
            tenant_id=tenant_id,
            graph_id=graph_id,
            query_hash=query_hash,
            query_vec=query_vec,
            profile=profile,
            k=k,
            n_candidates=n_candidates,
        )


# =============================================================================
# Cosine Similarity
# =============================================================================


def cosine_similarity(a: Tuple[float, ...], b: Tuple[float, ...]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        raise ValueError(f"Vector dimension mismatch: {len(a)} vs {len(b)}")

    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0

    return dot / (norm_a * norm_b)


# =============================================================================
# Scoring Functions
# =============================================================================


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp value to range."""
    return max(lo, min(hi, x))


def opposition_penalty(
    q_opp: Optional[Dict[str, float]], n_opp: Optional[Dict[str, float]]
) -> float:
    """Compute opposition penalty based on signature overlap."""
    if not q_opp or not n_opp:
        return 0.0

    # Overlap in opposition dimensions
    overlap = 0.0
    for key in q_opp:
        if key in n_opp:
            overlap += abs(q_opp[key] * n_opp[key])

    return _clamp(overlap, 0.0, 1.0)


def redundancy_penalty(n_touch: int, graph_avg_touch: float) -> float:
    """Penalize highly touched (redundant) nodes."""
    if graph_avg_touch <= 0:
        return 0.0

    ratio = n_touch / graph_avg_touch
    # Penalty increases with usage above average
    return _clamp((ratio - 1.0) / 10.0, 0.0, 1.0)


def recency_boost(
    last_access: Optional[datetime], now: Optional[datetime] = None
) -> float:
    """Boost recently accessed nodes."""
    if not last_access:
        return 0.0

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)

    # SQLite may return naive datetimes; treat them as UTC to keep scoring stable.
    if last_access.tzinfo is None:
        last_access = last_access.replace(tzinfo=timezone.utc)
    else:
        last_access = last_access.astimezone(timezone.utc)

    age = (now - last_access).total_seconds()

    # Decay over 7 days
    decay_seconds = 7 * 24 * 3600
    boost = max(0.0, 1.0 - (age / decay_seconds))

    return boost


def level_penalty(level: int) -> float:
    """Penalize higher-level macro nodes."""
    # Level 0 = no penalty, higher levels get penalty
    return _clamp(level * 0.1, 0.0, 1.0)


def compute_node_score(
    q_vec: Tuple[float, ...],
    n_vec: Tuple[float, ...],
    n_residual: float,
    n_opp: Optional[Dict[str, float]],
    n_touch: int,
    n_last_access: Optional[datetime],
    n_level: int,
    graph_avg_touch: float,
    q_opp: Optional[Dict[str, float]] = None,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
) -> Tuple[float, Dict[str, float]]:
    """Compute FAIM score for a node.

    Returns:
        (total_score, score_components dict)
    """
    sim = cosine_similarity(q_vec, n_vec)
    novel = _clamp(n_residual, 0.0, 1.0)
    opp = opposition_penalty(q_opp, n_opp)
    red = redundancy_penalty(n_touch, graph_avg_touch)
    rec = recency_boost(n_last_access)
    use = math.log1p(n_touch) / 10.0  # Normalize
    lvl = level_penalty(n_level)

    score = (
        weights.w_sim * sim
        + weights.w_novel * novel
        - weights.w_opp * opp
        - weights.w_red * red
        + weights.w_rec * rec
        + weights.w_use * use
        - weights.w_lvl * lvl
    )

    components = {
        "sim": round(sim, 6),
        "novel": round(novel, 6),
        "opp": round(opp, 6),
        "red": round(red, 6),
        "rec": round(rec, 6),
        "use": round(use, 6),
        "lvl": round(lvl, 6),
    }

    return round(score, 6), components


# =============================================================================
# Candidate Recall
# =============================================================================


def recall_candidates_brute_force(
    session,
    tenant_id: str,
    graph_id: str,
    q_vec: Tuple[float, ...],
    n: int = 200,
    level_filter: Optional[int] = None,
    cluster_ids: Optional[List[int]] = None,
) -> List[Tuple[UUID, float]]:
    """Brute-force candidate recall from Postgres.

    If cluster_ids is provided (from cluster scoping), filters to those clusters first,
    then falls back to full scan if the filtered result is too small.

    Returns list of (node_id, cosine_sim) ordered by similarity desc.
    """
    from store.pg.models_faim import NodeModel

    query = session.query(NodeModel).filter(
        NodeModel.tenant_id == tenant_id,
        NodeModel.graph_id == graph_id,
    )

    if level_filter is not None:
        query = query.filter(NodeModel.level <= level_filter)

    # Cluster scoping: filter to relevant clusters when available
    if cluster_ids:
        scoped_query = query.filter(NodeModel.cluster_id.in_(cluster_ids))
        scoped_nodes = scoped_query.limit(n * 10).all()
        # Fall back to full scan if cluster filter yields too few candidates
        if len(scoped_nodes) >= max(10, n // 2):
            candidates = []
            for node in scoped_nodes:
                n_vec = (
                    tuple(node.v_native)
                    if isinstance(node.v_native, list)
                    else tuple(node.v_native)
                )
                sim = cosine_similarity(q_vec, n_vec)
                candidates.append((node.node_id, sim))
            candidates.sort(key=lambda x: (-x[1], str(x[0])))
            return candidates[:n]

    # Limit scan for performance
    nodes = query.limit(n * 10).all()

    # Compute similarities
    candidates = []
    for node in nodes:
        n_vec = (
            tuple(node.v_native)
            if isinstance(node.v_native, list)
            else tuple(node.v_native)
        )
        sim = cosine_similarity(q_vec, n_vec)
        candidates.append((node.node_id, sim))

    # Sort by similarity descending, then by node_id for determinism
    candidates.sort(key=lambda x: (-x[1], str(x[0])))

    return candidates[:n]


def recall_with_graph_expansion(
    session,
    tenant_id: str,
    graph_id: str,
    q_vec: Tuple[float, ...],
    n: int = 200,
    seed_k: int = 30,
    hop_limit: int = 8,
    graph_max_hops: int = 2,
    graph_max_neighbors: Optional[int] = None,
    graph_decay: float = 0.6,
    graph_alpha: float = 0.2,
    graph_diffusion_steps: int = 3,
) -> List[Tuple[UUID, float]]:
    """Recall candidates using cosine seeds + 1-hop inheritance edge expansion + semantic edges.

    Step 1: Get top-k cosine matches (seeds)
    Step 2: Expand via 1-hop inheritance edges (parents + children)
    Step 2c: Semantic edge traversal with score boost
    Step 3: Score expanded set and return top-n

    Returns list of (node_id, cosine_sim) ordered by similarity desc.
    """
    from core.clustering import nearest_cluster
    from core.operators.semantic_typing import KNOWN_SEMANTIC_KINDS
    from sqlalchemy import or_
    from store.pg.models_faim import EdgeModel, GraphClusterModel, NodeModel

    # Cluster scoping: load centers and find top-2 clusters for this query
    cluster_ids: Optional[List[int]] = None
    try:
        cluster_rows = (
            session.query(GraphClusterModel)
            .filter(
                GraphClusterModel.tenant_id == tenant_id,
                GraphClusterModel.graph_id == graph_id,
            )
            .all()
        )
        if len(cluster_rows) >= 2:
            centers = [None] * len(cluster_rows)
            for row in cluster_rows:
                if 0 <= row.cluster_id < len(centers):
                    centers[row.cluster_id] = list(row.center) if row.center else []
            q_list = list(q_vec)
            cluster_ids = nearest_cluster(q_list, [c for c in centers if c], top_k=2)
    except Exception:
        cluster_ids = None  # silently fall back to full scan

    # Step 1: Fast seed recall — top seed_k by cosine (cluster-scoped if available)
    seeds = recall_candidates_brute_force(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        q_vec=q_vec,
        n=seed_k,
        cluster_ids=cluster_ids,
    )
    if not seeds:
        return []

    seed_ids = [node_id for node_id, _ in seeds]
    expanded_ids: set = set(seed_ids)

    # Step 2a: Batch query — parents of seeds (src -> seed via inheritance)
    parent_rows = (
        session.query(EdgeModel.src_node_id, EdgeModel.dst_node_id)
        .filter(
            EdgeModel.tenant_id == tenant_id,
            EdgeModel.graph_id == graph_id,
            EdgeModel.kind == "inheritance",
            EdgeModel.dst_node_id.in_(seed_ids),
        )
        .limit(seed_k * hop_limit)
        .all()
    )
    for src, _dst in parent_rows:
        expanded_ids.add(src)

    # Step 2b: Batch query — children of seeds (seed -> child via inheritance)
    child_rows = (
        session.query(EdgeModel.src_node_id, EdgeModel.dst_node_id)
        .filter(
            EdgeModel.tenant_id == tenant_id,
            EdgeModel.graph_id == graph_id,
            EdgeModel.kind == "inheritance",
            EdgeModel.src_node_id.in_(seed_ids),
        )
        .limit(seed_k * hop_limit)
        .all()
    )
    for _src, dst in child_rows:
        expanded_ids.add(dst)

    # Step 2c: Semantic edge expansion — traverse semantic edges (synonym, hypernym, hyponym, related)
    # connected to seeds, track semantic weight as boost
    semantic_boost: Dict[UUID, float] = {}
    if KNOWN_SEMANTIC_KINDS:
        semantic_rows = (
            session.query(
                EdgeModel.src_node_id,
                EdgeModel.dst_node_id,
                EdgeModel.kind,
                EdgeModel.weight,
            )
            .filter(
                EdgeModel.tenant_id == tenant_id,
                EdgeModel.graph_id == graph_id,
                EdgeModel.kind.in_(list(KNOWN_SEMANTIC_KINDS)),
                or_(
                    EdgeModel.src_node_id.in_(seed_ids),
                    EdgeModel.dst_node_id.in_(seed_ids),
                ),
            )
            .limit(seed_k * hop_limit)
            .all()
        )

        for src, dst, _kind, weight_int in semantic_rows:
            # Expand both directions from seed
            if src in seed_ids:
                expanded_ids.add(dst)
                # Track weight (max semantic weight for this node)
                semantic_weight = weight_int / 1e9 if weight_int else 1.0
                semantic_boost[dst] = max(semantic_boost.get(dst, 0.0), semantic_weight)
            if dst in seed_ids:
                expanded_ids.add(src)
                semantic_weight = weight_int / 1e9 if weight_int else 1.0
                semantic_boost[src] = max(semantic_boost.get(src, 0.0), semantic_weight)

    # Step 2d: Phase 3 graph semantics and bounded multi-hop diffusion
    try:
        from core.query.graph_semantics import build_graph_semantic_scores
        from store.pg.repos.edge_repo import EdgeRepo
        from store.pg.repos.node_repo import NodeRepo

        seed_score_map = {node_id: max(0.0, score) for node_id, score in seeds}
        graph_candidate_ids, graph_scores, _graph_paths = build_graph_semantic_scores(
            edge_repo=EdgeRepo(session=session, tenant_id=tenant_id),
            node_repo=NodeRepo(session=session, tenant_id=tenant_id),
            graph_id=graph_id,
            seed_scores=seed_score_map,
            base_candidate_ids=sorted(expanded_ids, key=str),
            allowed_kinds={"inheritance"} | KNOWN_SEMANTIC_KINDS | {"opposition"},
            max_hops=max(1, int(graph_max_hops)),
            max_neighbors=max(2, int(graph_max_neighbors or hop_limit)),
            decay=graph_decay,
            alpha=graph_alpha,
            steps=max(1, int(graph_diffusion_steps)),
        )
        expanded_ids = set(graph_candidate_ids)
    except Exception:
        graph_scores = {}

    # Step 3: Load and score the full expanded set
    expanded_nodes = (
        session.query(NodeModel)
        .filter(
            NodeModel.tenant_id == tenant_id,
            NodeModel.graph_id == graph_id,
            NodeModel.node_id.in_(list(expanded_ids)),
        )
        .all()
    )

    candidates: List[Tuple[UUID, float]] = []
    for node in expanded_nodes:
        n_vec = (
            tuple(node.v_native)
            if isinstance(node.v_native, list)
            else tuple(node.v_native)
        )
        raw_sim = cosine_similarity(q_vec, n_vec)

        # Apply semantic boost if node has semantic edges to seeds
        semantic_alpha = 0.05
        boost = semantic_boost.get(node.node_id, 0.0)
        graph_boost = 0.0
        if graph_scores:
            graph_boost = graph_scores.get(node.node_id, {}).get("total", 0.0)
        effective_sim = min(1.0, raw_sim + semantic_alpha * boost + 0.08 * graph_boost)

        candidates.append((node.node_id, effective_sim))

    candidates.sort(key=lambda x: (-x[1], str(x[0])))
    return candidates[:n]


def recall_candidates_index(
    index,
    tenant_id: str,
    graph_id: str,
    q_vec: Tuple[float, ...],
    n: int = 200,
) -> List[Tuple[UUID, float]]:
    """Index-based candidate recall.

    Supports both contracts:
    - Preferred: ``index.top_k(graph_id, query_vec, k)``
    - Legacy: ``index.search(tenant_id=..., graph_id=..., vector=..., k=...)``
    """
    try:
        results: List[Tuple[UUID, float]] = []

        if hasattr(index, "top_k"):
            raw = index.top_k(graph_id=graph_id, query_vec=q_vec, k=n)
            for node_id, score in raw:
                try:
                    results.append((UUID(str(node_id)), float(score)))
                except (ValueError, TypeError):
                    continue
        elif hasattr(index, "search"):
            raw = index.search(
                tenant_id=tenant_id,
                graph_id=graph_id,
                vector=list(q_vec),
                k=n,
            )
            for item in raw:
                node_id = item.get("id") if isinstance(item, dict) else None
                score = item.get("score") if isinstance(item, dict) else None
                try:
                    results.append((UUID(str(node_id)), float(score)))
                except (ValueError, TypeError):
                    continue
        else:
            return []

        # Stable ordering to preserve deterministic behavior on ties.
        results.sort(key=lambda x: (-x[1], str(x[0])))
        return results[:n]
    except Exception:
        # Fallback to empty if index unavailable
        return []


# =============================================================================
# Inheritance-Weighted Query Expansion (Phase 7)
# =============================================================================


def inheritance_weighted_expansion(
    session,
    tenant_id: str,
    graph_id: str,
    q_vec: Tuple[float, ...],
    seed_node_ids: List[UUID],
    alpha: float = 0.2,
    max_parents: int = 3,
) -> Tuple[float, ...]:
    """Blend query vector with inheritance-weighted parent vectors of seed nodes.

    For each seed node, traverses its parent edges and adds:
        alpha * fraction * semantic_weight * parent_v_native
    to the query vector, with semantic_weight from edge meta (default 1.0).
    Also blends semantic edges (synonym, hypernym, hyponym, related) with
    semantic_alpha = alpha * 0.5.

    Then re-normalizes.

    Args:
        session: SQLAlchemy session
        tenant_id: Tenant ID
        graph_id: Graph ID
        q_vec: Original query vector (256-dim)
        seed_node_ids: Top-k candidate node IDs from initial recall
        alpha: Blending weight for parent contribution (0.0 = no expansion, 1.0 = full)
        max_parents: Max parents to traverse per seed node

    Returns:
        Expanded and re-normalized query vector (256-dim tuple)
    """
    from core.operators.semantic_typing import (
        KNOWN_SEMANTIC_KINDS,
        get_semantic_weight_from_meta,
    )
    from sqlalchemy import or_
    from store.pg.models_faim import EdgeModel, NodeModel

    if not seed_node_ids:
        return q_vec

    # Batch-load all parent edges (inheritance) for seed nodes
    parent_edges = (
        session.query(EdgeModel)
        .filter(
            EdgeModel.tenant_id == tenant_id,
            EdgeModel.graph_id == graph_id,
            EdgeModel.kind == "inheritance",
            EdgeModel.dst_node_id.in_(seed_node_ids),
        )
        .all()
    )

    # Batch-load semantic edges connected to seeds (Layer B)
    semantic_edges = []
    if KNOWN_SEMANTIC_KINDS:
        semantic_edges = (
            session.query(EdgeModel)
            .filter(
                EdgeModel.tenant_id == tenant_id,
                EdgeModel.graph_id == graph_id,
                EdgeModel.kind.in_(list(KNOWN_SEMANTIC_KINDS)),
                or_(
                    EdgeModel.src_node_id.in_(seed_node_ids),
                    EdgeModel.dst_node_id.in_(seed_node_ids),
                ),
            )
            .limit(len(seed_node_ids) * 5)
            .all()
        )

    if not parent_edges and not semantic_edges:
        return q_vec  # no expansion available

    # Group by dst_node_id, take top max_parents by fraction (weight)
    from collections import defaultdict

    seed_parents: Dict[UUID, List[EdgeModel]] = defaultdict(list)
    for edge in parent_edges:
        seed_parents[edge.dst_node_id].append(edge)

    # Collect all unique parent IDs to load (from inheritance)
    parent_ids_to_load: set = set()
    for edges in seed_parents.values():
        top_edges = sorted(edges, key=lambda e: -e.weight)[:max_parents]
        for edge in top_edges:
            parent_ids_to_load.add(edge.src_node_id)

    # Collect semantic neighbor IDs to load (from semantic edges)
    semantic_neighbor_ids: set = set()
    for edge in semantic_edges:
        if edge.src_node_id in seed_node_ids:
            semantic_neighbor_ids.add(edge.dst_node_id)
        elif edge.dst_node_id in seed_node_ids:
            semantic_neighbor_ids.add(edge.src_node_id)

    all_nodes_to_load = parent_ids_to_load | semantic_neighbor_ids
    if not all_nodes_to_load:
        return q_vec

    # Load all vectors (parents + semantic neighbors)
    all_nodes = (
        session.query(NodeModel)
        .filter(
            NodeModel.tenant_id == tenant_id,
            NodeModel.graph_id == graph_id,
            NodeModel.node_id.in_(list(all_nodes_to_load)),
        )
        .all()
    )
    vec_map: Dict[UUID, Tuple[float, ...]] = {
        n.node_id: (
            tuple(n.v_native) if isinstance(n.v_native, list) else tuple(n.v_native)
        )
        for n in all_nodes
    }

    # Blend: expanded = q_vec + inheritance_contribution + semantic_contribution
    dim = len(q_vec)
    expanded: List[float] = list(q_vec)

    # Phase 7 inheritance blending with semantic weight modifier (Layer A)
    for edges in seed_parents.values():
        top_edges = sorted(edges, key=lambda e: -e.weight)[:max_parents]
        for edge in top_edges:
            fraction = edge.weight / 1e9

            # Extract semantic_weight from edge meta (Layer A), default 1.0
            semantic_weight = get_semantic_weight_from_meta(edge.meta)

            parent_vec = vec_map.get(edge.src_node_id)
            if parent_vec:
                for i in range(dim):
                    expanded[i] += alpha * fraction * semantic_weight * parent_vec[i]

    # Semantic edge blending (Layer B) with reduced alpha
    semantic_alpha = alpha * 0.5
    for edge in semantic_edges:
        neighbor_id = None
        if edge.src_node_id in seed_node_ids:
            neighbor_id = edge.dst_node_id
        elif edge.dst_node_id in seed_node_ids:
            neighbor_id = edge.src_node_id

        if neighbor_id and neighbor_id in vec_map:
            # Use edge weight as semantic strength (already 0.0-1.0 when divided by 1e9)
            semantic_strength = edge.weight / 1e9 if edge.weight else 1.0
            neighbor_vec = vec_map[neighbor_id]
            for i in range(dim):
                expanded[i] += semantic_alpha * semantic_strength * neighbor_vec[i]

    # Re-normalize L2
    norm = math.sqrt(sum(x * x for x in expanded)) or 1.0
    return tuple(x / norm for x in expanded)


# =============================================================================
# FAIM Re-ranker
# =============================================================================


def rerank_faim(
    session,
    tenant_id: str,
    graph_id: str,
    q_vec: Tuple[float, ...],
    candidate_ids: List[UUID],
    graph_avg_touch: float = 1.0,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
    k: int = 10,
    lexical_scores: Optional[Dict[UUID, Tuple[float, Dict[str, float]]]] = None,
    graph_scores: Optional[Dict[UUID, Dict[str, float]]] = None,
    graph_paths: Optional[Dict[UUID, List[Dict[str, object]]]] = None,
    domain_scores: Optional[Dict[UUID, Dict[str, float]]] = None,
    query_text: str = "",
    query_repr_v2=None,
    include_historical: bool = True,
) -> List[Dict[str, Any]]:
    """Re-rank candidates using FAIM physics scoring.

    Returns list of result dicts with node_id, score, score_components.
    """
    from core.query.reranker_v2 import RerankerV2Candidate, score_reranker_v2
    from store.pg.models_faim import NodeModel
    from store.pg.repos.modality_repo import ModalityRepo
    from store.pg.repos.representation_repo import RepresentationRepo

    # Load candidate nodes
    nodes = (
        session.query(NodeModel)
        .filter(
            NodeModel.tenant_id == tenant_id,
            NodeModel.graph_id == graph_id,
            NodeModel.node_id.in_(candidate_ids),
        )
        .all()
    )

    # Score each node
    scored = []
    repr_repo = RepresentationRepo(session=session, tenant_id=tenant_id)
    repr_rows = {
        row.node_id: row
        for row in repr_repo.list_by_node_ids(graph_id=graph_id, node_ids=candidate_ids)
    }
    modality_repo = ModalityRepo(session=session, tenant_id=tenant_id)
    modality_rows = {
        row.node_id: row
        for row in modality_repo.list_by_node_ids(
            graph_id=graph_id, node_ids=candidate_ids
        )
    }
    for node in nodes:
        n_vec = (
            tuple(node.v_native)
            if isinstance(node.v_native, list)
            else tuple(node.v_native)
        )
        n_opp = node.opp_signature if isinstance(node.opp_signature, dict) else {}

        score, components = compute_node_score(
            q_vec=q_vec,
            n_vec=n_vec,
            n_residual=node.residual / 1e9 if node.residual else 0.0,
            n_opp=n_opp,
            n_touch=node.touch_count or 0,
            n_last_access=node.last_access,
            n_level=node.level or 0,
            graph_avg_touch=graph_avg_touch,
            weights=weights,
        )

        lex_score = 0.0
        lex_components: Dict[str, float] = {}
        if lexical_scores and node.node_id in lexical_scores:
            lex_score, lex_components = lexical_scores[node.node_id]
            score = round(score + 0.15 * lex_score, 6)
        components["lex"] = round(lex_score, 6)
        for key, value in lex_components.items():
            components[f"lex_{key}"] = round(value, 6)

        graph_total = 0.0
        graph_components: Dict[str, float] = {}
        if graph_scores and node.node_id in graph_scores:
            graph_components = graph_scores[node.node_id]
            graph_total = graph_components.get("total", 0.0)
            score = round(score + 0.12 * graph_total, 6)
        components["graph"] = round(graph_total, 6)
        for key, value in graph_components.items():
            if key == "total":
                continue
            components[f"graph_{key}"] = round(value, 6)

        modality_score = 0.0
        modality_row = modality_rows.get(node.node_id)
        if modality_row is not None and query_text:
            query_terms = {term for term in query_text.lower().split() if term}
            ocr_terms = set(str(modality_row.ocr_text or "").lower().split())
            table_terms = set(str(modality_row.table_text or "").lower().split())
            filename_terms = set(modality_row.filename_tokens or [])
            overlap = 0.0
            if query_terms:
                overlap += len(query_terms & ocr_terms) / len(query_terms)
                overlap += len(query_terms & table_terms) / len(query_terms)
                overlap += len(query_terms & filename_terms) / len(query_terms)
            modality_score = min(1.0, overlap / 3.0)
            score = round(score + 0.08 * modality_score, 6)
        components["modality"] = round(modality_score, 6)

        domain_total = 0.0
        if domain_scores and node.node_id in domain_scores:
            entity_link = float(domain_scores[node.node_id].get("entity_link", 0.0))
            fact_support = float(domain_scores[node.node_id].get("fact_support", 0.0))
            domain_term = float(domain_scores[node.node_id].get("domain_term", 0.0))
            domain_total = min(
                1.0, 0.45 * entity_link + 0.40 * fact_support + 0.15 * domain_term
            )
            score = round(score + 0.10 * domain_total, 6)
            components["domain_entity_link"] = round(entity_link, 6)
            components["domain_fact_support"] = round(fact_support, 6)
            components["domain_term"] = round(domain_term, 6)
        components["domain"] = round(domain_total, 6)

        repr_row = repr_rows.get(node.node_id)
        answer_text = ""
        if repr_row is not None and getattr(repr_row, "normalized_text", None):
            answer_text = str(repr_row.normalized_text)
        elif modality_row is not None:
            answer_text = str(modality_row.ocr_text or "") or str(
                modality_row.table_text or ""
            )
        scored.append(
            {
                "node_id": node.node_id,
                "vector_hash": node.vector_hash,
                "score": score,
                "score_components": components,
                "level": node.level,
                "touch_count": node.touch_count,
                "raw_id": node.raw_id,
                "block_id": node.block_id,
                "anchor": node.anchor_json,
                "created_at": node.created_at,
                "graph_paths": (graph_paths or {}).get(node.node_id, []),
                "repr_v2": repr_repo._row_to_repr(repr_row) if repr_row else None,
                "answer_text": answer_text,
            }
        )

    # --- PHASE 4: Deterministic reranker v2 ---
    if query_text and query_repr_v2 is not None and scored:
        phase4_candidates = [
            RerankerV2Candidate(
                node_id=item["node_id"],
                created_at=item.get("created_at"),
                representation=item.get("repr_v2"),
                base_score=float(item["score"]),
            )
            for item in scored
        ]
        phase4_totals, phase4_components, phase4_explain, phase4_suppressed = (
            score_reranker_v2(
                query_text=query_text,
                query_repr=query_repr_v2,
                candidates=phase4_candidates,
            )
        )
        for item in scored:
            phase4_total = phase4_totals.get(item["node_id"], 0.0)
            item["score"] = round(item["score"] + 0.18 * phase4_total, 6)
            item["score_components"]["phase4"] = round(phase4_total, 6)
            for key, value in phase4_components.get(item["node_id"], {}).items():
                item["score_components"][f"phase4_{key}"] = round(value, 6)
            item["phase4_explain"] = phase4_explain.get(item["node_id"], {})
        if phase4_suppressed:
            scored = [
                item for item in scored if item["node_id"] not in phase4_suppressed
            ]

    # Stable sort: by score desc, then by node_id for determinism
    scored.sort(key=lambda x: (-x["score"], str(x["node_id"])))

    # --- PHASE 1 + PHASE 6: Advanced Opposition Suppression & Transitive Temporal Contradiction Resolution ---
    temporal_labels: Dict[UUID, str] = {}  # node_id → "CURRENT" | "HISTORICAL"
    superseded_by_map: Dict[UUID, UUID] = {}  # node_id → newer_node_id
    supersedes_map: Dict[UUID, List[UUID]] = {}  # node_id → list of older_node_ids

    if len(candidate_ids) > 1:
        from store.pg.models_faim import EdgeModel, NodeModel
        from collections import defaultdict

        # 1. Resolve Ancestors for each candidate (up to 2-hop inheritance paths)
        ancestors: Dict[UUID, set] = {cid: {cid} for cid in candidate_ids}

        # Hop 1 of inheritance lookup
        hop1_edges = (
            session.query(EdgeModel)
            .filter(
                EdgeModel.tenant_id == tenant_id,
                EdgeModel.graph_id == graph_id,
                EdgeModel.kind == "inheritance",
                EdgeModel.dst_node_id.in_(candidate_ids),
            )
            .all()
        )

        hop1_parents = defaultdict(set)
        for edge in hop1_edges:
            hop1_parents[edge.dst_node_id].add(edge.src_node_id)
            ancestors[edge.dst_node_id].add(edge.src_node_id)

        # Hop 2 of inheritance lookup
        hop1_parent_ids = list({pid for parents in hop1_parents.values() for pid in parents})
        if hop1_parent_ids:
            hop2_edges = (
                session.query(EdgeModel)
                .filter(
                    EdgeModel.tenant_id == tenant_id,
                    EdgeModel.graph_id == graph_id,
                    EdgeModel.kind == "inheritance",
                    EdgeModel.dst_node_id.in_(hop1_parent_ids),
                )
                .all()
            )
            hop2_parents = defaultdict(set)
            for edge in hop2_edges:
                hop2_parents[edge.dst_node_id].add(edge.src_node_id)

            # Map second hop to original candidates
            for cid in candidate_ids:
                for p1 in hop1_parents[cid]:
                    for p2 in hop2_parents[p1]:
                        ancestors[cid].add(p2)

        # Collect all unique ancestors to perform a single batch query for opposition
        all_ancestors = set()
        for cid in candidate_ids:
            all_ancestors.update(ancestors[cid])

        # 2. Query opposition edges among all ancestors in the candidate space
        opp_edges = []
        if len(all_ancestors) > 1:
            opp_edges = (
                session.query(EdgeModel)
                .filter(
                    EdgeModel.tenant_id == tenant_id,
                    EdgeModel.graph_id == graph_id,
                    EdgeModel.kind == "opposition",
                    EdgeModel.src_node_id.in_(list(all_ancestors)),
                    EdgeModel.dst_node_id.in_(list(all_ancestors)),
                )
                .all()
            )

        if opp_edges:
            opp_pairs = {(edge.src_node_id, edge.dst_node_id) for edge in opp_edges}
            opp_pairs.update({(edge.dst_node_id, edge.src_node_id) for edge in opp_edges})

            # 3. Detect contradictions between candidate pairs
            contradictions = []
            for i in range(len(candidate_ids)):
                for j in range(i + 1, len(candidate_ids)):
                    ci = candidate_ids[i]
                    cj = candidate_ids[j]
                    conflicting = False
                    for anc_i in ancestors[ci]:
                        for anc_j in ancestors[cj]:
                            if (anc_i, anc_j) in opp_pairs:
                                conflicting = True
                                break
                        if conflicting:
                            break
                    if conflicting:
                        contradictions.append((ci, cj))

            if contradictions:
                # Load created_at timestamps for all involved candidates
                opp_node_ids = set()
                for ci, cj in contradictions:
                    opp_node_ids.add(ci)
                    opp_node_ids.add(cj)

                ts_rows = (
                    session.query(NodeModel.node_id, NodeModel.created_at)
                    .filter(NodeModel.node_id.in_(list(opp_node_ids)))
                    .all()
                )
                created_at_map = {row.node_id: row.created_at for row in ts_rows}
                score_map = {r["node_id"]: r["score"] for r in scored}

                to_suppress: set = set()
                for ci, cj in contradictions:
                    # Skip if either is already marked for hard suppression (only if hard suppression is active)
                    if not include_historical and (ci in to_suppress or cj in to_suppress):
                        continue

                    ts_i = created_at_map.get(ci)
                    ts_j = created_at_map.get(cj)

                    # Determine CURRENT vs HISTORICAL (newer = CURRENT)
                    is_i_newer = True
                    if ts_i and ts_j:
                        is_i_newer = (ts_i >= ts_j)
                    else:
                        is_i_newer = (score_map.get(ci, -999.0) >= score_map.get(cj, -999.0))

                    if is_i_newer:
                        current_node, historical_node = ci, cj
                    else:
                        current_node, historical_node = cj, ci

                    temporal_labels[current_node] = "CURRENT"
                    temporal_labels[historical_node] = "HISTORICAL"
                    superseded_by_map[historical_node] = current_node
                    if current_node not in supersedes_map:
                        supersedes_map[current_node] = []
                    if historical_node not in supersedes_map[current_node]:
                        supersedes_map[current_node].append(historical_node)

                    # Suppress older contradiction results only if include_historical is False
                    if not include_historical:
                        to_suppress.add(historical_node)

                if to_suppress:
                    scored = [r for r in scored if r["node_id"] not in to_suppress]

    # Apply temporal status and lineage mapping
    for r in scored:
        nid = r["node_id"]
        r["temporal_status"] = temporal_labels.get(nid)
        r["superseded_by"] = superseded_by_map.get(nid)
        r["supersedes"] = supersedes_map.get(nid, [])
        r.pop("repr_v2", None)
    # --- END PHASE 1 + PHASE 6 ---

    return scored[:k]


# =============================================================================
# Explain Payload
# =============================================================================


def build_explain_payload(
    session,
    tenant_id: str,
    graph_id: str,
    node_id: UUID,
) -> Dict[str, Any]:
    """Build explain payload for a node.

    Returns:
        - node data
        - parents + fractions
        - opposition neighbors
        - evidence anchor
    """
    from store.pg.models_faim import EdgeModel, NodeModel
    from store.pg.repos.representation_repo import RepresentationRepo

    # Load node
    node = (
        session.query(NodeModel)
        .filter(
            NodeModel.tenant_id == tenant_id,
            NodeModel.graph_id == graph_id,
            NodeModel.node_id == node_id,
        )
        .first()
    )

    if not node:
        return {"error": "Node not found"}

    repr_repo = RepresentationRepo(session=session, tenant_id=tenant_id)
    repr_rows = repr_repo.list_by_node_ids(graph_id=graph_id, node_ids=[node_id])
    repr_row = repr_rows[0] if repr_rows else None

    # Load inheritance parents
    parents = (
        session.query(EdgeModel)
        .filter(
            EdgeModel.tenant_id == tenant_id,
            EdgeModel.graph_id == graph_id,
            EdgeModel.dst_node_id == node_id,
            EdgeModel.kind == "inheritance",
        )
        .all()
    )

    parent_list = [
        {"parent_id": str(p.src_node_id), "fraction": p.weight / 1e9} for p in parents
    ]

    # Load opposition edges
    oppositions = (
        session.query(EdgeModel)
        .filter(
            EdgeModel.tenant_id == tenant_id,
            EdgeModel.graph_id == graph_id,
            EdgeModel.kind == "opposition",
        )
        .filter((EdgeModel.src_node_id == node_id) | (EdgeModel.dst_node_id == node_id))
        .limit(10)
        .all()
    )

    opp_list = []
    for o in oppositions:
        other_id = o.dst_node_id if o.src_node_id == node_id else o.src_node_id
        opp_list.append(
            {
                "other_id": str(other_id),
                "magnitude": o.weight / 1e9,
            }
        )

    semantic_neighbors = (
        session.query(EdgeModel)
        .filter(
            EdgeModel.tenant_id == tenant_id,
            EdgeModel.graph_id == graph_id,
            EdgeModel.kind != "inheritance",
            EdgeModel.kind != "opposition",
        )
        .filter((EdgeModel.src_node_id == node_id) | (EdgeModel.dst_node_id == node_id))
        .limit(12)
        .all()
    )
    graph_paths = []
    for edge in semantic_neighbors:
        other_id = edge.dst_node_id if edge.src_node_id == node_id else edge.src_node_id
        graph_paths.append(
            {
                "to_node_id": str(other_id),
                "kind": edge.kind,
                "weight": edge.weight / 1e9 if edge.weight else 0.0,
            }
        )

    return {
        "node_id": str(node.node_id),
        "vector_hash": node.vector_hash,
        "level": node.level,
        "kind": node.kind,
        "residual": node.residual / 1e9 if node.residual else 0.0,
        "touch_count": node.touch_count,
        "last_access": node.last_access.isoformat() if node.last_access else None,
        "created_at": node.created_at.isoformat() if node.created_at else None,
        "parents": parent_list,
        "parents_sum": sum(p["fraction"] for p in parent_list),
        "oppositions": opp_list,
        "graph_paths": graph_paths,
        "evidence": {
            "raw_id": node.raw_id,
            "block_id": node.block_id,
            "anchor": node.anchor_json,
        },
        "semantic_signature": (
            {
                "alias_families": list(repr_row.alias_families or []),
                "transliterated_tokens": list(repr_row.transliterated_tokens or []),
                "stem_families": list(repr_row.stem_families or []),
                "relation_cues": list(repr_row.relation_cues or []),
                "value_cues": list(repr_row.value_cues or []),
                "temporal_cues": list(repr_row.temporal_cues or []),
                "semantic_phrase_bucket_count": len(
                    dict(repr_row.semantic_phrase_counts or {})
                ),
                "concept_bucket_count": len(dict(repr_row.concept_counts or {})),
                "morphology_bucket_count": len(
                    dict(repr_row.morphology_counts or {})
                ),
            }
            if repr_row is not None
            else None
        ),
    }


# =============================================================================
# Query Hash Computation
# =============================================================================


def compute_query_hash(query_text: str, graph_id: str) -> str:
    """Compute deterministic query hash."""
    data = json.dumps({"q": query_text, "g": graph_id}, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "QueryPlan",
    "ScoringWeights",
    "DEFAULT_WEIGHTS",
    "STRICT_WEIGHTS",
    "cosine_similarity",
    "compute_node_score",
    "recall_candidates_brute_force",
    "recall_candidates_index",
    "recall_with_graph_expansion",
    "inheritance_weighted_expansion",
    "rerank_faim",
    "build_explain_payload",
    "compute_query_hash",
]
