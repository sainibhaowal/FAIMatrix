"""Unit tests for inheritance invariants."""

from __future__ import annotations

import sys
from pathlib import Path

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.operators.inheritance import (  # noqa: E402
    compute_fractions,
    compute_inheritance_plan,
    compute_residual,
    cosine_similarity,
    verify_fraction_sum,
)


class TestInheritanceInvariants:
    """Unit tests for inheritance invariants."""

    def test_fractions_sum_to_one(self):
        """compute_fractions should sum to 1.0."""
        similarities = [0.9, 0.8, 0.5, 0.3]
        fractions = compute_fractions(similarities)

        assert verify_fraction_sum(fractions)
        assert abs(sum(fractions) - 1.0) < 1e-9

    def test_single_parent_fraction_is_one(self):
        """Single parent should get fraction 1.0."""
        fractions = compute_fractions([0.8])

        assert len(fractions) == 1
        assert fractions[0] == 1.0

    def test_empty_similarities_empty_fractions(self):
        """Empty similarities should return empty fractions."""
        fractions = compute_fractions([])
        assert fractions == []

    def test_zero_similarities_equal_distribution(self):
        """All-zero similarities should distribute equally."""
        fractions = compute_fractions([0.0, 0.0, 0.0])

        assert len(fractions) == 3
        for f in fractions:
            assert abs(f - 1.0 / 3) < 1e-9

    def test_cosine_identical_vectors(self):
        """Identical vectors should have cosine 1.0."""
        v = [0.5, 0.5, 0.5, 0.5]
        sim = cosine_similarity(v, v)
        assert abs(sim - 1.0) < 1e-9

    def test_cosine_orthogonal_vectors(self):
        """Orthogonal vectors should have cosine 0.0."""
        v1 = [1.0, 0.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0, 0.0]
        sim = cosine_similarity(v1, v2)
        assert abs(sim) < 1e-9

    def test_residual_no_parents_is_one(self):
        """Residual with no parents should be 1.0."""
        child = [0.5] * 256
        residual = compute_residual(child, [], [])
        assert residual == 1.0

    def test_residual_identical_parent_is_zero(self):
        """Residual with identical parent should be ~0."""
        child = [0.5] * 256
        residual = compute_residual(child, [child], [1.0])
        assert residual < 0.01

    def test_inheritance_plan_fractions_sum(self):
        """InheritancePlan fractions should sum to 1.0."""
        from uuid import uuid4

        child_vector = [0.5] * 256
        candidates = [
            (uuid4(), [0.4] * 256),
            (uuid4(), [0.6] * 256),
            (uuid4(), [0.3] * 256),
        ]

        plan = compute_inheritance_plan(child_vector, candidates, k=8)

        if plan.fractions:
            assert verify_fraction_sum(list(plan.fractions))

    def test_verify_fraction_sum_with_tolerance(self):
        """verify_fraction_sum should handle floating point."""
        # Slightly off due to floating point
        fractions = [0.3333333333, 0.3333333333, 0.3333333334]
        assert verify_fraction_sum(fractions, tolerance=1e-9)

    def test_fractions_preserve_order(self):
        """Fractions should preserve similarity order."""
        similarities = [0.9, 0.5, 0.1]
        fractions = compute_fractions(similarities)

        # Higher similarity = higher fraction
        assert fractions[0] > fractions[1] > fractions[2]
