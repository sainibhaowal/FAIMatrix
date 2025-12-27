"""Approximate Nearest Neighbour (ANN) index (CPU baseline).

P2 baseline: a simple in-memory per-graph index using NumPy.
Ready to be swapped with FAISS/pgvector in the future.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np

from faim.core.types import GraphId, NodeId, Vector


@dataclass
class _GraphIndex:
    """Per-graph ANN index."""

    ids: List[NodeId] = field(default_factory=list)
    vecs: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), dtype=np.float32))
    dim: int = 0

    def add(self, node_id: NodeId, vec: Vector) -> None:
        """Append a new vector for node_id."""
        v = vec.astype(np.float32).reshape(1, -1)
        if self.vecs.size == 0:
            self.vecs = v
            self.dim = v.shape[1]
        else:
            if v.shape[1] != self.dim:
                raise ValueError(
                    f"Dimension mismatch in ANNIndex: have {self.dim}, got {v.shape[1]}"
                )
            self.vecs = np.vstack([self.vecs, v])
        self.ids.append(node_id)

    def update(self, node_id: NodeId, vec: Vector) -> None:
        """Update an existing node vector (no-op if node_id not present)."""
        if node_id not in self.ids:
            return
        idx = self.ids.index(node_id)
        v = vec.astype(np.float32).reshape(1, -1)
        if self.vecs.size == 0:
            # Treat as add, but this should not normally happen.
            self.vecs = v
            self.dim = v.shape[1]
            self.ids[:] = [node_id]
        else:
            if v.shape[1] != self.dim:
                raise ValueError(
                    f"Dimension mismatch in ANNIndex.update: have {self.dim}, got {v.shape[1]}"
                )
            self.vecs[idx, :] = v

    def remove(self, node_id: NodeId) -> None:
        """Remove node_id and its vector, if present."""
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


class ANNIndex:
    """ANN index wrapper for FAIM.

    P2: linear scan using NumPy. Deterministic and sufficient for up to ~1M nodes
    on a single machine; can later be swapped with FAISS/HNSW without changing the
    engine API.
    """

    def __init__(self, dim: int) -> None:
        self._dim = dim
        self._per_graph: Dict[GraphId, _GraphIndex] = {}

    def _get_or_create(self, graph_id: GraphId) -> _GraphIndex:
        if graph_id not in self._per_graph:
            self._per_graph[graph_id] = _GraphIndex(dim=self._dim)
        return self._per_graph[graph_id]

    def size(self, graph_id: GraphId) -> int:
        return self._per_graph.get(graph_id, _GraphIndex(dim=self._dim)).size()

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

    def top_k(
        self,
        graph_id: GraphId,
        query_vec: Vector,
        k: int,
    ) -> List[Tuple[NodeId, float]]:
        """Return top-k neighbors by dot-product similarity (per graph).

        Deterministic, CPU-only baseline: O(N) scan over all vectors.
        """
        g = self._per_graph.get(graph_id)
        if g is None or g.size() == 0:
            return []

        q = query_vec.astype(np.float32).reshape(-1)
        if q.shape[0] != g.dim:
            raise ValueError(
                f"Query dim mismatch in ANNIndex.top_k: index dim={g.dim}, query dim={q.shape[0]}"
            )

        if g.vecs.size == 0:
            return []

        scores = g.vecs @ q  # shape (N,)
        k_eff = max(0, min(k, g.size()))
        if k_eff == 0:
            return []

        order = np.argsort(-scores)  # descending
        hits: List[Tuple[NodeId, float]] = []
        for idx in order[:k_eff]:
            hits.append((g.ids[int(idx)], float(scores[int(idx)])))
        return hits
