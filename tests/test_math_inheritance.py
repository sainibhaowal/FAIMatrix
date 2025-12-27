# ========================================================================== #
#  FAIM Fractal Math Tests (Golden Edition)                                  #
# ========================================================================== #
#  Module: tests.test_math_inheritance                                       #
#                                                                           #
#  Purpose                                                                  #
#  -------                                                                  #
#  Validate the core mathematical invariants of FAIM's fractal inheritance  #
#  layer and golden-ratio scaling:                                          #
#    - s = GOLDEN_SCALE = 1 / φ                                             #
#    - Inheritance fractions are normalised (Σ f_p = 1, f_p ≥ 0)           #
#    - Root-node construction reduces to pure novelty                       #
#    - Build-inheritance paths stay Banach-bounded                          #
#    - Softmax-based inheritance_construction has sane fractions and norms  #
# ========================================================================== #

from __future__ import annotations

import numpy as np
from faim.core.math import (
    DEFAULT_NORM_BOUND,
    GOLDEN_SCALE,
    PHI,
    build_inheritance_vec,
    inheritance_construction,
    l2_norm,
    normalize_fractions,
    simulate_inheritance_chain,
)

# ========================================================================== #
# Golden ratio invariants                                                    #
# ========================================================================== #


def test_golden_scale_is_inverse_phi():
    """Check GOLDEN_SCALE * PHI ≈ 1.0 (s = 1/φ)."""
    assert np.isclose(GOLDEN_SCALE * PHI, 1.0, atol=1e-9)


# ========================================================================== #
# Fraction normalisation                                                     #
# ========================================================================== #


def test_normalize_fractions_sums_to_one():
    """normalize_fractions should produce non-negative fractions summing to 1."""
    fracs = normalize_fractions([0.2, 0.3, 0.0, 0.5])
    assert fracs.shape == (4,)
    total = float(fracs.sum())
    assert np.isclose(total, 1.0, atol=1e-8)
    assert np.all(fracs >= 0.0)


def test_normalize_fractions_uniform_on_all_zero():
    """All-zero (or negative) inputs should yield a uniform distribution."""
    fracs = normalize_fractions([0.0, -1e-6, 0.0])
    expected = np.array([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0], dtype=float)
    assert np.allclose(fracs, expected)


# ========================================================================== #
# Explicit inheritance construction                                          #
# ========================================================================== #


def test_build_inheritance_vec_root_node_is_novelty():
    """
    Root nodes (no parents) should reduce to pure novelty:

        v_i = Δ_i
    """
    delta = np.array([1.0, -2.0, 3.5], dtype=np.float64)
    res = build_inheritance_vec(parents=[], fractions=[], novelty_vec=delta)

    # v_new is exactly the novelty; inherited is all zeros; no fractions.
    assert np.allclose(res.v_new, delta)
    assert np.allclose(res.inherited, np.zeros_like(delta))
    assert len(res.fractions) == 0


def test_build_inheritance_vec_invariants():
    """
    With parents present, build_inheritance_vec must:

    - Normalise fractions (Σ f_p = 1)
    - Produce a vector of correct dimension
    - Keep norms finite and non-exploding
    """
    p1 = np.array([1.0, 0.0], dtype=np.float64)
    p2 = np.array([0.0, 1.0], dtype=np.float64)
    delta = np.array([0.1, -0.2], dtype=np.float64)

    res = build_inheritance_vec(
        parents=[p1, p2],
        fractions=[0.2, 0.8],
        novelty_vec=delta,
        production=True,
        norm_bound=DEFAULT_NORM_BOUND,
    )

    # Fractions must sum to 1.
    assert np.isclose(sum(res.fractions), 1.0, atol=1e-8)
    # Final vector dimensionality matches parents/novelty.
    assert res.v_new.shape == (2,)
    # Norm is finite and not exploding.
    assert np.isfinite(np.linalg.norm(res.v_new))


def test_long_inheritance_chain_is_bounded():
    """
    Long inheritance chains with GOLDEN_SCALE must remain Banach-bounded.

    We use simulate_inheritance_chain to repeatedly apply:

        v_{k+1} = s * v_k + Δ_{k+1}

    and ensure norms stay within DEFAULT_NORM_BOUND.
    """
    norms = simulate_inheritance_chain(depth=256, dim=32)
    max_norm = max(norms)
    # With GOLDEN_SCALE and small deltas, this should stay nicely bounded.
    assert max_norm < DEFAULT_NORM_BOUND


# ========================================================================== #
# Softmax-based inheritance_construction                                     #
# ========================================================================== #


def test_inheritance_fractions_sum_to_one_softmax_variant():
    """
    Softmax-based inheritance_construction must produce fractions that sum to 1.
    """
    parents = [np.ones(4, dtype=np.float32), 2 * np.ones(4, dtype=np.float32)]
    embed = 3 * np.ones(4, dtype=np.float32)

    res = inheritance_construction(parents, embed)
    total = sum(res.fractions)
    assert abs(total - 1.0) < 1e-6


def test_inheritance_norm_bounded_softmax_variant():
    """
    Softmax-based inheritance_construction should produce finite, non-exploding
    norms for reasonable parent / embed configurations.
    """
    parents = [np.ones(8, dtype=np.float32), -np.ones(8, dtype=np.float32)]
    embed = np.ones(8, dtype=np.float32)

    res = inheritance_construction(parents, embed)
    norm = l2_norm(res.v_new)

    # Just check it's finite and in a sane ball for this synthetic test.
    assert 0.0 < norm < 10.0
