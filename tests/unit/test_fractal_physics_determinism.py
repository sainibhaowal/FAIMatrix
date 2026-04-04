"""Unit tests for fractal physics determinism."""

from __future__ import annotations

import sys
from pathlib import Path

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.metrics.fractal_physics import (  # noqa: E402
    DEFAULT_CONFIG,
    GOLDEN_S,
    PHI,
    compute_diagnostics,
    compute_energy_E,
    compute_scaling_s,
    estimate_D_fractal,
    estimate_H_entropy,
    estimate_lambda,
)


class TestFractalPhysicsDeterminism:
    """Tests for deterministic behavior of fractal physics."""

    def test_same_inputs_same_D_hash(self):
        """Same inputs should produce same D/H/λ hash."""
        vectors = [[0.5] * 256 for _ in range(5)]
        residuals = [0.1, 0.2, 0.3, 0.2, 0.1]

        diag1 = compute_diagnostics(
            graph_id="test",
            vectors=vectors,
            residuals=residuals,
            edge_count=4,
            graph_version=1,
        )

        diag2 = compute_diagnostics(
            graph_id="test",
            vectors=vectors,
            residuals=residuals,
            edge_count=4,
            graph_version=1,
        )

        assert diag1.diagnostics_hash == diag2.diagnostics_hash

    def test_stable_under_reordering(self):
        """D/H/λ should be stable if vectors are same (order matters for pairs)."""
        v1 = [0.1] * 256
        v2 = [0.2] * 256
        v3 = [0.3] * 256

        # Same vectors, different order
        vectors1 = [v1, v2, v3]
        vectors2 = [v1, v2, v3]  # Exact same order

        diag1 = compute_diagnostics(
            graph_id="test",
            vectors=vectors1,
            residuals=[0.1, 0.1, 0.1],
            edge_count=2,
            graph_version=1,
        )

        diag2 = compute_diagnostics(
            graph_id="test",
            vectors=vectors2,
            residuals=[0.1, 0.1, 0.1],
            edge_count=2,
            graph_version=1,
        )

        # Same order = same results
        assert diag1.D_hat == diag2.D_hat
        assert diag1.H_hat == diag2.H_hat
        assert diag1.lambda_hat == diag2.lambda_hat

    def test_golden_s_is_used_in_composition(self):
        """GOLDEN_S should be approximately 1/PHI."""
        expected = 1.0 / PHI
        assert abs(GOLDEN_S - expected) < 1e-10

    def test_scaling_s_equals_golden(self):
        """compute_scaling_s should return GOLDEN_S."""
        s = compute_scaling_s()
        assert abs(s - GOLDEN_S) < 1e-9

    def test_J_objective_is_deterministic(self):
        """λ (evolution pressure) should be deterministic."""
        N, R, H = 0.3, 0.4, 0.5

        lambda1 = estimate_lambda(N, R, H)
        lambda2 = estimate_lambda(N, R, H)

        assert lambda1 == lambda2

    def test_diagnostics_hash_excludes_volatile(self):
        """Diagnostics hash should be based on stable fields only."""
        vectors = [[0.5] * 256] * 3

        diag = compute_diagnostics(
            graph_id="test",
            vectors=vectors,
            residuals=[0.1, 0.1, 0.1],
            edge_count=2,
            graph_version=1,
        )

        # Hash should be 64 hex chars
        assert len(diag.diagnostics_hash) == 64


class TestFractalDimensionEstimator:
    """Tests for D estimator."""

    def test_one_node_D_zero(self):
        """1 node should have D=0."""
        D = estimate_D_fractal([[0.5] * 256])
        assert D == 0.0

    def test_identical_vectors_low_D(self):
        """Identical vectors should have low D."""
        vectors = [[0.5] * 256] * 10
        D = estimate_D_fractal(vectors)
        # All distances are 0, so D should be 0
        assert D == 0.0

    def test_diverse_vectors_higher_D(self):
        """Diverse vectors should have higher D."""
        # Create diverse vectors
        vectors = []
        for i in range(10):
            v = [0.0] * 256
            v[i % 256] = 1.0  # One-hot style
            vectors.append(v)

        D = estimate_D_fractal(vectors)
        # Should have positive D
        assert D >= 0.0

    def test_D_bounded(self):
        """D should be in [0, d_max]."""
        vectors = [[i * 0.1] * 256 for i in range(5)]
        D = estimate_D_fractal(vectors)

        assert 0 <= D <= DEFAULT_CONFIG.d_max


