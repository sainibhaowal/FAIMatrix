"""FAIM-Native Antisymmetric Operator.

Deterministic merge/cancel for opposing vectors.

NO ML MODELS. NO RANDOMNESS.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
from uuid import UUID

# Flexible imports
try:
    from faim.Faim_Native.encoding.vector_schema import FAIMVector  # noqa: F401
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))


@dataclass(frozen=True)
class MergeResult:
    """Result of a merge operation.

    Attributes:
        winner_id: Node ID that survives.
        loser_id: Node ID that is merged/cancelled.
        score: Opposition/similarity score that triggered merge.
        meta: Additional metadata.
    """

    winner_id: UUID
    loser_id: UUID
    score: float
    meta: Dict[str, Any]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def opposition_score(a_vector: List[float], b_vector: List[float]) -> float:
    """Compute opposition score between two vectors.

    High similarity indicates potential redundancy.
    Opposition score = similarity for positive redundancy.

    Args:
        a_vector: First v_native.
        b_vector: Second v_native.

    Returns:
        Opposition score in [0, 1].
    """
    sim = cosine_similarity(a_vector, b_vector)
    # Convert to [0, 1] range - high similarity = high opposition/redundancy
    return max(0.0, sim)


def should_merge(score: float, threshold: float = 0.95) -> bool:
    """Determine if two vectors should be merged.

    Args:
        score: Opposition/similarity score.
        threshold: Merge threshold (default 0.95 = very similar).

    Returns:
        True if should merge.
    """
    return score >= threshold


def select_winner(
    a_id: UUID,
    b_id: UUID,
    a_hash: str,
    b_hash: str,
) -> Tuple[UUID, UUID]:
    """Deterministically select winner and loser.

    Winner is the one with lower vector_hash (lexicographic).
    This ensures deterministic behavior across runs.

    Args:
        a_id: First node ID.
        b_id: Second node ID.
        a_hash: First node's vector_hash.
        b_hash: Second node's vector_hash.

    Returns:
        (winner_id, loser_id) tuple.
    """
    if a_hash < b_hash:
        return (a_id, b_id)
    elif b_hash < a_hash:
        return (b_id, a_id)
    else:
        # Same hash (shouldn't happen), use node_id
        if str(a_id) < str(b_id):
            return (a_id, b_id)
        else:
            return (b_id, a_id)


def merge_vectors(
    a_id: UUID,
    b_id: UUID,
    a_hash: str,
    b_hash: str,
    score: float,
) -> MergeResult:
    """Perform deterministic merge of two vectors.

    Args:
        a_id: First node ID.
        b_id: Second node ID.
        a_hash: First node's vector_hash.
        b_hash: Second node's vector_hash.
        score: Opposition/similarity score.

    Returns:
        MergeResult with winner/loser.
    """
    winner_id, loser_id = select_winner(a_id, b_id, a_hash, b_hash)

    return MergeResult(
        winner_id=winner_id,
        loser_id=loser_id,
        score=score,
        meta={
            "winner_hash": a_hash if winner_id == a_id else b_hash,
            "loser_hash": b_hash if winner_id == a_id else a_hash,
            "merge_reason": "high_similarity",
        },
    )


def find_merge_candidates(
    target_vector: List[float],
    candidates: List[Tuple[UUID, str, List[float]]],
    threshold: float = 0.95,
    max_candidates: int = 5,
) -> List[Tuple[UUID, str, float]]:
    """Find merge candidates for a target vector.

    Args:
        target_vector: Target v_native.
        candidates: List of (node_id, vector_hash, v_native) tuples.
        threshold: Minimum similarity for merge.
        max_candidates: Maximum candidates to return.

    Returns:
        List of (node_id, vector_hash, score) for candidates above threshold.
    """
    scored = []

    for node_id, vector_hash, v_native in candidates:
        score = opposition_score(target_vector, v_native)
        if score >= threshold:
            scored.append((node_id, vector_hash, score))

    # Sort by score desc, then hash asc for determinism
    scored.sort(key=lambda x: (-x[2], x[1]))

    return scored[:max_candidates]


def check_merge_idempotence(
    merged_ids: set,
    a_id: UUID,
    b_id: UUID,
) -> bool:
    """Check if merge is idempotent (already done).

    Args:
        merged_ids: Set of already merged node IDs.
        a_id: First node ID.
        b_id: Second node ID.

    Returns:
        True if either node already merged (skip).
    """
    return a_id in merged_ids or b_id in merged_ids


# Exports
__all__ = [
    "MergeResult",
    "cosine_similarity",
    "opposition_score",
    "should_merge",
    "select_winner",
    "merge_vectors",
    "find_merge_candidates",
    "check_merge_idempotence",
]
