"""ANN index for model-generated semantic embeddings."""

from __future__ import annotations

import logging
from typing import Any, Iterable, List, Optional, Sequence, Tuple
from uuid import UUID

from .qdrant_collections import point_id_from_node_id

logger = logging.getLogger(__name__)


def _client() -> Any:
    from .qdrant_index import _get_client

    return _get_client()


def _collection_name(project_id: UUID, dimension: int) -> str:
    return f"faim_semantic_{str(project_id).replace('-', '_')}_{int(dimension)}"


def _project_id(graph_id: str, fallback: Optional[Any] = None) -> UUID:
    try:
        return UUID(str(fallback or graph_id))
    except (ValueError, TypeError, AttributeError):
        return UUID("00000000-0000-0000-0000-000000000000")


class SemanticQdrantIndex:
    """Dimension-specific Qdrant ANN index with a safe no-op fallback."""

    def __init__(self, project_id: UUID, dimension: int):
        if dimension <= 0:
            raise ValueError("semantic embedding dimension must be positive")
        self.collection = _collection_name(project_id, dimension)
        self.dimension = int(dimension)
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        client = _client()
        if client is None:
            return
        try:
            from qdrant_client.models import Distance, VectorParams

            collections = client.get_collections().collections
            if not any(item.name == self.collection for item in collections):
                client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE,
                    ),
                )
        except Exception as exc:
            logger.warning("Failed to ensure semantic Qdrant collection: %s", exc)

    def upsert_batch(
        self,
        graph_id: str,
        items: Iterable[Tuple[str, Sequence[float]]],
    ) -> int:
        rows = [(str(node_id), list(vector)) for node_id, vector in items]
        if not rows:
            return 0
        invalid = [len(vector) for _, vector in rows if len(vector) != self.dimension]
        if invalid:
            raise ValueError(
                f"semantic vector dimension mismatch: expected {self.dimension}, got {invalid[0]}"
            )
        client = _client()
        if client is None:
            return 0
        try:
            from qdrant_client.models import PointStruct

            client.upsert(
                collection_name=self.collection,
                points=[
                    PointStruct(
                        id=point_id_from_node_id(node_id),
                        vector=vector,
                        payload={"graph_id": str(graph_id), "node_id": node_id},
                    )
                    for node_id, vector in rows
                ],
                wait=True,
            )
            return len(rows)
        except Exception as exc:
            logger.warning("Semantic Qdrant batch upsert failed: %s", exc)
            return 0

    def top_k(
        self,
        graph_id: str,
        query_vector: Sequence[float],
        limit: int,
    ) -> List[Tuple[str, float]]:
        if len(query_vector) != self.dimension:
            return []
        client = _client()
        if client is None:
            return []
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="graph_id",
                        match=MatchValue(value=str(graph_id)),
                    )
                ]
            )
            if hasattr(client, "search"):
                results = client.search(
                    collection_name=self.collection,
                    query_vector=list(query_vector),
                    query_filter=query_filter,
                    limit=max(1, int(limit)),
                )
            else:
                response = client.query_points(
                    collection_name=self.collection,
                    query=list(query_vector),
                    query_filter=query_filter,
                    limit=max(1, int(limit)),
                    with_payload=True,
                )
                results = response.points
            rows = [
                (str(item.payload.get("node_id")), float(item.score))
                for item in results
                if item.payload and item.payload.get("node_id")
            ]
            return sorted(rows, key=lambda row: (-row[1], row[0]))
        except Exception as exc:
            logger.warning("Semantic Qdrant search failed: %s", exc)
            return []


def semantic_index_for_graph(
    graph_id: str,
    dimension: int,
    project_id: Optional[Any] = None,
) -> SemanticQdrantIndex:
    return SemanticQdrantIndex(_project_id(graph_id, project_id), dimension)


__all__ = ["SemanticQdrantIndex", "semantic_index_for_graph"]
