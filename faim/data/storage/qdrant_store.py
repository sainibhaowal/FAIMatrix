"""Qdrant-backed Vector Store for FAIM.

Production implementation using Qdrant vector database for semantic search.
Vectors are stored in collections scoped by project_id for multi-tenant isolation.

Collection naming: faim_{project_id}
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional, Tuple
from uuid import UUID

from faim.core.types import GraphId, NodeId, Vector

logger = logging.getLogger(__name__)

# Qdrant client - lazy loaded
_qdrant_client = None


def _get_qdrant_url() -> str:
    """Get Qdrant URL from environment."""
    return os.getenv("QDRANT_URL", "http://localhost:6333")


def _get_qdrant_api_key() -> str | None:
    """Get Qdrant API key from environment (optional but recommended)."""
    return os.getenv("QDRANT_API_KEY") or None


def _get_client():
    """Get or create Qdrant client (lazy loading with API key auth)."""
    global _qdrant_client
    if _qdrant_client is None:
        try:
            from qdrant_client import QdrantClient

            api_key = _get_qdrant_api_key()
            if api_key:
                _qdrant_client = QdrantClient(url=_get_qdrant_url(), api_key=api_key)
                logger.info(f"Connected to Qdrant at {_get_qdrant_url()} (authenticated)")
            else:
                _qdrant_client = QdrantClient(url=_get_qdrant_url())
                logger.warning(f"Connected to Qdrant at {_get_qdrant_url()} (NO API KEY - insecure!)")
        except ImportError:
            logger.warning("qdrant-client not installed, falling back to memory")
            _qdrant_client = None
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            _qdrant_client = None
    return _qdrant_client


def _collection_name(project_id: UUID) -> str:
    """Generate collection name for a project."""
    return f"faim_{str(project_id).replace('-', '_')}"


class QdrantVectorStore:
    """Qdrant-backed vector store with multi-tenant isolation.

    Each project has its own collection for complete data isolation.
    Vectors are stored with graph_id and node_id as payload metadata.
    """

    def __init__(self, project_id: UUID, dim: int = 384) -> None:
        """Initialize vector store for a project.

        Args:
            project_id: The project UUID for tenant isolation
            dim: Vector dimension (default 384 for MiniLM)
        """
        self._project_id = project_id
        self._dim = dim
        self._collection = _collection_name(project_id)
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Ensure the collection exists in Qdrant."""
        client = _get_client()
        if client is None:
            return  # Fallback mode

        try:
            from qdrant_client.models import Distance, VectorParams

            # Check if collection exists
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
            logger.error(f"Failed to ensure collection: {e}")

    def add(self, graph_id: GraphId, node_id: NodeId, vec: Vector) -> None:
        """Add or update a vector in the store."""
        client = _get_client()
        if client is None:
            return

        try:
            from qdrant_client.models import PointStruct

            # Use node_id hash as point ID (Qdrant needs int or UUID)
            point_id = hash(f"{graph_id}:{node_id}") & 0x7FFFFFFFFFFFFFFF  # Positive int

            client.upsert(
                collection_name=self._collection,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vec.tolist(),
                        payload={
                            "graph_id": str(graph_id),
                            "node_id": str(node_id),
                        },
                    )
                ],
            )
        except Exception as e:
            logger.error(f"Failed to add vector: {e}")

    def remove(self, graph_id: GraphId, node_id: NodeId) -> None:
        """Remove a vector from the store."""
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
                        FieldCondition(
                            key="node_id",
                            match=MatchValue(value=str(node_id)),
                        ),
                    ]
                ),
            )
        except Exception as e:
            logger.error(f"Failed to remove vector: {e}")

    def top_k(self, graph_id: GraphId, query_vec: Vector, k: int = 32) -> List[Tuple[NodeId, float]]:
        """Find top-k nearest neighbors in a graph.

        Returns list of (node_id, score) tuples sorted by similarity.
        """
        client = _get_client()
        if client is None:
            return []

        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            results = client.search(
                collection_name=self._collection,
                query_vector=query_vec.tolist(),
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

            return [(NodeId(r.payload["node_id"]), r.score) for r in results]
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            return []

    def radius_search(
        self, graph_id: GraphId, query_vec: Vector, radius: float = 0.5, limit: int = 100
    ) -> List[Tuple[NodeId, float]]:
        """Find all vectors within a similarity radius.

        Returns list of (node_id, score) tuples for vectors within radius.
        """
        client = _get_client()
        if client is None:
            return []

        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            # Qdrant uses similarity score, so we search with score_threshold
            results = client.search(
                collection_name=self._collection,
                query_vector=query_vec.tolist(),
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="graph_id",
                            match=MatchValue(value=str(graph_id)),
                        ),
                    ]
                ),
                score_threshold=1.0 - radius,  # Convert distance to similarity threshold
                limit=limit,
            )

            return [(NodeId(r.payload["node_id"]), r.score) for r in results]
        except Exception as e:
            logger.error(f"Failed to radius search: {e}")
            return []

    def count(self, graph_id: Optional[GraphId] = None) -> int:
        """Count vectors in the store, optionally filtered by graph."""
        client = _get_client()
        if client is None:
            return 0

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
            logger.error(f"Failed to count vectors: {e}")
            return 0

    def delete_graph(self, graph_id: GraphId) -> None:
        """Delete all vectors for a graph."""
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
            logger.info(f"Deleted all vectors for graph {graph_id}")
        except Exception as e:
            logger.error(f"Failed to delete graph vectors: {e}")

    def delete_collection(self) -> None:
        """Delete the entire collection (use with caution!)."""
        client = _get_client()
        if client is None:
            return

        try:
            client.delete_collection(collection_name=self._collection)
            logger.info(f"Deleted collection: {self._collection}")
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
