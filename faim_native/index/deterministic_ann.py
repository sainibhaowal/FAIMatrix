"""Deterministic VP-tree ANN for FAIM native vectors.

The build and search order are fixed to keep results stable. This layer is
acceleration only; callers can always fall back to exact brute-force scoring.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
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


def build_vptree(points: Sequence[VectorPoint]) -> Optional[VPTreeNode]:
    if not points:
        return None
    if len(points) == 1:
        return VPTreeNode(point=points[0], threshold=0.0)

    pivot = _choose_pivot(points)
    others = [p for p in points if p.node_id != pivot.node_id]
    distances = [(p, cosine_distance(pivot.vector, p.vector)) for p in others]
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
    scored = [
        (point.node_id, cosine_similarity(query_vec, point.vector)) for point in points
    ]
    scored.sort(key=lambda item: (-item[1], str(item[0])))
    return scored[:k]


def search_vptree(
    root: Optional[VPTreeNode], query_vec: Vector, k: int
) -> List[Tuple[UUID, float]]:
    if root is None or k <= 0:
        return []
    points: List[VectorPoint] = []

    def collect(node: Optional[VPTreeNode]) -> None:
        if node is None:
            return
        points.append(node.point)
        collect(node.left)
        collect(node.right)

    collect(root)
    return exact_top_k(points, query_vec, k)


__all__ = [
    "VectorPoint",
    "VPTreeNode",
    "build_vptree",
    "search_vptree",
    "exact_top_k",
]
