"""FAIM-Native Inheritance Operator.

Deterministic parent selection and fraction computation.

NO ML MODELS. NO RANDOMNESS.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
from uuid import UUID

# Flexible imports
try:
    from faim.Faim_Native.encoding.vector_schema import (  # noqa: F401
        VECTOR_DIMENSION,
        FAIMVector,
    )
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))


@dataclass(frozen=True)
class InheritancePlan:
    """Result of inheritance computation.

    Attributes:
        parents: List of parent node IDs.
        fractions: Weights for each parent (Σ=1).
        residual: Novelty proxy (0-1).
        similarities: Raw similarity scores.
    """

    parents: Tuple[UUID, ...]
    fractions: Tuple[float, ...]
    residual: float
    similarities: Tuple[float, ...]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector.
        b: Second vector.

    Returns:
        Cosine similarity in [-1, 1].
    """
    if len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def select_parents(
    child_vector: List[float],
    candidates: List[Tuple[UUID, List[float]]],
    k: int = 8,
) -> List[Tuple[UUID, float]]:
    """Select top-k parents based on cosine similarity.

    Deterministic tie-breaking: sort by (similarity desc, node_id asc).

    Args:
        child_vector: Child's v_native.
        candidates: List of (node_id, v_native) pairs.
        k: Maximum number of parents to select.

    Returns:
        List of (parent_id, similarity) tuples.
    """
    if not candidates:
        return []

    # Compute similarities
    scored = []
    for node_id, v_native in candidates:
        sim = cosine_similarity(child_vector, v_native)
        scored.append((node_id, sim))

    # Sort by similarity desc, then node_id asc for ties
    scored.sort(key=lambda x: (-x[1], str(x[0])))

    # Take top k with positive similarity
    result = [(node_id, sim) for node_id, sim in scored[:k] if sim > 0]

    return result


def compute_fractions(similarities: List[float]) -> List[float]:
    """Compute normalized fractions from similarities.

    Guarantees Σfractions = 1.0 exactly using stable rounding.

    Args:
        similarities: List of similarity scores.

    Returns:
        List of fractions summing to 1.0.
    """
    if not similarities:
        return []

    if len(similarities) == 1:
        return [1.0]

    total = sum(similarities)
    if total == 0:
        # Equal distribution if all zeros
        n = len(similarities)
        return [1.0 / n] * n

    # Initial fractions
    fractions = [s / total for s in similarities]

    # Stable rounding to ensure Σ=1 exactly
    # Round to 10 decimal places
    rounded = [round(f, 10) for f in fractions]

    # Adjust last element to ensure sum is exactly 1
    diff = 1.0 - sum(rounded[:-1])
    rounded[-1] = round(diff, 10)

    return rounded


def compute_residual(
    child_vector: List[float],
    parent_vectors: List[List[float]],
    fractions: List[float],
) -> float:
    """Compute residual (novelty proxy) for child.

    residual = 1 - cosine(child, inherited_mix)

    The inherited_mix is the weighted sum of parent vectors.

    Args:
        child_vector: Child's v_native.
        parent_vectors: Parent v_native vectors.
        fractions: Weights for each parent.

    Returns:
        Residual in [0, 1].
    """
    if not parent_vectors or not fractions:
        return 1.0  # No parents = fully novel

    if len(parent_vectors) != len(fractions):
        return 1.0

    # Compute inherited mix
    dim = len(child_vector)
    mix = [0.0] * dim

    for pv, f in zip(parent_vectors, fractions, strict=False):
        if len(pv) == dim:
            for i in range(dim):
                mix[i] += pv[i] * f

    # Compute similarity to mix
    sim = cosine_similarity(child_vector, mix)

    # Residual = 1 - similarity, clamped to [0, 1]
    residual = 1.0 - max(0.0, min(1.0, sim))

    return round(residual, 10)


def compute_inheritance_plan(
    child_vector: List[float],
    candidates: List[Tuple[UUID, List[float]]],
    k: int = 8,
) -> InheritancePlan:
    """Compute full inheritance plan for a child.

    Args:
        child_vector: Child's v_native.
        candidates: List of (node_id, v_native) pairs.
        k: Maximum number of parents.

    Returns:
        InheritancePlan with parents, fractions, residual.
    """
    if not candidates:
        return InheritancePlan(
            parents=(),
            fractions=(),
            residual=1.0,
            similarities=(),
        )

    # Select parents
    parent_sims = select_parents(child_vector, candidates, k)

    if not parent_sims:
        return InheritancePlan(
            parents=(),
            fractions=(),
            residual=1.0,
            similarities=(),
        )

    parent_ids = [p[0] for p in parent_sims]
    similarities = [p[1] for p in parent_sims]

    # Compute fractions
    fractions = compute_fractions(similarities)

    # Get parent vectors for residual computation
    parent_vectors = []
    for parent_id in parent_ids:
        for node_id, v_native in candidates:
            if node_id == parent_id:
                parent_vectors.append(v_native)
                break

    # Compute residual
    residual = compute_residual(child_vector, parent_vectors, fractions)

    return InheritancePlan(
        parents=tuple(parent_ids),
        fractions=tuple(fractions),
        residual=residual,
        similarities=tuple(similarities),
    )


def verify_fraction_sum(fractions: List[float], tolerance: float = 1e-9) -> bool:
    """Verify that fractions sum to 1.0 within tolerance."""
    if not fractions:
        return True
    return abs(sum(fractions) - 1.0) <= tolerance


# Exports
__all__ = [
    "InheritancePlan",
    "cosine_similarity",
    "select_parents",
    "compute_fractions",
    "compute_residual",
    "compute_inheritance_plan",
    "verify_fraction_sum",
]
