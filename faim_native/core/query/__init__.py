"""FAIM-Native Query Module (Stage-8)."""

from core.query.query_engine import (
    DEFAULT_WEIGHTS,
    STRICT_WEIGHTS,
    QueryPlan,
    ScoringWeights,
    build_explain_payload,
    compute_node_score,
    compute_query_hash,
    cosine_similarity,
    recall_candidates_brute_force,
    recall_candidates_index,
    rerank_faim,
)

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
