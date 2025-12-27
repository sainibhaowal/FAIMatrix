# ========================================================================== #
#  FAIM Antisymmetry Tests (Golden Edition)                                  #
# ========================================================================== #
#  Module: tests.test_antisym_merge                                          #
#                                                                           #
#  Purpose                                                                  #
#  -------                                                                  #
#  Validate the mathematical invariants of FAIM's antisymmetric layer:      #
#    - Ω(a, b) is antisymmetric                                              #
#    - Wedge merge is idempotent and redundancy-reducing                    #
#    - Redundancy statistics react as expected to merges                    #
#    - opposition_update cancels duplicate energy and is idempotent         #
#                                                                           #
#  Invariants Covered                                                       #
#  -------------------                                                      #
#  1) opposition_vector(a, b) = -opposition_vector(b, a)                    #
#  2) practical_wedge_merge(wedge(v, u), u) ≈ wedge(v, u)                  #
#  3) cos(wedge(v, u), u) ≤ cos(v, u)                                      #
#  4) redundancy_stats(mean_cosine) decreases after wedge merges           #
#  5) opposition_update(v, v, α=1) drives v → ~0 (energy cancellation)     #
#  6) opposition_update is idempotent when applied repeatedly with same u  #
# ========================================================================== #

from __future__ import annotations

import numpy as np
from faim.core.antisym import (
    cosine_similarity,
    opposition_update,
    opposition_vector,
    practical_wedge_merge,
    redundancy_stats,
)
from faim.core.math import l2_norm

# ========================================================================== #
# Antisymmetric opposition operator                                          #
# ========================================================================== #


def test_opposition_is_antisymmetric():
    """Ω(a, b) must be the negative of Ω(b, a)."""
    v_i = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    v_j = np.array([-1.0, 0.5, 4.0], dtype=np.float32)

    omega_ij = opposition_vector(v_i, v_j)
    omega_ji = opposition_vector(v_j, v_i)

    assert np.allclose(omega_ij, -omega_ji, atol=1e-7)


def test_opposition_vector_is_antisymmetric_again_different_values():
    """Second antisymmetry check with different values (extra safety)."""
    a = np.array([0.3, -1.2, 0.7], dtype=np.float32)
    b = np.array([2.5, 0.0, -0.4], dtype=np.float32)

    omega_ab = opposition_vector(a, b)
    omega_ba = opposition_vector(b, a)

    assert np.allclose(omega_ab, -omega_ba, atol=1e-7)


# ========================================================================== #
# Wedge operator invariants                                                  #
# ========================================================================== #


def test_wedge_is_idempotent_for_same_partner():
    """
    Wedge merge should be idempotent when using the same partner vector.

    Once we have removed the component along v_new, applying wedge again
    with the same v_new should not change the result (beyond numerical noise).
    """
    v_rep = np.array([1.0, 2.0, -1.0], dtype=np.float64)
    v_new = np.array([1.0, 2.0, -1.0], dtype=np.float64)

    once = practical_wedge_merge(v_rep, v_new)
    twice = practical_wedge_merge(once, v_new)

    assert np.allclose(once, twice, atol=1e-7)


def test_wedge_reduces_similarity_to_partner():
    """
    Wedge merge should reduce similarity to the merge partner.

    After removing the redundant direction, cosine similarity between
    the merged representative and the partner must not increase.
    """
    rng = np.random.default_rng(42)
    base = rng.normal(size=(64,))
    noise = rng.normal(scale=0.01, size=(64,))
    v_rep = base + noise
    v_new = base - noise

    before = cosine_similarity(v_rep, v_new)
    merged = practical_wedge_merge(v_rep, v_new)
    after = cosine_similarity(merged, v_new)

    # After removing the redundant direction, similarity should go down.
    assert after <= before + 1e-6


# ========================================================================== #
# Redundancy statistics                                                      #
# ========================================================================== #


def test_redundancy_stats_decrease_after_merges():
    """
    RedundancyStats.mean_cosine should decrease after applying wedge merges.

    We construct several near-duplicate vectors around a base, compute
    redundancy, then wedge them against the base and ensure redundancy
    drops (or stays within numerical slack).
    """
    rng = np.random.default_rng(0)
    base = rng.normal(size=(32,))

    originals = [base + 0.01 * rng.normal(size=(32,)) for _ in range(5)]
    stats_before = redundancy_stats(originals)

    merged = [practical_wedge_merge(v, base) for v in originals]
    stats_after = redundancy_stats(merged)

    # Mean redundancy must go down (within tiny numerical slack).
    assert stats_after.mean_cosine <= stats_before.mean_cosine + 1e-6


# ========================================================================== #
# opposition_update: duplicate cancellation + idempotence                    #
# ========================================================================== #


def test_antisym_merge_reduces_duplicate_energy():
    """
    opposition_update should strongly reduce energy for perfect duplicates.

    When base_vec == incoming_vec and alpha=1.0, the updated vector should
    have very small norm (effectively cancelling the duplicate direction),
    matching the FAIM antisymmetry intuition.
    """
    v_base = np.ones(4, dtype=np.float32)
    v_incoming = np.ones(4, dtype=np.float32)

    before = l2_norm(v_base)
    updated = opposition_update(v_base, v_incoming, alpha=1.0)
    after = l2_norm(updated)

    # identical vectors with alpha=1 → near-zero result
    assert after < before
    assert after < 1e-3


def test_opposition_update_is_idempotent_for_same_incoming():
    """
    opposition_update must be idempotent when applied repeatedly with
    the same incoming vector and alpha=1.0.
    """
    base = np.array([1.0, 2.0, -1.0], dtype=np.float32)
    incoming = np.array([1.0, 2.0, -1.0], dtype=np.float32)

    once = opposition_update(base, incoming, alpha=1.0)
    twice = opposition_update(once, incoming, alpha=1.0)

    # Once we’ve removed the component along incoming, repeating should
    # not change the vector (up to numerical noise).
    assert np.allclose(once, twice, atol=1e-6)
