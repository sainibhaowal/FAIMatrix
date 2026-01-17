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
) -> List[Tuple[UUID, float]]:
    """Brute-force candidate recall from Postgres.

    Returns list of (node_id, cosine_sim) ordered by similarity desc.
    """
    from store.pg.models_faim import NodeModel

    query = session.query(NodeModel).filter(
        NodeModel.tenant_id == tenant_id,
        NodeModel.graph_id == graph_id,
    )

    if level_filter is not None:
        query = query.filter(NodeModel.level <= level_filter)

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


def recall_candidates_index(
    index,
    tenant_id: str,
    graph_id: str,
    q_vec: Tuple[float, ...],
    n: int = 200,
) -> List[Tuple[UUID, float]]:
    """Index-based candidate recall (Qdrant).

    Returns list of (node_id, score) from index.
    """
    try:
        results = index.search(
            tenant_id=tenant_id,
            graph_id=graph_id,
            vector=list(q_vec),
            k=n,
        )
        return [(UUID(r["id"]), r["score"]) for r in results]
    except Exception:
        # Fallback to empty if index unavailable
        return []


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
) -> List[Dict[str, Any]]:
    """Re-rank candidates using FAIM physics scoring.

    Returns list of result dicts with node_id, score, score_components.
    """
    from store.pg.models_faim import NodeModel

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
            }
        )

    # Stable sort: by score desc, then by node_id for determinism
    scored.sort(key=lambda x: (-x["score"], str(x["node_id"])))

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
        "evidence": {
            "raw_id": node.raw_id,
            "block_id": node.block_id,
            "anchor": node.anchor_json,
        },
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
    "rerank_faim",
    "build_explain_payload",
    "compute_query_hash",
]
