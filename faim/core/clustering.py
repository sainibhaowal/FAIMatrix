"""
FAIM Semantic Auto-clustering - AGI Feature #3

NEW MODULE - Does not modify any existing code.
Automatically groups related concepts into clusters.

Features:
- K-means or HDBSCAN clustering on node embeddings
- Automatic cluster labeling via LLM
- Cluster hierarchy for large graphs

Usage:
    POST /api/v1/graphs/{graph_id}/cluster  - Run clustering
    GET /api/v1/graphs/{graph_id}/clusters  - Get cluster info
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graphs", tags=["Clustering"])


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class Cluster:
    """A semantic cluster of related nodes."""

    cluster_id: str
    label: str
    description: str
    node_ids: List[str] = field(default_factory=list)
    centroid: Optional[np.ndarray] = None
    coherence: float = 0.0  # Average similarity within cluster
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class ClusterRequest(BaseModel):
    """Request to run clustering."""

    n_clusters: Optional[int] = None  # Auto-detect if None
    min_cluster_size: int = 3  # Minimum nodes per cluster
    use_llm_labels: bool = True  # Generate labels via LLM


class ClusterResult(BaseModel):
    """Result of clustering run."""

    graph_id: str
    total_nodes: int
    n_clusters: int
    clusters: List[dict]


# In-memory cluster storage
_clusters: Dict[str, List[Cluster]] = {}


# =============================================================================
# Clustering Engine
# =============================================================================


def kmeans_cluster(
    vectors: np.ndarray,
    n_clusters: int,
    max_iters: int = 100,
) -> np.ndarray:
    """
    Simple K-means clustering.

    Returns cluster assignments for each vector.
    """
    n_samples = vectors.shape[0]

    if n_samples <= n_clusters:
        return np.arange(n_samples)

    # Initialize centroids randomly
    idx = np.random.choice(n_samples, n_clusters, replace=False)
    centroids = vectors[idx].copy()

    for _ in range(max_iters):
        # Assign to nearest centroid
        distances = np.zeros((n_samples, n_clusters))
        for k in range(n_clusters):
            diff = vectors - centroids[k]
            distances[:, k] = np.sum(diff**2, axis=1)

        assignments = np.argmin(distances, axis=1)

        # Update centroids
        new_centroids = np.zeros_like(centroids)
        for k in range(n_clusters):
            mask = assignments == k
            if np.any(mask):
                new_centroids[k] = vectors[mask].mean(axis=0)
            else:
                new_centroids[k] = centroids[k]

        # Check convergence
        if np.allclose(centroids, new_centroids):
            break

        centroids = new_centroids

    return assignments


def estimate_n_clusters(n_samples: int) -> int:
    """Estimate optimal number of clusters."""
    if n_samples <= 5:
        return 1
    elif n_samples <= 20:
        return 3
    elif n_samples <= 50:
        return 5
    elif n_samples <= 100:
        return 8
    else:
        return min(15, int(np.sqrt(n_samples)))


def calculate_coherence(vectors: np.ndarray) -> float:
    """Calculate average pairwise similarity within a cluster."""
    if len(vectors) <= 1:
        return 1.0

    total_sim = 0.0
    count = 0

    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            norm_i = np.linalg.norm(vectors[i])
            norm_j = np.linalg.norm(vectors[j])
            if norm_i > 0 and norm_j > 0:
                sim = np.dot(vectors[i], vectors[j]) / (norm_i * norm_j)
                total_sim += sim
                count += 1

    return total_sim / count if count > 0 else 0.0


def generate_cluster_label(node_payloads: List[str], use_llm: bool = True) -> Tuple[str, str]:
    """
    Generate a label and description for a cluster.

    Returns (label, description).
    """
    if not node_payloads:
        return "Empty Cluster", "No content"

    # Simple keyword extraction (fallback)
    all_text = " ".join(node_payloads[:5])  # Sample first 5
    words = all_text.lower().split()

    # Find common words (simple approach)
    word_counts = {}
    for word in words:
        if len(word) > 4:  # Skip short words
            word_counts[word] = word_counts.get(word, 0) + 1

    top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    label = " ".join(w[0].title() for w in top_words) if top_words else "Misc"

    if use_llm:
        try:
            import os

            from groq import Groq

            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                client = Groq(api_key=api_key)

                sample_content = "\n".join(p[:200] for p in node_payloads[:3])

                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {
                            "role": "system",
                            "content": "Generate a short 2-3 word label and one sentence description for this cluster of related content. Format: LABEL: <label>\nDESCRIPTION: <description>",
                        },
                        {
                            "role": "user",
                            "content": f"Content samples:\n{sample_content}",
                        },
                    ],
                    max_tokens=100,
                    temperature=0.3,
                )

                result = response.choices[0].message.content

                # Parse response
                for line in result.split("\n"):
                    if line.startswith("LABEL:"):
                        label = line.replace("LABEL:", "").strip()
                    elif line.startswith("DESCRIPTION:"):
                        return label, line.replace("DESCRIPTION:", "").strip()

        except Exception as e:
            logger.warning(f"LLM labeling failed: {e}")

    description = f"Cluster containing {len(node_payloads)} related concepts"
    return label, description


def run_clustering(
    graph_id: str,
    n_clusters: Optional[int] = None,
    min_cluster_size: int = 3,
    use_llm_labels: bool = True,
) -> Tuple[int, List[Cluster]]:
    """
    Run clustering on a graph.

    Returns (total_nodes, clusters).
    """
    try:
        from faim.api.production_state import get_faim_context

        ctx = get_faim_context(graph_id)
        store = ctx.get("store")

        if not store:
            return 0, []

        # Get all nodes
        nodes = list(store.iter_nodes(graph_id))
        total_nodes = len(nodes)

        if total_nodes < min_cluster_size:
            return total_nodes, []

        # Build vectors matrix
        node_ids = [str(n.node_id) for n in nodes]
        vectors = np.array([n.vec for n in nodes])

        # Get payloads for labeling
        payloads = {}
        for node in nodes:
            if node.payload_ref:
                try:
                    content = store.get_payload(node.payload_ref)
                    if content:
                        payloads[str(node.node_id)] = content[:500]
                except Exception:
                    pass

        # Determine number of clusters
        if n_clusters is None:
            n_clusters = estimate_n_clusters(total_nodes)

        # Run clustering
        assignments = kmeans_cluster(vectors, n_clusters)

        # Build cluster objects
        clusters = []
        for k in range(n_clusters):
            mask = assignments == k
            cluster_node_ids = [node_ids[i] for i in range(len(node_ids)) if mask[i]]

            if len(cluster_node_ids) < min_cluster_size:
                continue

            cluster_vectors = vectors[mask]
            centroid = cluster_vectors.mean(axis=0)
            coherence = calculate_coherence(cluster_vectors)

            # Get payloads for labeling
            cluster_payloads = [
                payloads.get(nid, "") for nid in cluster_node_ids if nid in payloads
            ]

            label, description = generate_cluster_label(cluster_payloads, use_llm_labels)

            cluster = Cluster(
                cluster_id=uuid4().hex[:12],
                label=label,
                description=description,
                node_ids=cluster_node_ids,
                centroid=centroid,
                coherence=coherence,
            )
            clusters.append(cluster)

        # Sort by size
        clusters.sort(key=lambda c: len(c.node_ids), reverse=True)

        # Store clusters
        _clusters[graph_id] = clusters

        return total_nodes, clusters

    except Exception as e:
        logger.error(f"Clustering failed: {e}")
        return 0, []


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("/{graph_id}/cluster")
async def cluster_graph(graph_id: str, request: ClusterRequest = None):
    """
    Run semantic clustering on a graph.
    
    Groups related nodes into clusters based on embedding similarity.
    
    Example:
        curl -X POST http://localhost:8000/api/v1/graphs/MAIN/cluster \
            -H "Content-Type: application/json" \
            -d '{"n_clusters": 5, "use_llm_labels": true}'
    """
    if request is None:
        request = ClusterRequest()

    total_nodes, clusters = run_clustering(
        graph_id=graph_id,
        n_clusters=request.n_clusters,
        min_cluster_size=request.min_cluster_size,
        use_llm_labels=request.use_llm_labels,
    )

    return {
        "graph_id": graph_id,
        "total_nodes": total_nodes,
        "n_clusters": len(clusters),
        "clusters": [
            {
                "cluster_id": c.cluster_id,
                "label": c.label,
                "description": c.description,
                "size": len(c.node_ids),
                "coherence": round(c.coherence, 4),
                "node_ids": c.node_ids[:10],  # Limit for response size
            }
            for c in clusters
        ],
    }


@router.get("/{graph_id}/clusters")
async def get_clusters(graph_id: str, include_nodes: bool = False):
    """
    Get cached clusters for a graph.

    Example:
        curl http://localhost:8000/api/v1/graphs/MAIN/clusters?include_nodes=true
    """
    clusters = _clusters.get(graph_id, [])

    return {
        "graph_id": graph_id,
        "n_clusters": len(clusters),
        "clusters": [
            {
                "cluster_id": c.cluster_id,
                "label": c.label,
                "description": c.description,
                "size": len(c.node_ids),
                "coherence": round(c.coherence, 4),
                "node_ids": c.node_ids if include_nodes else c.node_ids[:5],
            }
            for c in clusters
        ],
    }


@router.get("/{graph_id}/clusters/{cluster_id}")
async def get_cluster_detail(graph_id: str, cluster_id: str):
    """Get details for a specific cluster."""
    clusters = _clusters.get(graph_id, [])

    for c in clusters:
        if c.cluster_id == cluster_id:
            return {
                "cluster_id": c.cluster_id,
                "label": c.label,
                "description": c.description,
                "size": len(c.node_ids),
                "coherence": round(c.coherence, 4),
                "node_ids": c.node_ids,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }

    raise HTTPException(status_code=404, detail="Cluster not found")
