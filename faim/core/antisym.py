from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Optional, Sequence, Tuple

import numpy as np

from .types import NodeId, NodeRecord, Vector

# ========================================================================== #
#  FAIM Antisymmetric Core (Golden Edition)                                  #
# ========================================================================== #
#  Module: faim.core.antisym                                                 #
#                                                                           #
#  Purpose                                                                  #
#  -------                                                                  #
#  Implements the "A" in FAIM: antisymmetric opposition and merge logic     #
#  that ensures near-duplicates cancel instead of piling up.                #
#                                                                           #
#  Design Goals                                                             #
#  ------------                                                             #
#  - Deterministic, side-effect free math on pure vectors.                  #
#  - Clear separation between:                                              #
#       * distance/duplicate detection                                      #
#       * antisymmetric operators (Ω, wedge)                                #
#       * NodeRecord-level merge wiring                                     #
#       * redundancy diagnostics                                            #
#  - Backwards compatible with existing engine/tests.                       #
#                                                                           #
#  Notes                                                                    #
#  -----                                                                    #
#  - `opposition_update` is implemented in a wedge (projection) style so    #
#    that merging identical vectors drives the result to ~0 and is          #
#    idempotent when applied repeatedly with the same incoming vector.      #
#  - `merge_records` uses `opposition_update` and only updates scalar       #
#    counters; graph rewiring is handled by the engine.                     #
# ========================================================================== #

# --------------------------------------------------------------------------- #
# Constants                                                                  #
# --------------------------------------------------------------------------- #

#: Small epsilon used for numerical stability in norms and cosine similarity.
DEFAULT_EPS: float = 1e-8


# --------------------------------------------------------------------------- #
# Internal helpers                                                           #
# --------------------------------------------------------------------------- #


def _as_vec1d(vec: Vector, name: str) -> np.ndarray:
    """
    Convert an arbitrary vector-like into a 1D float32 NumPy array.

    - Accepts any array-like shape; flattens higher-dimensional inputs.
    - Keeps behaviour deterministic and avoids surprises in downstream math.
    """
    arr = np.asarray(vec, dtype=np.float32)
    if arr.ndim > 1:
        arr = arr.reshape(-1)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be 1D after flattening, got shape {arr.shape}")
    return arr


# --------------------------------------------------------------------------- #
# Distance / duplicate detection                                             #
# --------------------------------------------------------------------------- #


def euclidean_distance(a: Vector, b: Vector) -> float:
    """
    Compute Euclidean distance between two vectors.

    Parameters
    ----------
    a, b:
        Vectors in FAIM embedding space.

    Returns
    -------
    float
        ‖a - b‖_2 as a Python float.
    """
    a64 = _as_vec1d(a, "a").astype(np.float64)
    b64 = _as_vec1d(b, "b").astype(np.float64)
    return float(np.linalg.norm(a64 - b64))


def should_merge(
    candidate_vec: Vector,
    neighbor_vecs: Iterable[Tuple[NodeId, Vector]],
    *,
    theta: float,
) -> Optional[NodeId]:
    """
    Decide whether a candidate should merge into a nearby neighbor.

    Parameters
    ----------
    candidate_vec:
        Vector of the new node.
    neighbor_vecs:
        Iterable of (node_id, vec) pairs for neighbors in radius.
    theta:
        Distance threshold – if any neighbor is closer than `theta`, we
        consider it a near-duplicate and merge into that neighbor.

    Returns
    -------
    Optional[NodeId]
        The ID of the best merge target (closest neighbor within `theta`),
        or None if no neighbor qualifies.
    """
    best_id: Optional[NodeId] = None
    best_dist: float = float("inf")

    c = _as_vec1d(candidate_vec, "candidate_vec")

    for nid, vec in neighbor_vecs:
        dist = euclidean_distance(c, vec)
        if dist < theta and dist < best_dist:
            best_dist = dist
            best_id = nid

    return best_id


# --------------------------------------------------------------------------- #
# Core antisymmetric operators (Ω, wedge, cosine)                            #
# --------------------------------------------------------------------------- #


def opposition_vector(a: Vector, b: Vector) -> Vector:
    """
    Antisymmetric opposition operator:

        Ω(a, b) = a - b

    Properties
    ----------
    - Antisymmetric: Ω(a, b) = -Ω(b, a)
    - Linear in each argument.
    """
    a64 = _as_vec1d(a, "a").astype(np.float64)
    b64 = _as_vec1d(b, "b").astype(np.float64)
    return (a64 - b64).astype(np.float32)


def cosine_similarity(
    v_i: Vector,
    v_j: Vector,
    *,
    eps: float = DEFAULT_EPS,
) -> float:
    """
    Cosine similarity between two vectors.

    Parameters
    ----------
    v_i, v_j:
        Input vectors.
    eps:
        Small ε for numerical stability when norms are tiny.

    Returns
    -------
    float
        cos(θ) in [-1, 1], with 0.0 for degenerate zero vectors.
    """
    vi = _as_vec1d(v_i, "v_i").astype(np.float64)
    vj = _as_vec1d(v_j, "v_j").astype(np.float64)

    num = float(np.dot(vi, vj))
    denom = float(np.linalg.norm(vi) * np.linalg.norm(vj)) + eps
    if denom <= eps:
        return 0.0
    return num / denom


