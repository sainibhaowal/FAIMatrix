"""Radius index for antisymmetric neighbor search.

P2 baseline: linear radius queries on NumPy arrays.

Used mainly by the antisymmetry path in FAIMEngine:
- engine calls RadiusIndex.query_radius(graph_id, vec, radius)
  to find candidates for merge/cancel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np

from faim.core.types import GraphId, NodeId, Vector


@dataclass
class _GraphRadiusIndex:
    """Per-graph radius index (Euclidean baseline)."""

    ids: List[NodeId] = field(default_factory=list)
    vecs: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), dtype=np.float32))
    dim: int = 0

    def add(self, node_id: NodeId, vec: Vector) -> None:
        v = vec.astype(np.float32).reshape(1, -1)
        if self.vecs.size == 0:
            self.vecs = v
            self.dim = v.shape[1]
        else:
            if v.shape[1] != self.dim:
                raise ValueError(
                    f"Dimension mismatch in RadiusIndex: have {self.dim}, got {v.shape[1]}"
                )
            self.vecs = np.vstack([self.vecs, v])
        self.ids.append(node_id)

    def update(self, node_id: NodeId, vec: Vector) -> None:
        if node_id not in self.ids:
            return
        idx = self.ids.index(node_id)
        v = vec.astype(np.float32).reshape(1, -1)
        if self.vecs.size == 0:
            self.vecs = v
            self.dim = v.shape[1]
            self.ids[:] = [node_id]
        else:
            if v.shape[1] != self.dim:
                raise ValueError(
                    f"Dimension mismatch in RadiusIndex.update: have {self.dim}, got {v.shape[1]}"
                )
            self.vecs[idx, :] = v

    def remove(self, node_id: NodeId) -> None:
        if node_id not in self.ids:
            return
        idx = self.ids.index(node_id)
        self.ids.pop(idx)
        if self.vecs.shape[0] > 1:
            self.vecs = np.delete(self.vecs, idx, axis=0)
        else:
            # Keep shape consistent even when empty.
            self.vecs = np.zeros((0, self.dim or 0), dtype=np.float32)

    def size(self) -> int:
        return len(self.ids)


class RadiusIndex:
    """Radius index wrapper for FAIM.

    Engine contract (P2):
    - size(graph_id) -> int
    - add(graph_id, node_id, vec) -> None
    - update(graph_id, node_id, vec) -> None
    - remove(graph_id, node_id) -> None
    - query_radius(graph_id, query_vec, radius) -> list[(node_id, dist)]
    """

    def __init__(self, dim: int) -> None:
        self._dim = dim
        self._per_graph: Dict[GraphId, _GraphRadiusIndex] = {}

    def _get_or_create(self, graph_id: GraphId) -> _GraphRadiusIndex:
        if graph_id not in self._per_graph:
            self._per_graph[graph_id] = _GraphRadiusIndex(dim=self._dim)
        return self._per_graph[graph_id]

    def size(self, graph_id: GraphId) -> int:
        return self._per_graph.get(graph_id, _GraphRadiusIndex(dim=self._dim)).size()

    def add(self, graph_id: GraphId, node_id: NodeId, vec: Vector) -> None:
        g = self._get_or_create(graph_id)
        g.add(node_id, vec)

    def update(self, graph_id: GraphId, node_id: NodeId, vec: Vector) -> None:
        g = self._get_or_create(graph_id)
        g.update(node_id, vec)

    def remove(self, graph_id: GraphId, node_id: NodeId) -> None:
        g = self._per_graph.get(graph_id)
        if g is not None:
            g.remove(node_id)

    def query_radius(
        self,
        graph_id: GraphId,
        query_vec: Vector,
        *,
        radius: float,
    ) -> List[Tuple[NodeId, float]]:
        """Engine-facing API: all neighbors within `radius` (Euclidean).

        Results are sorted by ascending distance.
        """
        g = self._per_graph.get(graph_id)
        if g is None or g.size() == 0:
            return []

        v = query_vec.astype(np.float32).reshape(1, -1)
        if v.shape[1] != g.dim:
            raise ValueError(
                f"Query dim mismatch in RadiusIndex.query_radius: "
                f"index dim={g.dim}, query dim={v.shape[1]}"
            )

        if g.vecs.size == 0:
            return []

        diffs = g.vecs - v  # shape (N, D)
        dists = np.linalg.norm(diffs, axis=1)
        mask = dists <= float(radius)
        idxs = np.nonzero(mask)[0]

        pairs: List[Tuple[NodeId, float]] = [(g.ids[int(i)], float(dists[int(i)])) for i in idxs]
        pairs.sort(key=lambda pair: pair[1])
        return pairs

    # Optional alias if you want to keep the old name around internally
    def neighbors_within(
        self,
        graph_id: GraphId,
        query_vec: Vector,
        radius: float,
    ) -> List[Tuple[NodeId, float]]:
        """Compatibility alias for query_radius."""
        return self.query_radius(graph_id, query_vec, radius=radius)
