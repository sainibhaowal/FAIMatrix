"""
FAIM Cross-document Inference - AGI Feature #2

NEW MODULE - Does not modify any existing code.
Discovers connections between nodes from different documents.

Features:
- Find high-similarity nodes across documents
- Create inference links weighted by similarity
- Track inference provenance

Usage:
    POST /api/v1/graphs/{graph_id}/infer  - Run inference
    GET /api/v1/graphs/{graph_id}/inferences  - Get discovered connections
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import uuid4

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graphs", tags=["Inference"])


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class InferenceLink:
    """A discovered connection between nodes from different documents."""

    link_id: str
    source_node_id: str
    target_node_id: str
    similarity: float
    source_doc: Optional[str] = None
    target_doc: Optional[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class InferenceRequest(BaseModel):
    """Request to run inference."""

    min_similarity: float = 0.75  # Minimum similarity threshold
    max_results: int = 50  # Maximum inferences to return
    exclude_same_doc: bool = True  # Exclude nodes from same document


class InferenceResult(BaseModel):
    """Result of inference run."""

    graph_id: str
    total_nodes: int
    pairs_checked: int
    inferences_found: int
    inferences: List[dict]


# In-memory inference storage
_inferences: dict = {}  # graph_id -> List[InferenceLink]


# =============================================================================
# Inference Engine
# =============================================================================


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def get_document_source(node_record) -> Optional[str]:
    """Extract document source from node metadata."""
    # Try to get source from payload_ref or parents
    if hasattr(node_record, "payload_ref") and node_record.payload_ref:
        return str(node_record.payload_ref)[:16]
    return None


def run_inference(
    graph_id: str,
    min_similarity: float = 0.75,
    max_results: int = 50,
    exclude_same_doc: bool = True,
) -> Tuple[int, int, List[InferenceLink]]:
    """
    Run cross-document inference on a graph.

    Returns (total_nodes, pairs_checked, inferences)
    """
    try:
        from faim.api.production_state import get_faim_context

        ctx = get_faim_context(graph_id)
        store = ctx.get("store")

        if not store:
            return 0, 0, []

        # Get all nodes
        nodes = list(store.iter_nodes(graph_id))
        total_nodes = len(nodes)

        if total_nodes < 2:
            return total_nodes, 0, []

        # Build node list with vectors and docs
        node_data = []
        for node in nodes:
            doc_source = get_document_source(node)
            node_data.append(
                {
                    "id": str(node.node_id),
                    "vec": node.vec,
                    "doc": doc_source,
                }
            )

        # Find high-similarity pairs
        inferences = []
        pairs_checked = 0

        for i in range(len(node_data)):
            for j in range(i + 1, len(node_data)):
                pairs_checked += 1

                n1 = node_data[i]
                n2 = node_data[j]

                # Skip same document if requested
                if exclude_same_doc and n1["doc"] and n1["doc"] == n2["doc"]:
                    continue

                # Calculate similarity
                sim = cosine_similarity(n1["vec"], n2["vec"])

                if sim >= min_similarity:
                    inference = InferenceLink(
                        link_id=uuid4().hex[:12],
                        source_node_id=n1["id"],
                        target_node_id=n2["id"],
                        similarity=sim,
                        source_doc=n1["doc"],
                        target_doc=n2["doc"],
                    )
                    inferences.append(inference)

                # Limit results
                if len(inferences) >= max_results:
                    break

            if len(inferences) >= max_results:
                break

        # Sort by similarity (highest first)
        inferences.sort(key=lambda x: x.similarity, reverse=True)

        # Store inferences
        _inferences[graph_id] = inferences

        return total_nodes, pairs_checked, inferences

    except Exception as e:
        logger.error(f"Inference failed: {e}")
        return 0, 0, []


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("/{graph_id}/infer")
async def infer_connections(graph_id: str, request: InferenceRequest = None):
    """
    Run cross-document inference to find connections.
    
    Analyzes node embeddings to find similar concepts across different documents.
    
    Example:
        curl -X POST http://localhost:8000/api/v1/graphs/MAIN/infer \
            -H "Content-Type: application/json" \
            -d '{"min_similarity": 0.8, "max_results": 20}'
    """
    if request is None:
        request = InferenceRequest()

    total_nodes, pairs_checked, inferences = run_inference(
        graph_id=graph_id,
        min_similarity=request.min_similarity,
        max_results=request.max_results,
        exclude_same_doc=request.exclude_same_doc,
    )

    return {
        "graph_id": graph_id,
        "total_nodes": total_nodes,
        "pairs_checked": pairs_checked,
        "inferences_found": len(inferences),
        "inferences": [
            {
                "link_id": inf.link_id,
                "source": inf.source_node_id,
                "target": inf.target_node_id,
                "similarity": round(inf.similarity, 4),
                "source_doc": inf.source_doc,
                "target_doc": inf.target_doc,
            }
            for inf in inferences
        ],
    }


@router.get("/{graph_id}/inferences")
async def get_inferences(
    graph_id: str,
    min_similarity: float = 0.0,
    limit: int = 50,
):
    """
    Get previously discovered inferences.

    Example:
        curl http://localhost:8000/api/v1/graphs/MAIN/inferences?min_similarity=0.8
    """
    inferences = _inferences.get(graph_id, [])

    # Filter by similarity
    if min_similarity > 0:
        inferences = [inf for inf in inferences if inf.similarity >= min_similarity]

    # Limit results
    inferences = inferences[:limit]

    return {
        "graph_id": graph_id,
        "count": len(inferences),
        "inferences": [
            {
                "link_id": inf.link_id,
                "source": inf.source_node_id,
                "target": inf.target_node_id,
                "similarity": round(inf.similarity, 4),
                "source_doc": inf.source_doc,
                "target_doc": inf.target_doc,
            }
            for inf in inferences
        ],
    }


@router.delete("/{graph_id}/inferences")
async def clear_inferences(graph_id: str):
    """Clear cached inferences for a graph."""
    if graph_id in _inferences:
        del _inferences[graph_id]
        return {"cleared": True}
    return {"cleared": False, "message": "No inferences found"}