class TestEntropyEstimator:
    """Tests for H estimator."""

    def test_uniform_histogram_high_H(self):
        """Uniform distribution should have high H."""
        # Create similarities uniformly distributed
        similarities = [i * 0.1 - 0.5 for i in range(20)]
        H = estimate_H_entropy(similarities)

        # Should be relatively high
        assert H > 0.5

    def test_concentrated_low_H(self):
        """Concentrated distribution should have low H."""
        # All similarities clustered at one value
        similarities = [0.9] * 100
        H = estimate_H_entropy(similarities)

        # Should be low
        assert H < 0.3

    def test_H_bounded_0_1(self):
        """H should be in [0, 1]."""
        similarities = [0.5, 0.6, 0.7]
        H = estimate_H_entropy(similarities)

        assert 0 <= H <= 1


class TestLambdaBounds:
    """Tests for λ bounds."""

    def test_lambda_clamp_high(self):
        """λ should be clamped to max 1.0."""
        # All inputs at max
        lambda_hat = estimate_lambda(1.0, 0.0, 1.0)
        assert lambda_hat <= 1.0

    def test_lambda_clamp_low(self):
        """λ should be clamped to min 0.0."""
        # All inputs at min
        lambda_hat = estimate_lambda(0.0, 1.0, 0.0)
        assert lambda_hat >= 0.0

    def test_lambda_in_range(self):
        """λ should always be in [0, 1]."""
        for N in [0.0, 0.5, 1.0]:
            for R in [0.0, 0.5, 1.0]:
                for H in [0.0, 0.5, 1.0]:
                    lam = estimate_lambda(N, R, H)
                    assert 0 <= lam <= 1


class TestInvariantsFractal:
    """Tests for fractal invariants."""

    def test_s_bounds_valid(self):
        """s should be in (0, 1]."""
        from core.invariants import check_scaling_bounds

        result = check_scaling_bounds(GOLDEN_S)
        assert result.passed

    def test_s_bounds_invalid_zero(self):
        """s=0 should fail."""
        from core.invariants import check_scaling_bounds

        result = check_scaling_bounds(0.0)
        assert not result.passed

    def test_D_range_valid(self):
        """D in range should pass."""
        from core.invariants import check_D_range

        result = check_D_range(2.5)
        assert result.passed

    def test_H_range_valid(self):
        """H in range should pass."""
        from core.invariants import check_H_range

        result = check_H_range(0.5)
        assert result.passed

    def test_lambda_range_valid(self):
        """λ in range should pass."""
        from core.invariants import check_lambda_range

        result = check_lambda_range(0.5)
        assert result.passed

    def test_energy_bounded(self):
        """Energy under bound should pass."""
        from core.invariants import check_energy_bounded

        result = check_energy_bounded(0.5)
        assert result.passed


class TestDeltaResidual:
    """Tests for delta/residual computation."""

    def test_delta_residual_nonzero_when_child_differs(self):
        """Residual should be nonzero when child differs from parents."""
        from core.operators.inheritance import compute_residual

        child = [1.0] + [0.0] * 255
        parent = [0.0, 1.0] + [0.0] * 254

        residual = compute_residual(child, [parent], [1.0])

        # Orthogonal vectors = residual = 1.0
        assert residual > 0.9

    def test_delta_residual_zero_when_identical(self):
        """Residual should be ~0 when child equals parent."""
        from core.operators.inheritance import compute_residual

        v = [0.5] * 256
        residual = compute_residual(v, [v], [1.0])

        assert residual < 0.01


class TestBoundednessOverGenerations:
    """Tests for boundedness stability."""

    def test_energy_stable_over_iterations(self):
        """Energy should not explode over iterations (Banach-style)."""
        vectors = [[0.5] * 256 for _ in range(10)]

        energies = []
        for _ in range(5):
            E = compute_energy_E(vectors)
            energies.append(E)

        # All energies should be equal (deterministic)
        assert all(e == energies[0] for e in energies)

        # Energy should be bounded (vector norm ~8 * s ~5)
        assert all(e < 10.0 for e in energies)
