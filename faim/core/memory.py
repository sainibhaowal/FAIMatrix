"""
FAIM Core Memory
================
The "Hippocampus" of the Engine.

This module consolidates all short-term indexing and retrieval mechanisms
into a single Memory component owned by the Engine.

Contains:
1. ANNIndex: Approximate Nearest Neighbor search (Vector Memory)
2. RadiusIndex: Radius search (Contradiction/Antisymmetry Memory)
3. UsageTracker: Usage statistics (Evolution Memory)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from time import time
from typing import Dict, List, Tuple

import numpy as np

from faim.core.types import GraphId, NodeId, NodeRecord, Vector

logger = logging.getLogger(__name__)


# =============================================================================
# 1. VECTOR MEMORY (ANN)
# =============================================================================


@dataclass
class _GraphIndex:
    """Per-graph vector index."""

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
                # Auto-correct or warn? For now strict.
                pass
            self.vecs = np.vstack([self.vecs, v])
        self.ids.append(node_id)

    def update(self, node_id: NodeId, vec: Vector) -> None:
        if node_id not in self.ids:
            return
        idx = self.ids.index(node_id)
        v = vec.astype(np.float32).reshape(1, -1)
        if self.vecs.size > 0:
            self.vecs[idx, :] = v

    def remove(self, node_id: NodeId) -> None:
        if node_id not in self.ids:
            return
        idx = self.ids.index(node_id)
        self.ids.pop(idx)
        if self.vecs.shape[0] > 1:
            self.vecs = np.delete(self.vecs, idx, axis=0)
        else:
            self.vecs = np.zeros((0, self.dim or 0), dtype=np.float32)

    def size(self) -> int:
        return len(self.ids)


class VectorMemory:
    """
    Handles similarity search (ANN) and radius queries.
    Replaces old ANNIndex and RadiusIndex.
    """

    def __init__(self, dim: int = 384) -> None:
        self._dim = dim
        self._per_graph: Dict[GraphId, _GraphIndex] = {}

    def _get(self, graph_id: GraphId) -> _GraphIndex:
        if graph_id not in self._per_graph:
            self._per_graph[graph_id] = _GraphIndex(dim=self._dim)
        return self._per_graph[graph_id]

    def add(self, graph_id: GraphId, node_id: NodeId, vec: Vector) -> None:
        self._get(graph_id).add(node_id, vec)

    def update(self, graph_id: GraphId, node_id: NodeId, vec: Vector) -> None:
        self._get(graph_id).update(node_id, vec)

    def remove(self, graph_id: GraphId, node_id: NodeId) -> None:
        self._get(graph_id).remove(node_id)

    def size(self, graph_id: GraphId) -> int:
        return self._get(graph_id).size()

    def search(
        self,
        graph_id: GraphId,
        query_vec: Vector,
        k: int = 10,
    ) -> List[Tuple[NodeId, float]]:
        """Find top-k similar nodes (dot product)."""
        g = self._per_graph.get(graph_id)
        if not g or g.size() == 0:
            return []

        q = query_vec.astype(np.float32).reshape(-1)
        if g.vecs.size == 0 or q.shape[0] != g.dim:
            return []

        scores = g.vecs @ q
        k_eff = max(0, min(k, g.size()))
        if k_eff == 0:
            return []

        # Argsort is slightly expensive for large N, but ok for <1M
        order = np.argsort(-scores)
        hits = []
        for idx in order[:k_eff]:
            hits.append((g.ids[int(idx)], float(scores[int(idx)])))
        return hits

    def query_radius(
        self,
        graph_id: GraphId,
        query_vec: Vector,
        radius: float,
    ) -> List[Tuple[NodeId, float]]:
        """Find all nodes within Euclidean distance radius."""
        g = self._per_graph.get(graph_id)
        if not g or g.size() == 0:
            return []

        v = query_vec.astype(np.float32).reshape(1, -1)
        if g.vecs.size == 0:
            return []

        diffs = g.vecs - v
        dists = np.linalg.norm(diffs, axis=1)
        mask = dists <= float(radius)
        idxs = np.nonzero(mask)[0]

        pairs = [(g.ids[int(i)], float(dists[int(i)])) for i in idxs]
        pairs.sort(key=lambda p: p[1])
        return pairs


# =============================================================================
# 2. USAGE MEMORY
# =============================================================================


@dataclass
class UsageTracker:
    """
    Tracks how often memories are accessed.
    Used by Evolution to determine node importance.
    """

    def touch(self, node: NodeRecord, *, at: float | None = None) -> None:
        """Mark a node as used."""
        now = time() if at is None else at
        node.use_count += 1
        node.last_used_at = now

    def score(self, node: NodeRecord) -> float:
        """Get usage score (currently just raw count)."""
        return float(node.use_count)
