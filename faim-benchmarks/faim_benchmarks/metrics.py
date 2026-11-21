"""Standard IR, QA, latency, and 95% bootstrap confidence-interval metrics."""

from __future__ import annotations

import math
import random
import re
import string
from collections import Counter
from typing import Any, Dict, Iterable, List, Sequence, Set


def recall_at_k(retrieved: Sequence[str], relevant: Set[str], k: int) -> float:
    if not relevant or k <= 0:
        return 0.0
    hits = sum(1 for doc_id in retrieved[:k] if doc_id in relevant)
    return hits / len(relevant)


def precision_at_k(retrieved: Sequence[str], relevant: Set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top = retrieved[:k]
    if not top:
        return 0.0
    hits = sum(1 for doc_id in top if doc_id in relevant)
    return hits / len(top)


def ndcg_at_k(retrieved: Sequence[str], qrels: Dict[str, float], k: int) -> float:
    if not qrels or k <= 0:
        return 0.0
    dcg = 0.0
    for idx, doc_id in enumerate(retrieved[:k], start=1):
        rel = float(qrels.get(doc_id, 0.0))
        if rel > 0:
            dcg += (2.0**rel - 1.0) / math.log2(idx + 1)

    ideal_rels = sorted((float(v) for v in qrels.values() if v > 0), reverse=True)[:k]
    idcg = sum(
        (2.0**rel - 1.0) / math.log2(idx + 1)
        for idx, rel in enumerate(ideal_rels, start=1)
    )
    return (dcg / idcg) if idcg > 0 else 0.0


def mrr(retrieved: Sequence[str], relevant: Set[str]) -> float:
    for idx, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / idx
    return 0.0


def average_precision(retrieved: Sequence[str], relevant: Set[str]) -> float:
    if not relevant:
        return 0.0
    hits = 0
    total = 0.0
    for idx, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            hits += 1
            total += hits / idx
    return total / len(relevant)


def compute_ir_metrics(
    retrieved: Sequence[str],
    qrels: Dict[str, float],
    k_values: Iterable[int] = (1, 3, 5, 10),
) -> Dict[str, float]:
    relevant = {doc_id for doc_id, score in qrels.items() if float(score) > 0}
    out: Dict[str, float] = {
        "mrr": mrr(retrieved, relevant),
        "map": average_precision(retrieved, relevant),
    }
    for k in k_values:
        out[f"recall@{k}"] = recall_at_k(retrieved, relevant, k)
        out[f"precision@{k}"] = precision_at_k(retrieved, relevant, k)
        out[f"ndcg@{k}"] = ndcg_at_k(retrieved, qrels, k)
    return out


def _normalize_answer(text: str) -> str:
    text = text.lower()
    text = "".join(ch for ch in text if ch not in set(string.punctuation))
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    return " ".join(text.split())


def exact_match(prediction: str, gold: str) -> float:
    return 1.0 if _normalize_answer(prediction) == _normalize_answer(gold) else 0.0


def token_f1(prediction: str, gold: str) -> float:
    pred_tokens = _normalize_answer(prediction).split()
    gold_tokens = _normalize_answer(gold).split()
    if not pred_tokens and not gold_tokens:
        return 1.0
    if not pred_tokens or not gold_tokens:
        return 0.0
    common = Counter(pred_tokens) & Counter(gold_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    prec = num_same / len(pred_tokens)
    rec = num_same / len(gold_tokens)
    return (2 * prec * rec) / (prec + rec)


def answer_contains_gold(context_or_answer: str, gold: str) -> float:
    norm_gold = _normalize_answer(gold)
    if not norm_gold:
        return 0.0
    return 1.0 if norm_gold in _normalize_answer(context_or_answer) else 0.0


def bootstrap_ci(
    values: Sequence[float],
    *,
    iterations: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    vals = [float(v) for v in values]
    n = len(vals)
    if n == 0:
        return {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}
    mean = sum(vals) / n
    if n == 1:
        return {
            "mean": round(mean, 4),
            "ci_low": round(mean, 4),
            "ci_high": round(mean, 4),
            "n": 1,
        }
    rng = random.Random(seed)
    means: List[float] = []
    for _ in range(iterations):
        sample = [vals[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    low_idx = max(0, int((alpha / 2.0) * len(means)))
    high_idx = min(len(means) - 1, int((1.0 - alpha / 2.0) * len(means)))
    return {
        "mean": round(mean, 4),
        "ci_low": round(means[low_idx], 4),
        "ci_high": round(means[high_idx], 4),
        "n": n,
    }


def percentile(values: Sequence[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(v) for v in values)
    idx = (pct / 100.0) * (len(ordered) - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return round(ordered[lo], 2)
    frac = idx - lo
    return round(ordered[lo] * (1.0 - frac) + ordered[hi] * frac, 2)
