"""Standard IR evaluation metrics.

All implementations match the definitions in:
- TREC Evaluation Guidelines
- Voorhees & Harman (2005) TREC: Experiment and Evaluation in IR
- Järvelin & Kekäläinen (2002) nDCG paper
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Set


def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Recall@k = |top-k ∩ relevant| / |relevant|."""
    if not relevant:
        return 0.0
    hits = sum(1 for doc_id in retrieved[:k] if doc_id in relevant)
    return hits / len(relevant)


def precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Precision@k = |top-k ∩ relevant| / k."""
    if k == 0:
        return 0.0
    hits = sum(1 for doc_id in retrieved[:k] if doc_id in relevant)
    return hits / k


def average_precision(retrieved: List[str], relevant: Set[str]) -> float:
    """AP = mean of Precision@k over positions where a relevant doc appears."""
    if not relevant:
        return 0.0
    hits = 0
    sum_precision = 0.0
    for i, doc_id in enumerate(retrieved):
        if doc_id in relevant:
            hits += 1
            sum_precision += hits / (i + 1)
    if hits == 0:
        return 0.0
    return sum_precision / len(relevant)


def reciprocal_rank(retrieved: List[str], relevant: Set[str]) -> float:
    """Reciprocal rank of the first relevant document (1/rank)."""
    for i, doc_id in enumerate(retrieved):
        if doc_id in relevant:
            return 1.0 / (i + 1)
    return 0.0


def dcg_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Discounted Cumulative Gain@k using binary relevance."""
    dcg = 0.0
    for i, doc_id in enumerate(retrieved[:k]):
        if doc_id in relevant:
            dcg += 1.0 / math.log2(i + 2)  # log2(rank+1), rank is 1-indexed
    return dcg


def ndcg_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """nDCG@k = DCG@k / IDCG@k."""
    ideal_hits = min(len(relevant), k)
    if ideal_hits == 0:
        return 0.0
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    if idcg == 0.0:
        return 0.0
    return dcg_at_k(retrieved, relevant, k) / idcg


def compute_all(
    retrieved: List[str],
    relevant: Set[str],
    k_values: Optional[List[int]] = None,
) -> Dict[str, float]:
    """Compute all standard metrics for a single query."""
    if k_values is None:
        k_values = [1, 3, 5, 10]
    result: Dict[str, float] = {}
    for k in k_values:
        result[f"recall@{k}"] = recall_at_k(retrieved, relevant, k)
        result[f"precision@{k}"] = precision_at_k(retrieved, relevant, k)
        result[f"ndcg@{k}"] = ndcg_at_k(retrieved, relevant, k)
    result["mrr"] = reciprocal_rank(retrieved, relevant)
    result["map"] = average_precision(retrieved, relevant)
    return result


def aggregate(per_query: List[Dict[str, float]]) -> Dict[str, float]:
    """Macro-average metrics across all queries."""
    if not per_query:
        return {}
    keys = per_query[0].keys()
    return {k: sum(q[k] for q in per_query) / len(per_query) for k in keys}
