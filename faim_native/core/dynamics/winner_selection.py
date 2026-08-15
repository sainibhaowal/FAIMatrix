"""Semantic winner selection for merge operations (Phase 0032).

Legacy behavior picks a merge winner by lexicographic vector hash, which is
deterministic but semantically arbitrary — it destroys the better node about
half the time. This module scores candidates by information value:

    score = w1 * evidence_norm      (member count / evidence support)
          + w2 * usage_norm         (touch count, saturated)
          + w3 * recency_decay      (recent exposure counts more)
          + w4 * source_quality     (macro/long-term/provenance/anchor)
          + w5 * residual_norm      (novel information content)

Weights are normalized to sum to 1. Tie-breaks fall back to the legacy
lexicographic rule so the decision stays fully deterministic.

The selector is injected into evolve_once only when
FAIM_EVOLUTION_LEARNING_ENABLED is on; otherwise the legacy selector remains.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

# Weights for semantic value scoring (sum = 1.0).
W_EVIDENCE: float = 0.25
W_USAGE: float = 0.20
W_RECENCY: float = 0.15
W_SOURCE: float = 0.20
W_RESIDUAL: float = 0.20

# Recency half-life: usage/exposure within this many days counts double.
RECENCY_HALF_LIFE_DAYS: float = 14.0

RESIDUAL_SCALE: float = 1e9  # residuals are stored as int * 1e9

# Saturation bounds so one field can't dominate.
USAGE_SATURATION: int = 50
EVIDENCE_SATURATION: int = 10  # member count / supporting evidence
LEVEL_CAP: int = 8


@dataclass(frozen=True)
class WinnerDecision:
    """Result of a semantic winner selection."""

    winner_id: UUID
    loser_id: UUID
    winner_score: float
    loser_score: float
    meta: Dict[str, Any]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _residual_norm(residual: Any) -> float:
    """Residual stored as int*1e9 (or float 0..1); normalize to [0,1]."""
    if residual is None:
        return 0.0
    try:
        value = float(residual)
    except (TypeError, ValueError):
        return 0.0
    if value >= RESIDUAL_SCALE * 0.1:
        value = value / RESIDUAL_SCALE
    return _clamp01(value)


def _usage_norm(touch_count: Any) -> float:
    try:
        usage = max(0, int(touch_count or 0))
    except (TypeError, ValueError):
        return 0.0
    return _clamp01(usage / USAGE_SATURATION)


def _recency_decay(last_access: Any, now: datetime) -> float:
    if not last_access:
        return 0.5  # unknown recency is neutral
    if isinstance(last_access, str):
        try:
            last_access = datetime.fromisoformat(
                last_access.replace("Z", "+00:00")
            )
        except ValueError:
            return 0.5
    if last_access.tzinfo is None:
        last_access = last_access.replace(tzinfo=timezone.utc)
    delta = now - last_access
    if delta < timedelta(0):
        return 1.0
    days = delta.total_seconds() / 86400.0
    return _clamp01(0.5 ** (days / RECENCY_HALF_LIFE_DAYS))


def _evidence_norm(node: Any) -> float:
    """Evidence support: macro member count, or explicit evidence lists."""
    signature = getattr(node, "opp_signature", None)
    if isinstance(signature, dict):
        try:
            member_count = int(signature.get("member_count") or 0)
            if member_count > 0:
                return _clamp01(member_count / EVIDENCE_SATURATION)
        except (TypeError, ValueError):
            pass
    anchor = getattr(node, "anchor_json", None)
    if isinstance(anchor, dict):
        for key in ("evidence_node_ids", "member_ids", "evidence_ids"):
            evidence = anchor.get(key)
            if isinstance(evidence, (list, tuple)) and len(evidence) > 0:
                return _clamp01(len(evidence) / EVIDENCE_SATURATION)
    return 0.0


def _source_quality(node: Any) -> float:
    """Source/derivation quality: distilled kinds, long-term, provenance.

    Folded here (instead of a separate protection bonus) so the formula
    stays the verdict's exact five terms: evidence/usage/recency/source/
    residual.
    """
    quality = 0.0
    kind = getattr(node, "kind", None)
    if kind == "macro":
        quality += 0.6  # distilled from members = higher-grade source
    if getattr(node, "long_term", False):
        quality += 0.2
    if getattr(node, "raw_id", None):
        quality += 0.1  # traceable provenance
    if getattr(node, "block_id", None):
        quality += 0.05
    anchor = getattr(node, "anchor_json", None)
    if isinstance(anchor, dict):
        if any(
            isinstance(anchor.get(k), str) and anchor[k].strip()
            for k in ("text", "canonical", "summary")
        ):
            quality += 0.1
    try:
        level = max(0, int(getattr(node, "level", 0) or 0))
    except (TypeError, ValueError):
        level = 0
    quality += 0.05 * _clamp01(level / LEVEL_CAP)
    return _clamp01(quality)


def semantic_node_score(
    node: Any,
    *,
    now: Optional[datetime] = None,
) -> float:
    """Score a node by information value in [0, 1]."""
    now = now or datetime.now(timezone.utc)
    score = (
        W_EVIDENCE * _evidence_norm(node)
        + W_USAGE * _usage_norm(getattr(node, "touch_count", None))
        + W_RECENCY * _recency_decay(getattr(node, "last_access", None), now)
        + W_SOURCE * _source_quality(node)
        + W_RESIDUAL * _residual_norm(getattr(node, "residual", None))
    )
    return _clamp01(score)


def select_winner_semantic(
    node_a: Any,
    node_b: Any,
    *,
    now: Optional[datetime] = None,
) -> WinnerDecision:
    """Pick the semantically stronger node as merge winner.

    Falls back to legacy lexicographic hash ordering for exact ties so the
    decision stays fully deterministic.
    """
    score_a = semantic_node_score(node_a, now=now)
    score_b = semantic_node_score(node_b, now=now)
    id_a = UUID(str(node_a.node_id))
    id_b = UUID(str(node_b.node_id))

    if score_a > score_b:
        winner_id, loser_id = id_a, id_b
    elif score_b > score_a:
        winner_id, loser_id = id_b, id_a
    else:
        # Tie-break: legacy lexicographic vector_hash rule.
        hash_a = str(getattr(node_a, "vector_hash", "") or "")
        hash_b = str(getattr(node_b, "vector_hash", "") or "")
        if hash_a < hash_b:
            winner_id, loser_id = id_a, id_b
        elif hash_b < hash_a:
            winner_id, loser_id = id_b, id_a
        else:
            winner_id, loser_id = (
                (id_a, id_b) if str(id_a) < str(id_b) else (id_b, id_a)
            )

    winner_node = node_a if winner_id == id_a else node_b
    return WinnerDecision(
        winner_id=winner_id,
        loser_id=loser_id,
        winner_score=round(max(score_a, score_b), 6),
        loser_score=round(min(score_a, score_b), 6),
        meta={
            "selector": "semantic",
            "tie_break": "legacy_hash"
            if abs(score_a - score_b) < 1e-9
            else "score",
            "components_winner": {
                "evidence": round(W_EVIDENCE * _evidence_norm(winner_node), 6),
                "usage": round(
                    W_USAGE * _usage_norm(getattr(winner_node, "touch_count", None)),
                    6,
                ),
                "recency": round(
                    W_RECENCY
                    * _recency_decay(
                        getattr(winner_node, "last_access", None),
                        now or datetime.now(timezone.utc),
                    ),
                    6,
                ),
                "source": round(W_SOURCE * _source_quality(winner_node), 6),
                "residual": round(W_RESIDUAL * _residual_norm(getattr(winner_node, "residual", None)), 6),
            },
        },
    )


__all__ = [
    "WinnerDecision",
    "semantic_node_score",
    "select_winner_semantic",
]
