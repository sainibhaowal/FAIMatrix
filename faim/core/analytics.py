# =============================================================================
# FAIM Core Analytics - Automatic Clustering, Inference, Insights
# =============================================================================
# File: faim/core/analytics.py
#
# PURPOSE
#   - Real-time analytics that run automatically during Engine operation
#   - Provides clustering (topic grouping), inference (similarity connections),
#     and insights (surprising discoveries)
#   - Emits events via SSE for UI visualization
#
# USAGE
#   Analytics runs automatically via AnalyticsScheduler wired to Engine.
#   UI receives: cluster_updated, inference_found, insight_discovered events.
# =============================================================================

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np

if TYPE_CHECKING:
    from faim.data.storage.store import FAIMStore

logger = logging.getLogger(__name__)


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class Cluster:
    """A semantic cluster of related nodes."""

    cluster_id: str
    label: str
    description: str
    color: str
    node_ids: List[str] = field(default_factory=list)
    centroid: Optional[np.ndarray] = None
    coherence: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InferenceLink:
    """A discovered connection between nodes."""

    link_id: str
    source_node_id: str
    target_node_id: str
    similarity: float
    source_doc: Optional[str] = None
    target_doc: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Insight:
    """A discovered insight or hidden connection."""

    insight_id: str
    title: str
    description: str
    insight_type: str  # "connection", "pattern", "anomaly"
    surprise_score: float
    related_nodes: List[str] = field(default_factory=list)
    evidence: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# Cluster Colors
# =============================================================================

CLUSTER_COLORS = [
    "#3b82f6",  # Blue
    "#22c55e",  # Green
    "#f97316",  # Orange
    "#a855f7",  # Purple
    "#ec4899",  # Pink
    "#14b8a6",  # Teal
    "#eab308",  # Yellow
    "#ef4444",  # Red
    "#6366f1",  # Indigo
    "#84cc16",  # Lime
    "#06b6d4",  # Cyan
    "#f43f5e",  # Rose
]


def get_cluster_color(index: int) -> str:
    """Get color for cluster by index."""
    return CLUSTER_COLORS[index % len(CLUSTER_COLORS)]


# =============================================================================
# Math Utilities
# =============================================================================


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


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


# =============================================================================
# Clustering Engine
# =============================================================================