def practical_wedge_merge(
    v_rep: Vector,
    v_new: Vector,
    *,
    eps: float = DEFAULT_EPS,
) -> Vector:
    """
    Practical wedge-like merge operator for vector representatives.

    Given a representative vector `v_rep` and a near-duplicate `v_new`,
    construct:

        v_merge = v_rep - proj_{v_new}(v_rep)

    where proj_{v_new}(v_rep) is the projection of v_rep onto v_new.

    Intuition
    ---------
    - Subtracts exactly the redundant direction along `v_new` from `v_rep`.
    - After one application, `v_merge` is orthogonal to `v_new` (up to
      floating-point noise).
    - Applying the wedge again with the same `v_new` is idempotent.

    This is the vector-level implementation of the “wedge cancels the
    near-duplicate axis” idea used by FAIM's antisymmetric memory.
    """
    rep = _as_vec1d(v_rep, "v_rep").astype(np.float64)
    new = _as_vec1d(v_new, "v_new").astype(np.float64)

    denom = float(np.dot(new, new))
    if denom <= eps:
        # Degenerate: nothing to project on → return original representative.
        return rep.astype(np.float32)

    proj_coeff = float(np.dot(rep, new) / denom)
    merged = rep - proj_coeff * new
    return merged.astype(np.float32)


def opposition_update(
    base_vec: Vector,
    incoming_vec: Vector,
    *,
    alpha: float = 1.0,
) -> Vector:
    """
    Apply antisymmetric opposition (wedge-style) to update `base_vec`.

    Default behaviour (alpha=1.0)
    -----------------------------
    Uses `practical_wedge_merge(base_vec, incoming_vec)`:

        v' = v_base - proj_{incoming}(v_base)

    For identical vectors and alpha=1, v' is driven close to zero, which
    matches the existing test expectations.

    General alpha
    -------------
    For alpha ≠ 1, scales the removed projection:

        v' = v_base - alpha * proj_{incoming}(v_base)

    Properties
    ----------
    - Idempotent for alpha=1: applying `opposition_update` again with the
      same incoming_vec does not change v' (up to numerical noise).
    - Redundancy-reducing: removes the component of base_vec along the
      incoming direction instead of just subtracting the raw vector.
    """
    if alpha == 1.0:
        # Fast path: pure wedge.
        return practical_wedge_merge(base_vec, incoming_vec)

    # General case with scaled projection.
    b = _as_vec1d(base_vec, "base_vec").astype(np.float64)
    i = _as_vec1d(incoming_vec, "incoming_vec").astype(np.float64)

    denom = float(np.dot(i, i))
    if denom == 0.0:
        # Nothing to project on; leave unchanged.
        return b.astype(np.float32)

    proj_coeff = alpha * float(np.dot(b, i) / denom)
    updated = b - proj_coeff * i
    return updated.astype(np.float32)


# --------------------------------------------------------------------------- #
# NodeRecord-level merge wiring                                              #
# --------------------------------------------------------------------------- #


def merge_records(
    keep: NodeRecord,
    drop: NodeRecord,
    *,
    alpha: float = 1.0,
) -> NodeRecord:
    """
    Produce a new NodeRecord representing the antisymmetric merge keep ⊕ drop.

    Vector update
    -------------
    - Uses `opposition_update(keep.vec, drop.vec, alpha=alpha)` to cancel
      redundant components in the direction of `drop.vec`.

    Scalar counters
    ---------------
    - `use_count` is accumulated: keep.use_count + drop.use_count
    - `merged_count` is incremented by drop.merged_count + 1

    Graph structure
    ---------------
    - Parents/children rewiring is intentionally *not* handled here. That
      logic lives in the engine/graph layer, which decides how to rewire
      edges after the merge.

    Returns
    -------
    NodeRecord
        A new NodeRecord with updated vector and counters.
    """
    new_vec = opposition_update(keep.vec, drop.vec, alpha=alpha)
    return replace(
        keep,
        vec=new_vec,
        use_count=keep.use_count + drop.use_count,
        merged_count=keep.merged_count + drop.merged_count + 1,
    )


# --------------------------------------------------------------------------- #
# Redundancy diagnostics                                                     #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RedundancyStats:
    """
    Simple redundancy summary for a set of vectors.

    Attributes
    ----------
    mean_cosine:
        Average pairwise cosine similarity across all vector pairs.
    max_cosine:
        Maximum pairwise cosine similarity.
    count:
        Number of vectors in the set.
    """

    mean_cosine: float
    max_cosine: float
    count: int


def redundancy_stats(vectors: Sequence[Vector]) -> RedundancyStats:
    """
    Compute average and max pairwise cosine similarity as a redundancy proxy.

    Intended for diagnostics and tests: after antisymmetric merges, you
    should see redundancy (mean/max cosine) decrease.

    Parameters
    ----------
    vectors:
        Sequence of FAIM vectors (NodeRecord.vec or raw embeddings).

    Returns
    -------
    RedundancyStats
        Summary statistics over the provided set.
    """
    vs = [_as_vec1d(v, "vector").astype(np.float64) for v in vectors]
    n = len(vs)
    if n < 2:
        return RedundancyStats(mean_cosine=0.0, max_cosine=0.0, count=n)

    total = 0.0
    max_cos = -1.0
    pairs = 0

    for i in range(n):
        for j in range(i + 1, n):
            c = cosine_similarity(vs[i], vs[j])
            total += c
            max_cos = max(max_cos, c)
            pairs += 1

    mean_cos = total / pairs if pairs > 0 else 0.0
    return RedundancyStats(mean_cosine=mean_cos, max_cosine=max_cos, count=n)
