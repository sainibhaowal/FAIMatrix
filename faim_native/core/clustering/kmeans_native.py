"""Deterministic k-means clustering on FAIM v_native vectors.

Pure Python — zero ML, zero numpy, zero sklearn.

Rules:
- Cosine distance (1 - cosine_similarity) as metric
- k-means++ initialisation (deterministic seed from graph_id hash)
- Convergence: centroids unchanged OR max_iterations reached
- K = clamp(sqrt(N/2), 2, 20)
- Returns: cluster assignments + centroid vectors
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional
from uuid import UUID

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class ClusterResult:
    k: int
    iterations: int
    assignments: Dict[UUID, int]  # node_id → cluster_id
    centers: List[List[float]]  # cluster_id → centroid vector
    cluster_sizes: Dict[int, int]  # cluster_id → node count
    converged: bool


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))


def _norm(a: List[float]) -> float:
    return math.sqrt(sum(x * x for x in a))


def cosine_sim(a: List[float], b: List[float]) -> float:
    na, nb = _norm(a), _norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return _dot(a, b) / (na * nb)


def cosine_dist(a: List[float], b: List[float]) -> float:
    return 1.0 - cosine_sim(a, b)


def _mean_vector(vectors: List[List[float]]) -> List[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    result = [0.0] * dim
    n = len(vectors)
    for v in vectors:
        for i, x in enumerate(v):
            result[i] += x / n
    # L2-normalize the centroid so it's on the unit sphere (consistent with cosine)
    norm = math.sqrt(sum(x * x for x in result))
    if norm > 0:
        result = [x / norm for x in result]
    return result


# ---------------------------------------------------------------------------
# k selection
# ---------------------------------------------------------------------------


def choose_k(n_nodes: int) -> int:
    """Heuristic: sqrt(N/2), clamped to [2, 20]."""
    if n_nodes < 4:
        return 2
    k = max(2, min(20, int(math.sqrt(n_nodes / 2))))
    return k


# ---------------------------------------------------------------------------
# k-means++ initialisation
# ---------------------------------------------------------------------------


def _kmeans_plus_plus_init(
    vectors: List[List[float]],
    k: int,
    rng: random.Random,
) -> List[List[float]]:
    """Pick k seed centroids using k-means++ distance-weighted sampling."""
    n = len(vectors)
    first_idx = rng.randint(0, n - 1)
    centers = [vectors[first_idx][:]]

    for _ in range(1, k):
        # Compute min cosine distance from each point to nearest existing center
        dists = []
        for v in vectors:
            min_d = min(cosine_dist(v, c) for c in centers)
            dists.append(min_d**2)  # square for probability weighting

        total = sum(dists)
        if total == 0.0:
            # All points at zero distance — pick randomly
            centers.append(vectors[rng.randint(0, n - 1)][:])
        else:
            # Weighted random selection
            threshold = rng.random() * total
            cumulative = 0.0
            chosen = n - 1
            for i, d in enumerate(dists):
                cumulative += d
                if cumulative >= threshold:
                    chosen = i
                    break
            centers.append(vectors[chosen][:])

    return centers


# ---------------------------------------------------------------------------
# Core k-means
# ---------------------------------------------------------------------------


def _assign(vectors: List[List[float]], centers: List[List[float]]) -> List[int]:
    """Assign each vector to its nearest center by cosine distance."""
    assignments = []
    for v in vectors:
        best = 0
        best_d = float("inf")
        for ci, c in enumerate(centers):
            d = cosine_dist(v, c)
            if d < best_d:
                best_d = d
                best = ci
        assignments.append(best)
    return assignments


def _recompute_centers(
    vectors: List[List[float]],
    assignments: List[int],
    k: int,
) -> List[List[float]]:
    """Recompute centroid for each cluster."""
    groups: Dict[int, List[List[float]]] = {i: [] for i in range(k)}
    for v, a in zip(vectors, assignments, strict=False):
        groups[a].append(v)

    centers = []
    for ci in range(k):
        members = groups[ci]
        if members:
            centers.append(_mean_vector(members))
        else:
            # Empty cluster — keep old center (handled by caller)
            centers.append([])
    return centers


def _centers_equal(
    a: List[List[float]], b: List[List[float]], tol: float = 1e-6
) -> bool:
    if len(a) != len(b):
        return False
    for ca, cb in zip(a, b, strict=False):
        if len(ca) != len(cb):
            return False
        if any(abs(x - y) > tol for x, y in zip(ca, cb, strict=False)):
            return False
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_kmeans(
    node_ids: List[UUID],
    vectors: List[List[float]],
    graph_id: str,
    k: Optional[int] = None,
    max_iterations: int = 50,
) -> ClusterResult:
    """Run k-means clustering on v_native vectors.

    Args:
        node_ids: UUID list matching vectors order.
        vectors: v_native vectors as List[List[float]].
        graph_id: Used to seed the RNG deterministically.
        k: Number of clusters. If None, auto-selected via choose_k().
        max_iterations: Maximum iterations before forced convergence.

    Returns:
        ClusterResult with assignments, centers, and metadata.
    """
    n = len(vectors)
    if n == 0:
        return ClusterResult(
            k=0,
            iterations=0,
            assignments={},
            centers=[],
            cluster_sizes={},
            converged=True,
        )

    if k is None:
        k = choose_k(n)
    k = min(k, n)  # can't have more clusters than nodes

    # Deterministic seed from graph_id
    seed_int = int(hashlib.sha256(graph_id.encode()).hexdigest()[:16], 16)
    rng = random.Random(seed_int)

    # Initialise centers with k-means++
    centers = _kmeans_plus_plus_init(vectors, k, rng)

    assignments: List[int] = []
    converged = False

    for iteration in range(max_iterations):
        new_assignments = _assign(vectors, centers)
        new_centers = _recompute_centers(vectors, new_assignments, k)

        # Restore empty clusters with previous center
        for ci in range(k):
            if not new_centers[ci]:
                new_centers[ci] = centers[ci][:]

        if _centers_equal(centers, new_centers) and iteration > 0:
            assignments = new_assignments
            centers = new_centers
            converged = True
            break

        centers = new_centers
        assignments = new_assignments

    if not assignments:
        assignments = _assign(vectors, centers)

    # Build result
    assignment_map: Dict[UUID, int] = {
        node_id: cluster_id
        for node_id, cluster_id in zip(node_ids, assignments, strict=False)
    }
    cluster_sizes: Dict[int, int] = {}
    for cid in assignments:
        cluster_sizes[cid] = cluster_sizes.get(cid, 0) + 1

    return ClusterResult(
        k=k,
        iterations=iteration + 1 if not converged else iteration,
        assignments=assignment_map,
        centers=centers,
        cluster_sizes=cluster_sizes,
        converged=converged,
    )


def nearest_cluster(
    query_vector: List[float],
    centers: List[List[float]],
    top_k: int = 2,
) -> List[int]:
    """Return the top_k cluster IDs nearest to query_vector by cosine similarity.

    Used at query time to scope recall to relevant clusters.
    """
    if not centers:
        return []
    scored = [(ci, cosine_sim(query_vector, c)) for ci, c in enumerate(centers) if c]
    scored.sort(key=lambda x: -x[1])
    return [ci for ci, _ in scored[:top_k]]
