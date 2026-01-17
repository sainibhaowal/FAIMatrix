"""FAIM-Native Qdrant Vector Index.

FAIM-native acceleration layer using Qdrant vector database.

Key properties:
- Dimension: 256 (imported from encoding.vector_schema)
- Point IDs: Deterministic (node UUID, NOT Python hash())
- Fallback: In-memory brute-force when Qdrant unavailable
- Stable ordering: Results sorted by (-score, node_id)
- Never a second truth: Index can be deleted and rebuilt

NO NUMPY IN PUBLIC API. NO ML DEPENDENCIES.
"""

from __future__ import annotations

import logging
import math
import os
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from .qdrant_collections import (
    VECTOR_DIMENSION,
    collection_name,
    create_payload,
    point_id_from_node_id,
)

logger = logging.getLogger(__name__)

# Type aliases
GraphId = str
NodeId = str
Vector = Tuple[float, ...]


# =============================================================================
# Qdrant Client (Lazy Loading)
# =============================================================================

_qdrant_client = None
_qdrant_available = None  # None = not checked, True/False = known


def _get_qdrant_url() -> str:
    """Get Qdrant URL from environment."""
    return os.getenv("QDRANT_URL", "http://localhost:6333")


def _get_qdrant_api_key() -> Optional[str]:
    """Get Qdrant API key from environment (optional)."""
    return os.getenv("QDRANT_API_KEY") or None


def _get_client() -> Any:
    """Get or create Qdrant client (lazy loading).

    Returns None if Qdrant is unavailable.
    """
    global _qdrant_client, _qdrant_available

    # Already checked and unavailable
    if _qdrant_available is False:
        return None

    if _qdrant_client is None:
        try:
            from qdrant_client import QdrantClient

            api_key = _get_qdrant_api_key()
            if api_key:
                _qdrant_client = QdrantClient(url=_get_qdrant_url(), api_key=api_key)
            else:
                _qdrant_client = QdrantClient(url=_get_qdrant_url())

            # Test connection
            _qdrant_client.get_collections()
            _qdrant_available = True
            logger.info(f"Connected to Qdrant at {_get_qdrant_url()}")

        except ImportError:
            logger.warning("qdrant-client not installed, using fallback")
            _qdrant_available = False
            _qdrant_client = None
        except Exception as e:
            logger.warning(f"Qdrant unavailable: {e}, using fallback")
            _qdrant_available = False
            _qdrant_client = None

    return _qdrant_client


def is_qdrant_available() -> bool:
    """Check if Qdrant is available."""
    _get_client()
    return _qdrant_available is True


# =============================================================================
# Brute-Force Fallback Index
# =============================================================================