def kmeans_cluster(
    vectors: np.ndarray,
    n_clusters: int,
    max_iters: int = 100,
) -> np.ndarray:
    """
    K-means clustering algorithm.

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
    """Estimate optimal number of clusters based on sample count."""
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


def generate_cluster_label(node_payloads: List[str], use_llm: bool = True) -> Tuple[str, str]:
    """
    Generate a label and description for a cluster.

    Returns (label, description).
    """
    if not node_payloads:
        return "Empty Cluster", "No content"

    # Simple keyword extraction (fallback)
    all_text = " ".join(node_payloads[:5])
    words = all_text.lower().split()

    # Find common words (simple approach)
    word_counts: Dict[str, int] = {}
    for word in words:
        if len(word) > 4:  # Skip short words
            word_counts[word] = word_counts.get(word, 0) + 1

    top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    label = " ".join(w[0].title() for w in top_words) if top_words else "Misc"

    if use_llm:
        try:
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
                            "content": "Generate a short 2-3 word label and one sentence description for this cluster. Format: LABEL: <label>\nDESCRIPTION: <description>",
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
    store: "FAIMStore",
    graph_id: str,
    n_clusters: Optional[int] = None,
    min_cluster_size: int = 3,
    use_llm_labels: bool = True,
) -> List[Cluster]:
    """
    Run clustering on a graph.

    Returns list of Cluster objects.
    """
    try:
        # Get all nodes
        nodes = list(store.iter_nodes(graph_id))
        total_nodes = len(nodes)

        if total_nodes < min_cluster_size:
            return []

        # Build vectors matrix
        node_ids = [str(n.node_id) for n in nodes]
        vectors = np.array([n.vec for n in nodes if n.vec is not None])

        if len(vectors) < min_cluster_size:
            return []

        # Get payloads for labeling
        payloads: Dict[str, str] = {}
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

        # Run K-means clustering
        assignments = kmeans_cluster(vectors, n_clusters)

        # Build cluster objects
        clusters = []
        for k in range(n_clusters):
            mask = assignments == k
            cluster_node_ids = [node_ids[i] for i in range(len(node_ids)) if i < len(mask) and mask[i]]

            if len(cluster_node_ids) < min_cluster_size:
                continue

            cluster_vectors = vectors[mask]
            centroid = cluster_vectors.mean(axis=0)
            coherence = calculate_coherence(cluster_vectors)

            # Get payloads for labeling
            cluster_payloads = [payloads.get(nid, "") for nid in cluster_node_ids if nid in payloads]

            label, description = generate_cluster_label(cluster_payloads, use_llm_labels)

            cluster = Cluster(
                cluster_id=uuid4().hex[:12],
                label=label,
                description=description,
                color=get_cluster_color(k),
                node_ids=cluster_node_ids,
                centroid=centroid,
                coherence=coherence,
            )
            clusters.append(cluster)

        # Sort by size
        clusters.sort(key=lambda c: len(c.node_ids), reverse=True)

        logger.info(f"Clustering complete: {len(clusters)} clusters for graph {graph_id}")
        return clusters

    except Exception as e:
        logger.error(f"Clustering failed for graph {graph_id}: {e}")
        return []


# =============================================================================
# Inference Engine
# =============================================================================


def get_document_source(node_record: Any) -> Optional[str]:
    """Extract document source from node metadata."""
    if hasattr(node_record, "payload_ref") and node_record.payload_ref:
        return str(node_record.payload_ref)[:16]
    return None


def run_inference(
    store: "FAIMStore",
    graph_id: str,
    min_similarity: float = 0.75,
    max_results: int = 50,
    exclude_same_doc: bool = True,
) -> List[InferenceLink]:
    """
    Run cross-document inference on a graph.

    Returns list of InferenceLink objects.
    """
    try:
        # Get all nodes
        nodes = list(store.iter_nodes(graph_id))
        total_nodes = len(nodes)

        if total_nodes < 2:
            return []

        # Build node list with vectors and docs
        node_data = []
        for node in nodes:
            if node.vec is not None:
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

        logger.info(f"Inference complete: {len(inferences)} connections for graph {graph_id}")
        return inferences

    except Exception as e:
        logger.error(f"Inference failed for graph {graph_id}: {e}")
        return []


# =============================================================================
# Insights Engine
# =============================================================================


def calculate_surprise_score(
    similarity: float,
    graph_distance: int,
    is_cross_doc: bool,
) -> float:
    """
    Calculate surprise score for a connection.

    High surprise = high similarity BUT distant in graph OR different docs.
    """
    base = similarity
    distance_boost = min(graph_distance / 5.0, 1.0)
    cross_doc_boost = 0.3 if is_cross_doc else 0.0
    surprise = base * (1 + distance_boost + cross_doc_boost)
    return min(surprise, 1.0)


def find_surprising_connections(
    nodes: List[dict],
    top_k: int = 50,
    min_surprise: float = 0.3,
) -> List[Tuple[dict, dict, float]]:
    """
    Find surprising connections based on high similarity + high distance.
    """
    connections = []

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            n1 = nodes[i]
            n2 = nodes[j]

            sim = cosine_similarity(n1["vec"], n2["vec"])

            if sim < 0.5:
                continue

            is_cross_doc = n1.get("doc") != n2.get("doc")
            graph_distance = 3 if is_cross_doc else 1
            surprise = calculate_surprise_score(sim, graph_distance, is_cross_doc)

            if surprise >= min_surprise:
                connections.append((n1, n2, surprise))

    connections.sort(key=lambda x: x[2], reverse=True)
    return connections[:top_k]


def find_anomalous_nodes(nodes: List[dict], top_k: int = 10) -> List[dict]:
    """Find nodes that are anomalous (very different from neighbors)."""
    if len(nodes) < 3:
        return []

    anomalies = []

    for i, node in enumerate(nodes):
        similarities = []
        for j, other in enumerate(nodes):
            if i != j:
                sim = cosine_similarity(node["vec"], other["vec"])
                similarities.append(sim)

        avg_sim = np.mean(similarities) if similarities else 0.5

        if avg_sim < 0.3:
            node["anomaly_score"] = 1 - avg_sim
            anomalies.append(node)

    anomalies.sort(key=lambda x: x.get("anomaly_score", 0), reverse=True)
    return anomalies[:top_k]


def generate_insight_summary(
    nodes: List[dict],
    insight_type: str,
    payloads: Dict[str, str],
    use_llm: bool = True,
) -> Tuple[str, str]:
    """Generate title and description for an insight."""
    node_ids = [n["id"] for n in nodes]
    contents = [payloads.get(nid, "")[:200] for nid in node_ids if nid in payloads]

    # Default fallback
    if insight_type == "connection":
        title = "Hidden Connection Discovered"
        description = f"Found unexpected similarity between {len(nodes)} concepts"
    elif insight_type == "anomaly":
        title = "Anomalous Concept Detected"
        description = "This concept stands apart from the rest of your knowledge"
    else:
        title = "Pattern Identified"
        description = f"Identified pattern across {len(nodes)} nodes"

    if use_llm and contents:
        try:
            from groq import Groq

            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                client = Groq(api_key=api_key)

                sample = "\n---\n".join(contents[:3])

                if insight_type == "connection":
                    prompt = f"These concepts are surprisingly similar. Generate a brief insight title (5-8 words) and one sentence explaining the hidden connection.\n\nContent:\n{sample}"
                elif insight_type == "anomaly":
                    prompt = f"This concept is very different from everything else. Generate a brief title (5-8 words) and one sentence explaining why.\n\nContent:\n{sample}"
                else:
                    prompt = f"Generate a brief insight title (5-8 words) and one sentence description.\n\nContent:\n{sample}"

                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {
                            "role": "system",
                            "content": "Generate insights. Format: TITLE: <title>\nDESCRIPTION: <description>",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=150,
                    temperature=0.5,
                )

                result = response.choices[0].message.content

                for line in result.split("\n"):
                    if line.startswith("TITLE:"):
                        title = line.replace("TITLE:", "").strip()
                    elif line.startswith("DESCRIPTION:"):
                        description = line.replace("DESCRIPTION:", "").strip()

        except Exception as e:
            logger.warning(f"LLM insight generation failed: {e}")

    return title, description


def discover_insights(
    store: "FAIMStore",
    graph_id: str,
    max_insights: int = 20,
    min_surprise: float = 0.3,
    use_llm: bool = True,
) -> List[Insight]:
    """
    Discover insights in a graph.

    Returns list of Insight objects.
    """
    try:
        nodes_raw = list(store.iter_nodes(graph_id))

        if len(nodes_raw) < 3:
            return []

        # Build node data
        nodes: List[Dict[str, Any]] = []
        payloads: Dict[str, str] = {}

        for node in nodes_raw:
            if node.vec is not None:
                node_data = {
                    "id": str(node.node_id),
                    "vec": node.vec,
                    "doc": str(node.payload_ref)[:16] if node.payload_ref else None,
                }
                nodes.append(node_data)

                if node.payload_ref:
                    try:
                        content = store.get_payload(node.payload_ref)
                        if content:
                            payloads[str(node.node_id)] = content
                    except Exception:
                        pass

        insights = []

        # Find surprising connections
        connections = find_surprising_connections(nodes, top_k=max_insights // 2, min_surprise=min_surprise)

        for n1, n2, surprise in connections:
            title, description = generate_insight_summary([n1, n2], "connection", payloads, use_llm)

            insight = Insight(
                insight_id=uuid4().hex[:12],
                title=title,
                description=description,
                insight_type="connection",
                surprise_score=surprise,
                related_nodes=[n1["id"], n2["id"]],
                evidence=f"Similarity: {cosine_similarity(n1['vec'], n2['vec']):.2%}",
            )
            insights.append(insight)

        # Find anomalies
        anomalies = find_anomalous_nodes(nodes, top_k=max_insights // 4)

        for anom_node in anomalies:
            title, description = generate_insight_summary([anom_node], "anomaly", payloads, use_llm)

            insight = Insight(
                insight_id=uuid4().hex[:12],
                title=title,
                description=description,
                insight_type="anomaly",
                surprise_score=anom_node.get("anomaly_score", 0.5),
                related_nodes=[anom_node["id"]],
                evidence=f"Uniqueness: {anom_node.get('anomaly_score', 0.5):.2%}",
            )
            insights.append(insight)

        # Sort by surprise score
        insights.sort(key=lambda x: x.surprise_score, reverse=True)
        insights = insights[:max_insights]

        logger.info(f"Insights discovery complete: {len(insights)} insights for graph {graph_id}")
        return insights

    except Exception as e:
        logger.error(f"Insight discovery failed for graph {graph_id}: {e}")
        return []


# =============================================================================
# Analytics Scheduler
# =============================================================================


class AnalyticsScheduler:
    """
    Background scheduler that runs analytics automatically.

    Runs clustering, inference, and insights discovery periodically
    and emits events for UI updates.
    """

    def __init__(
        self,
        store: "FAIMStore",
        emit_cluster_updated: Callable,
        emit_inference_found: Callable,
        emit_insight_discovered: Callable,
        interval_seconds: float = 30.0,
        min_nodes_for_trigger: int = 10,
    ):
        self._store = store
        self._emit_cluster_updated = emit_cluster_updated
        self._emit_inference_found = emit_inference_found
        self._emit_insight_discovered = emit_insight_discovered
        self._interval = interval_seconds
        self._min_nodes_trigger = min_nodes_for_trigger

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_node_count: Dict[str, int] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start background analytics thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="FAIM-Analytics")
        self._thread.start()
        logger.info("AnalyticsScheduler started")

    def stop(self) -> None:
        """Stop background analytics thread."""
        self._running = False
        logger.info("AnalyticsScheduler stopping")

    def trigger_now(self, graph_id: str) -> None:
        """Manually trigger analytics for a graph (called after add_memory)."""
        threading.Thread(
            target=self._run_analytics_for_graph, args=(graph_id,), daemon=True, name=f"FAIM-Analytics-{graph_id[:8]}"
        ).start()

    def notify_node_added(self, graph_id: str) -> None:
        """Called when a node is added. Triggers analytics if threshold reached."""
        with self._lock:
            count = self._last_node_count.get(graph_id, 0) + 1
            self._last_node_count[graph_id] = count

            # Trigger every N nodes
            if count % self._min_nodes_trigger == 0:
                self.trigger_now(graph_id)

    def _run_loop(self) -> None:
        """Main background loop."""
        while self._running:
            try:
                time.sleep(self._interval)
                self._check_all_graphs()
            except Exception as e:
                logger.exception(f"Analytics scheduler error: {e}")

    def _check_all_graphs(self) -> None:
        """Check all active graphs and run analytics if needed."""
        # Get active graphs from recent node counts
        with self._lock:
            graphs = list(self._last_node_count.keys())

        for graph_id in graphs:
            try:
                current_count = self._store.count_nodes(graph_id)
                last_count = self._last_node_count.get(graph_id, 0)

                # Only run if significant new nodes
                if current_count > last_count + self._min_nodes_trigger:
                    self._run_analytics_for_graph(graph_id)
                    with self._lock:
                        self._last_node_count[graph_id] = current_count
            except Exception as e:
                logger.warning(f"Error checking graph {graph_id}: {e}")

    def _run_analytics_for_graph(self, graph_id: str) -> None:
        """Run all analytics for a single graph."""
        logger.info(f"Running analytics for graph {graph_id}")

        try:
            # 1. Clustering
            clusters = run_clustering(
                store=self._store,
                graph_id=graph_id,
                n_clusters=None,
                min_cluster_size=3,
                use_llm_labels=bool(os.getenv("GROQ_API_KEY")),
            )
            if clusters:
                cluster_data = [
                    {
                        "cluster_id": c.cluster_id,
                        "label": c.label,
                        "description": c.description,
                        "color": c.color,
                        "node_ids": c.node_ids,
                        "coherence": c.coherence,
                    }
                    for c in clusters
                ]
                self._emit_cluster_updated(graph_id, cluster_data)

            # 2. Inference
            inferences = run_inference(
                store=self._store,
                graph_id=graph_id,
                min_similarity=0.75,
                max_results=50,
            )
            if inferences:
                inference_data = [
                    {
                        "link_id": inf.link_id,
                        "source": inf.source_node_id,
                        "target": inf.target_node_id,
                        "similarity": inf.similarity,
                    }
                    for inf in inferences
                ]
                self._emit_inference_found(graph_id, inference_data)

            # 3. Insights
            insights = discover_insights(
                store=self._store,
                graph_id=graph_id,
                max_insights=20,
                min_surprise=0.3,
                use_llm=bool(os.getenv("GROQ_API_KEY")),
            )
            if insights:
                insight_data = [
                    {
                        "insight_id": ins.insight_id,
                        "title": ins.title,
                        "description": ins.description,
                        "type": ins.insight_type,
                        "surprise_score": ins.surprise_score,
                        "related_nodes": ins.related_nodes,
                        "evidence": ins.evidence,
                    }
                    for ins in insights
                ]
                self._emit_insight_discovered(graph_id, insight_data)

        except Exception as e:
            logger.exception(f"Analytics failed for graph {graph_id}: {e}")
