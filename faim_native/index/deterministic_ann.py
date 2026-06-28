"""Deterministic VP-tree ANN for FAIM native vectors.

The build and search order are fixed to keep results stable. This layer is
acceleration only; callers can always fall back to exact brute-force scoring.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple
from uuid import UUID

Vector = Tuple[float, ...]


def cosine_similarity(a: Vector, b: Vector) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a <= 1e-12 or norm_b <= 1e-12:
        return 0.0
    return dot / (norm_a * norm_b)


def cosine_distance(a: Vector, b: Vector) -> float:
    return 1.0 - cosine_similarity(a, b)


@dataclass(frozen=True)
class VectorPoint:
    node_id: UUID
    vector: Vector
    unit_vector: Vector = field(default=())


@dataclass
class VPTreeNode:
    point: VectorPoint
    threshold: float
    left: Optional["VPTreeNode"] = None
    right: Optional["VPTreeNode"] = None


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _choose_pivot(points: Sequence[VectorPoint]) -> VectorPoint:
    return sorted(points, key=lambda item: str(item.node_id))[0]


def _normalize_vector(vector: Vector) -> Vector:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 1e-12:
        return tuple(0.0 for _ in vector)
    return tuple(value / norm for value in vector)


def _ensure_unit_point(point: VectorPoint) -> VectorPoint:
    if point.unit_vector:
        return point
    return VectorPoint(
        node_id=point.node_id,
        vector=point.vector,
        unit_vector=_normalize_vector(point.vector),
    )


def _euclidean_distance(a: Vector, b: Vector) -> float:
    return math.sqrt(sum((x - y) * (x - y) for x, y in zip(a, b, strict=False)))


def _similarity_to_distance_threshold(similarity: float) -> float:
    similarity = max(-1.0, min(1.0, similarity))
    return math.sqrt(max(0.0, 2.0 * (1.0 - similarity)))


def _distance_to_similarity(distance: float) -> float:
    return 1.0 - (distance * distance) / 2.0


def build_vptree(points: Sequence[VectorPoint]) -> Optional[VPTreeNode]:
    if not points:
        return None

    normalized_points = tuple(_ensure_unit_point(point) for point in points)
    if len(normalized_points) == 1:
        return VPTreeNode(point=normalized_points[0], threshold=0.0)

    pivot = _choose_pivot(normalized_points)
    others = [p for p in normalized_points if p.node_id != pivot.node_id]
    distances = [
        (p, _euclidean_distance(pivot.unit_vector, p.unit_vector)) for p in others
    ]
    threshold = _median([dist for _p, dist in distances])
    left_points = [p for p, dist in distances if dist <= threshold]
    right_points = [p for p, dist in distances if dist > threshold]
    return VPTreeNode(
        point=pivot,
        threshold=threshold,
        left=build_vptree(left_points),
        right=build_vptree(right_points),
    )


def exact_top_k(
    points: Iterable[VectorPoint], query_vec: Vector, k: int
) -> List[Tuple[UUID, float]]:
    query_unit = _normalize_vector(query_vec)
    scored = [
        (
            point.node_id,
            cosine_similarity(
                query_unit,
                point.unit_vector or _normalize_vector(point.vector),
            ),
        )
        for point in points
    ]
    scored.sort(key=lambda item: (-item[1], str(item[0])))
    return scored[:k]


def search_vptree(
    root: Optional[VPTreeNode], query_vec: Vector, k: int
) -> List[Tuple[UUID, float]]:
    if root is None or k <= 0:
        return []

    query_unit = _normalize_vector(query_vec)
    best: List[Tuple[float, UUID]] = []

    def worst_distance() -> float:
        if len(best) < k:
            return float("inf")
        worst_distance_value, _worst_id = max(
            best, key=lambda item: (item[0], str(item[1]))
        )
        return worst_distance_value

    def push(point: VectorPoint) -> None:
        similarity = cosine_similarity(
            query_unit,
            point.unit_vector or _normalize_vector(point.vector),
        )
        distance = _similarity_to_distance_threshold(similarity)
        candidate = (distance, point.node_id)
        if len(best) < k:
            best.append(candidate)
            return
        worst = max(best, key=lambda item: (item[0], str(item[1])))
        if candidate[0] < worst[0] or (
            math.isclose(candidate[0], worst[0], rel_tol=1e-12, abs_tol=1e-12)
            and str(candidate[1]) < str(worst[1])
        ):
            best.remove(worst)
            best.append(candidate)

    def search(node: Optional[VPTreeNode]) -> None:
        if node is None:
            return

        pivot = node.point
        pivot_unit = pivot.unit_vector or _normalize_vector(pivot.vector)
        query_distance = _euclidean_distance(query_unit, pivot_unit)
        push(pivot)

        tau = worst_distance()
        if query_distance < node.threshold:
            search(node.left)
            tau = worst_distance()
            if query_distance + tau >= node.threshold:
                search(node.right)
        else:
            search(node.right)
            tau = worst_distance()
            if query_distance - tau <= node.threshold:
                search(node.left)

    search(root)

    ranked = sorted(
        (
            (node_id, _distance_to_similarity(distance))
            for distance, node_id in best
        ),
        key=lambda item: (-item[1], str(item[0])),
    )
    return ranked[:k]


__all__ = [
    "VectorPoint",
    "VPTreeNode",
    "build_vptree",
    "search_vptree",
    "exact_top_k",
]