class BruteForceIndex:
    """In-memory brute-force vector index.

    Used as fallback when Qdrant is unavailable.
    Ensures tests pass without Qdrant.
    """

    def __init__(self) -> None:
        # graph_id -> node_id -> (vector, payload)
        self._vectors: Dict[str, Dict[str, Tuple[Tuple[float, ...], Dict]]] = {}

    def add(
        self,
        graph_id: GraphId,
        node_id: NodeId,
        vector: Vector,
        payload: Optional[Dict] = None,
    ) -> None:
        """Add or update a vector."""
        if graph_id not in self._vectors:
            self._vectors[graph_id] = {}

        # Store as tuple for immutability
        v = tuple(vector) if not isinstance(vector, tuple) else vector
        self._vectors[graph_id][node_id] = (v, payload or {})

    def remove(self, graph_id: GraphId, node_id: NodeId) -> None:
        """Remove a vector."""
        if graph_id in self._vectors:
            self._vectors[graph_id].pop(node_id, None)

    def _cosine_similarity(self, v1: Tuple[float, ...], v2: Tuple[float, ...]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(v1) != len(v2):
            return 0.0

        dot = sum(a * b for a, b in zip(v1, v2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    def top_k(
        self,
        graph_id: GraphId,
        query_vec: Vector,
        k: int = 32,
    ) -> List[Tuple[NodeId, float]]:
        """Find top-k nearest neighbors.

        Results are sorted by (-score, node_id) for stable ordering.
        """
        if graph_id not in self._vectors:
            return []

        q = tuple(query_vec) if not isinstance(query_vec, tuple) else query_vec

        results = []
        for node_id, (vec, _payload) in self._vectors[graph_id].items():
            score = self._cosine_similarity(q, vec)
            results.append((node_id, score))

        # Sort by (-score, node_id) for stable ordering
        results.sort(key=lambda x: (-x[1], x[0]))

        return results[:k]

    def radius_search(
        self,
        graph_id: GraphId,
        query_vec: Vector,
        radius: float = 0.5,
        limit: int = 100,
    ) -> List[Tuple[NodeId, float]]:
        """Find all vectors within similarity threshold.

        Results are sorted by (-score, node_id) for stable ordering.
        """
        if graph_id not in self._vectors:
            return []

        q = tuple(query_vec) if not isinstance(query_vec, tuple) else query_vec
        threshold = 1.0 - radius  # Convert distance to similarity

        results = []
        for node_id, (vec, _payload) in self._vectors[graph_id].items():
            score = self._cosine_similarity(q, vec)
            if score >= threshold:
                results.append((node_id, score))

        # Sort by (-score, node_id) for stable ordering
        results.sort(key=lambda x: (-x[1], x[0]))

        return results[:limit]

    def count(self, graph_id: Optional[GraphId] = None) -> int:
        """Count vectors."""
        if graph_id:
            return len(self._vectors.get(graph_id, {}))
        return sum(len(v) for v in self._vectors.values())

    def delete_graph(self, graph_id: GraphId) -> None:
        """Delete all vectors for a graph."""
        self._vectors.pop(graph_id, None)

    def clear(self) -> None:
        """Clear all vectors."""
        self._vectors.clear()


# =============================================================================
# FAIM-Native Index
# =============================================================================


class FAIMIndex:
    """FAIM-native vector index with Qdrant backend and brute-force fallback.

    Key guarantees:
    - Dimension is always 256 (from encoding.vector_schema)
    - Point IDs are deterministic (node UUID, not hash())
    - Results are stably sorted by (-score, node_id)
    - If Qdrant unavailable, falls back to in-memory brute-force
    - Index is acceleration only, never a second truth
    """

    def __init__(
        self,
        project_id: UUID,
        dim: int = VECTOR_DIMENSION,
    ) -> None:
        """Initialize index for a project.

        Args:
            project_id: Project/tenant UUID.
            dim: Vector dimension (must be 256).
        """
        if dim != VECTOR_DIMENSION:
            raise ValueError(f"FAIM-native requires dim={VECTOR_DIMENSION}, got {dim}")

        self._project_id = project_id
        self._dim = dim
        self._collection = collection_name(project_id)

        # Fallback index (always available)
        self._fallback = BruteForceIndex()

        # Try to initialize Qdrant
        self._ensure_collection()

    @property
    def dim(self) -> int:
        """Vector dimension (always 256)."""
        return self._dim

    @property
    def uses_qdrant(self) -> bool:
        """Check if using Qdrant (vs fallback)."""
        return is_qdrant_available()

    def _ensure_collection(self) -> None:
        """Ensure collection exists in Qdrant."""
        client = _get_client()
        if client is None:
            return

        try:
            from qdrant_client.models import Distance, VectorParams

            collections = client.get_collections().collections
            exists = any(c.name == self._collection for c in collections)

            if not exists:
                client.create_collection(
                    collection_name=self._collection,
                    vectors_config=VectorParams(
                        size=self._dim,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Created Qdrant collection: {self._collection}")
        except Exception as e:
            logger.warning(f"Failed to ensure collection: {e}")

    def _stable_sort(
        self,
        results: List[Tuple[NodeId, float]],
    ) -> List[Tuple[NodeId, float]]:
        """Sort results by (-score, node_id) for stable ordering."""
        return sorted(results, key=lambda x: (-x[1], x[0]))

    def add(
        self,
        graph_id: GraphId,
        node_id: NodeId,
        vector: Vector,
        level: int = 0,
        kind: str = "atom",
    ) -> None:
        """Add or update a vector in the index.

        Args:
            graph_id: Graph identifier.
            node_id: Node identifier (used as point_id).
            vector: Vector tuple (must be 256 dim).
            level: Node level in hierarchy.
            kind: Node kind ("atom" or "macro").
        """
        if len(vector) != self._dim:
            raise ValueError(f"Vector must be {self._dim} dim, got {len(vector)}")

        # Always update fallback
        payload = create_payload(graph_id, node_id, level, kind)
        self._fallback.add(graph_id, node_id, vector, payload)

        # Try Qdrant
        client = _get_client()
        if client is None:
            return

        try:
            from qdrant_client.models import PointStruct

            # Use node_id as point_id (deterministic!)
            point_id = point_id_from_node_id(node_id)

            client.upsert(
                collection_name=self._collection,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=list(vector),
                        payload=payload,
                    )
                ],
            )
        except Exception as e:
            logger.warning(f"Qdrant upsert failed: {e}")

    def add_batch(
        self,
        graph_id: GraphId,
        items: List[Tuple[NodeId, Vector, int, str]],
    ) -> None:
        """Add multiple vectors in batch.

        Args:
            graph_id: Graph identifier.
            items: List of (node_id, vector, level, kind) tuples.
        """
        for node_id, vector, level, kind in items:
            self.add(graph_id, node_id, vector, level, kind)

    def remove(self, graph_id: GraphId, node_id: NodeId) -> None:
        """Remove a vector from the index."""
        # Remove from fallback
        self._fallback.remove(graph_id, node_id)

        # Try Qdrant
        client = _get_client()
        if client is None:
            return

        try:
            from qdrant_client.models import PointIdsList

            point_id = point_id_from_node_id(node_id)
            client.delete(
                collection_name=self._collection,
                points_selector=PointIdsList(points=[point_id]),
            )
        except Exception as e:
            logger.warning(f"Qdrant delete failed: {e}")

    def top_k(
        self,
        graph_id: GraphId,
        query_vec: Vector,
        k: int = 32,
    ) -> List[Tuple[NodeId, float]]:
        """Find top-k nearest neighbors.

        Results are stably sorted by (-score, node_id).

        Args:
            graph_id: Graph to search in.
            query_vec: Query vector.
            k: Number of results.

        Returns:
            List of (node_id, score) tuples, sorted stably.
        """
        client = _get_client()

        if client is None:
            # Use fallback
            return self._fallback.top_k(graph_id, query_vec, k)

        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            results = client.search(
                collection_name=self._collection,
                query_vector=list(query_vec),
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="graph_id",
                            match=MatchValue(value=str(graph_id)),
                        ),
                    ]
                ),
                limit=k,
            )

            raw_results = [(r.payload["node_id"], r.score) for r in results]

            # Stable sort by (-score, node_id)
            return self._stable_sort(raw_results)

        except Exception as e:
            logger.warning(f"Qdrant search failed: {e}, using fallback")
            return self._fallback.top_k(graph_id, query_vec, k)

    def radius_search(
        self,
        graph_id: GraphId,
        query_vec: Vector,
        radius: float = 0.5,
        limit: int = 100,
    ) -> List[Tuple[NodeId, float]]:
        """Find all vectors within similarity threshold.

        Results are stably sorted by (-score, node_id).
        """
        client = _get_client()

        if client is None:
            return self._fallback.radius_search(graph_id, query_vec, radius, limit)

        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            results = client.search(
                collection_name=self._collection,
                query_vector=list(query_vec),
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="graph_id",
                            match=MatchValue(value=str(graph_id)),
                        ),
                    ]
                ),
                score_threshold=1.0 - radius,
                limit=limit,
            )

            raw_results = [(r.payload["node_id"], r.score) for r in results]

            return self._stable_sort(raw_results)

        except Exception as e:
            logger.warning(f"Qdrant radius search failed: {e}, using fallback")
            return self._fallback.radius_search(graph_id, query_vec, radius, limit)

    def count(self, graph_id: Optional[GraphId] = None) -> int:
        """Count vectors in the index."""
        client = _get_client()

        if client is None:
            return self._fallback.count(graph_id)

        try:
            if graph_id:
                from qdrant_client.models import FieldCondition, Filter, MatchValue

                result = client.count(
                    collection_name=self._collection,
                    count_filter=Filter(
                        must=[
                            FieldCondition(
                                key="graph_id",
                                match=MatchValue(value=str(graph_id)),
                            ),
                        ]
                    ),
                )
            else:
                result = client.count(collection_name=self._collection)

            return result.count

        except Exception as e:
            logger.warning(f"Qdrant count failed: {e}, using fallback")
            return self._fallback.count(graph_id)

    def delete_graph(self, graph_id: GraphId) -> None:
        """Delete all vectors for a graph."""
        # Delete from fallback
        self._fallback.delete_graph(graph_id)

        # Try Qdrant
        client = _get_client()
        if client is None:
            return

        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            client.delete(
                collection_name=self._collection,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="graph_id",
                            match=MatchValue(value=str(graph_id)),
                        ),
                    ]
                ),
            )
            logger.info(f"Deleted vectors for graph {graph_id}")
        except Exception as e:
            logger.warning(f"Qdrant delete graph failed: {e}")

    def delete_collection(self) -> None:
        """Delete the entire collection."""
        self._fallback.clear()

        client = _get_client()
        if client is None:
            return

        try:
            client.delete_collection(collection_name=self._collection)
            logger.info(f"Deleted collection: {self._collection}")
        except Exception as e:
            logger.warning(f"Qdrant delete collection failed: {e}")


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "VECTOR_DIMENSION",
    "BruteForceIndex",
    "FAIMIndex",
    "is_qdrant_available",
]
