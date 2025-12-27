"""FAIM core math utilities.

Golden Edition: deterministic, typed, side-effect free.

Implements the mathematical primitives for:
- fractal inheritance construction
- similarity scoring
- basic boundedness diagnostics
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np

# Public vector alias used by other FAIM modules.
Vector = np.ndarray

# ========================================================================== #
# Fractal invariants and numeric constants                                   #
# ========================================================================== #

#: Golden ratio φ and its inverse s = 1 / φ (default fractal scale).
PHI: float = float((1.0 + np.sqrt(5.0)) / 2.0)
GOLDEN_SCALE: float = 1.0 / PHI  # ≈ 0.618

#: Default allowed norm bound for Banach-style sanity checks.
DEFAULT_NORM_BOUND: float = 10.0

#: Default floating-point tolerance for invariants.
DEFAULT_EPS: float = 1e-6


# ========================================================================== #
# Inheritance result container                                               #
# ========================================================================== #


@dataclass(frozen=True)
class InheritanceResult:
    """Result of an inheritance construction step.

    Invariants
    ----------
    - fractions:
        Non-negative inheritance fractions f_p with sum ≈ 1.0
        (or empty when there are no parents).
    - inherited:
        Inherited component s * Σ f_p v_p.
    - novelty:
        Novelty component Δ such that v_new = inherited + novelty.
    - v_new:
        Final node vector for the new node.

    Notes
    -----
    This structure is used both by the softmax-based construction
    (``inheritance_construction``) and by more explicit P1-style math
    helpers. Existing engine/tests only rely on ``fractions`` and
    ``v_new``, but the other fields are included for diagnostics and
    future invariants.
    """

    fractions: Tuple[float, ...]
    inherited: Vector
    novelty: Vector
    v_new: Vector

    # Backwards-compatible aliases for potential future refactors.
    @property  # pragma: no cover - simple alias
    def vec(self) -> Vector:
        return self.v_new

    @property  # pragma: no cover - simple alias
    def inherited_vec(self) -> Vector:
        return self.inherited


# ========================================================================== #
# Core numeric helpers                                                       #
# ========================================================================== #


def _as_vec1d(vec: Vector, name: str) -> np.ndarray:
    """Internal helper: ensure a 1D float64 vector."""
    arr = np.asarray(vec, dtype=np.float64)
    if arr.ndim > 1:
        arr = arr.reshape(-1)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be 1D after flattening, got shape {arr.shape}")
    return arr


def l2_norm(vec: Vector) -> float:
    """Compute L2 norm in a numerically safe way."""
    return float(np.linalg.norm(_as_vec1d(vec, "vec")))


def cosine_similarity(a: Vector, b: Vector) -> float:
    """Cosine similarity between two vectors.

    Returns 0.0 if either vector is (near-)zero to avoid NaNs.
    """
    a64 = _as_vec1d(a, "a")
    b64 = _as_vec1d(b, "b")
    na = float(np.linalg.norm(a64))
    nb = float(np.linalg.norm(b64))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a64, b64) / (na * nb))


def softmax(xs: Sequence[float]) -> Tuple[float, ...]:
    """Stable softmax over a sequence of scalars.

    Returns a tuple of probabilities that sum to 1.0 (within float noise).
    """
    if not xs:
        return ()
    xs_arr = np.asarray(xs, dtype=np.float64)
    m = float(xs_arr.max())
    exps = np.exp(xs_arr - m)
    denom = float(exps.sum())
    if denom == 0.0:
        # All -inf – fall back to uniform distribution.
        n = len(xs_arr)
        return tuple(1.0 / n for _ in range(n))
    probs = exps / denom
    return tuple(float(p) for p in probs)


# ========================================================================== #
# Fractal inheritance primitives                                             #
# ========================================================================== #


def normalize_fractions(
    fractions: Sequence[float],
    *,
    eps: float = DEFAULT_EPS,
) -> np.ndarray:
    """
    Normalise inheritance fractions so that ∑_p f_p = 1 (within tolerance).

    Behaviour
    ---------
    - Negative values are clipped to 0.
    - If total mass ≤ eps, fall back to uniform distribution.
    - If there are no parents, returns an empty array.
    """
    arr = np.asarray(fractions, dtype=np.float64)
    if arr.size == 0:
        return arr

    # Clip negatives, avoid tiny negative noise.
    arr = np.maximum(arr, 0.0)
    total = float(arr.sum())

    if total < eps:
        # All zeros (or effectively zeros) → uniform.
        arr.fill(1.0 / arr.size)
        return arr

    arr /= total
    return arr


def build_inheritance_vec(
    parents: Sequence[Vector],
    fractions: Sequence[float],
    novelty_vec: Vector,
    *,
    production: bool = True,
    scale: float | None = None,
    norm_bound: float = DEFAULT_NORM_BOUND,
    eps: float = DEFAULT_EPS,
) -> InheritanceResult:
    """
    Construct a node vector via explicit fractal inheritance:

        v_i = s * Σ_p f_p v_p + Δ_i

    where
    ------
    - s is GOLDEN_SCALE (1/φ) in production mode, unless explicitly
      overridden via `scale`.
    - fractions are normalised so that ∑ f_p = 1 if parents are present.
    - For root nodes (no parents), v_i = Δ_i.

    Parameters
    ----------
    parents:
        Sequence of parent vectors v_p.
    fractions:
        Raw (possibly unnormalised) inheritance fractions f_p.
    novelty_vec:
        Novelty term Δ_i (same dimension as parent vectors).
    production:
        If True, force scale = GOLDEN_SCALE and enforce norm bounds.
    scale:
        Optional override for the scale factor; ignored if production=True.
    norm_bound:
        Soft bound for ‖v_i‖; used in tests and production sanity checks.
    eps:
        Tolerance for invariant checks.

    Returns
    -------
    InheritanceResult

    Raises
    ------
    ValueError
        On shape mismatches or if norms explode far beyond `norm_bound`
        in production mode.
    """
    novelty = _as_vec1d(novelty_vec, "novelty_vec")

    if not parents:
        # Root: v_i = Δ_i, no inheritance.
        zeros = np.zeros_like(novelty)
        return InheritanceResult(
            fractions=tuple(),
            inherited=zeros,
            novelty=novelty.copy(),
            v_new=novelty.copy(),
        )

    parent_arr = np.stack([_as_vec1d(p, "parent") for p in parents], axis=0)
    if parent_arr.shape[1] != novelty.shape[0]:
        raise ValueError(
            f"Dimension mismatch: parents have dim={parent_arr.shape[1]} "
            f"but novelty_vec has dim={novelty.shape[0]}"
        )

    fracs_arr = normalize_fractions(fractions, eps=eps)
    if fracs_arr.shape[0] != parent_arr.shape[0]:
        raise ValueError(
            f"Fractions length {fracs_arr.shape[0]} does not match "
            f"number of parents {parent_arr.shape[0]}"
        )

    total = float(fracs_arr.sum())
    if abs(total - 1.0) > 10 * eps:
        # Should not happen given normalize_fractions, but guard anyway.
        raise ValueError(f"Inheritance fractions do not sum to 1 (got {total})")

    # Choose scale factor.
    if production or scale is None:
        s_val = GOLDEN_SCALE
    else:
        s_val = float(scale)

    # Σ f_p v_p
    mixed = (fracs_arr[:, None] * parent_arr).sum(axis=0)
    inherited = s_val * mixed
    v_new = inherited + novelty

    if production:
        # Banach-style sanity: norms must stay within a reasonable ball.
        norm = float(np.linalg.norm(v_new))
        if not np.isfinite(norm) or norm > norm_bound * 10.0:
            # 10× slack to keep tests robust; can tighten later.
            raise ValueError(
                f"Vector norm exploded (‖v_i‖ = {norm:.6f}) with norm_bound={norm_bound}"
            )

    return InheritanceResult(
        fractions=tuple(float(x) for x in fracs_arr),
        inherited=inherited.astype(np.float64),
        novelty=novelty.astype(np.float64),
        v_new=v_new.astype(np.float64),
    )


def inheritance_construction(
    parents: Sequence[Vector],
    embed: Vector,
    *,
    scale: float = GOLDEN_SCALE,
    alpha_sim: float = 1.0,
) -> InheritanceResult:
    """Construct a new node vector from parents + novelty (softmax variant).

    Parameters
    ----------
    parents:
        Parent vectors v_p (may be empty for root nodes).
    embed:
        Raw embedding e for the new payload. This acts as the final
        vector v_new in this construction.
    scale:
        Fractal scale factor s (0 < s < 1). Default ≈ 0.618 (1/φ).
    alpha_sim:
        Scale factor for similarities before softmax.

    Notes
    -----
    - If no parents are provided, this treats the node as a root:
      fractions = (), inherited = 0, novelty = embed, v_new = embed.
    - Deterministic for the same inputs.
    - Maintains the invariant: v_new = inherited + novelty, where
      inherited = scale * Σ f_p v_p and novelty = v_new - inherited.
    """
    v_new = _as_vec1d(embed, "embed").astype(np.float64)

    if not parents:
        zeros = np.zeros_like(v_new)
        return InheritanceResult(
            fractions=tuple(),
            inherited=zeros,
            novelty=v_new.copy(),
            v_new=v_new.copy(),
        )

    sims: List[float] = [alpha_sim * cosine_similarity(p, v_new) for p in parents]
    fracs = softmax(sims)

    parents_arr = np.stack([_as_vec1d(p, "parent") for p in parents], axis=0)
    weights = np.asarray(fracs, dtype=np.float64).reshape(-1, 1)

    # Inherited component: s * Σ f_p v_p
    mixed = (parents_arr * weights).sum(axis=0)
    inherited = float(scale) * mixed

    novelty = v_new - inherited

    return InheritanceResult(
        fractions=fracs,
        inherited=inherited.astype(np.float64),
        novelty=novelty.astype(np.float64),
        v_new=v_new.astype(np.float64),
    )


# ========================================================================== #
# Test / diagnostic helpers                                                  #
# ========================================================================== #


def simulate_inheritance_chain(
    depth: int,
    dim: int = 64,
    *,
    scale: float = GOLDEN_SCALE,
    delta_scale: float = 0.1,
) -> list[float]:
    """
    Simulate a simple linear inheritance chain:

        v_0 = Δ_0
        v_{k+1} = scale * v_k + Δ_{k+1}

    Returns
    -------
    list[float]
        The list of norms ‖v_k‖, k = 0..depth, so tests can assert that
        norms stay bounded (Banach-style sanity).
    """
    rng = np.random.default_rng(0)

    v = rng.normal(scale=delta_scale, size=(dim,)).astype(np.float64)
    norms: list[float] = [l2_norm(v)]

    for _ in range(depth):
        delta = rng.normal(scale=delta_scale, size=(dim,)).astype(np.float64)
        res = build_inheritance_vec(
            parents=[v],
            fractions=[1.0],
            novelty_vec=delta,
            production=False,  # allow arbitrary scale here
            scale=scale,
            norm_bound=DEFAULT_NORM_BOUND,
        )
        v = res.v_new
        norms.append(l2_norm(v))

    return norms


# ========================================================================== #
# Public exports                                                             #
# ========================================================================== #

__all__ = (
    "Vector",
    "PHI",
    "GOLDEN_SCALE",
    "DEFAULT_NORM_BOUND",
    "DEFAULT_EPS",
    "InheritanceResult",
    "l2_norm",
    "cosine_similarity",
    "softmax",
    "normalize_fractions",
    "build_inheritance_vec",
    "inheritance_construction",
    "simulate_inheritance_chain",
)
