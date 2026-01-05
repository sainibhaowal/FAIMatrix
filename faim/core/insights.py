"""
FAIM Hidden Insights Discovery - AGI Feature #4

NEW MODULE - Does not modify any existing code.
Reveals non-obvious patterns and connections in the knowledge graph.

Features:
- Surprise score based on distance + similarity
- LLM-generated insight summaries
- Insight ranking and prioritization

Usage:
    GET /api/v1/graphs/{graph_id}/insights  - Get discovered insights
    POST /api/v1/graphs/{graph_id}/discover-insights  - Run discovery
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graphs", tags=["Insights"])


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class Insight:
    """A discovered insight or hidden connection."""

    insight_id: str
    title: str
    description: str
    insight_type: str  # "connection", "pattern", "anomaly"
    surprise_score: float  # 0-1, higher = more surprising
    related_nodes: List[str] = field(default_factory=list)
    evidence: str = ""
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class InsightRequest(BaseModel):
    """Request to discover insights."""

    max_insights: int = 20
    min_surprise: float = 0.3
    use_llm: bool = True


# In-memory insight storage
_insights: Dict[str, List[Insight]] = {}


# =============================================================================
# Insight Discovery Engine
# =============================================================================


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def calculate_surprise_score(
    similarity: float,
    graph_distance: int,
    is_cross_doc: bool,
) -> float:
    """
    Calculate surprise score for a connection.

    High surprise = high similarity BUT distant in graph OR different docs
    """
    # Base surprise from similarity (inverted - we want high sim to POTENTIALLY surprise)
    base = similarity

    # Boost for graph distance (far apart but similar = surprising)
    distance_boost = min(graph_distance / 5.0, 1.0)

    # Boost for cross-document connections
    cross_doc_boost = 0.3 if is_cross_doc else 0.0

    # Combine factors
    surprise = base * (1 + distance_boost + cross_doc_boost)

    # Normalize to 0-1
    return min(surprise, 1.0)


def find_surprising_connections(
    nodes: List[dict],
    top_k: int = 50,
    min_surprise: float = 0.3,
) -> List[Tuple[dict, dict, float]]:
    """
    Find surprising connections based on high similarity + high distance.

    Returns list of (node1, node2, surprise_score).
    """
    connections = []

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            n1 = nodes[i]
            n2 = nodes[j]

            # Calculate similarity
            sim = cosine_similarity(n1["vec"], n2["vec"])

            # Skip low similarity
            if sim < 0.5:
                continue

            # Estimate graph distance (simplified)
            is_cross_doc = n1.get("doc") != n2.get("doc")
            graph_distance = 3 if is_cross_doc else 1

            # Calculate surprise
            surprise = calculate_surprise_score(sim, graph_distance, is_cross_doc)

            if surprise >= min_surprise:
                connections.append((n1, n2, surprise))

    # Sort by surprise (highest first)
    connections.sort(key=lambda x: x[2], reverse=True)

    return connections[:top_k]


def find_anomalous_nodes(nodes: List[dict], top_k: int = 10) -> List[dict]:
    """
    Find nodes that are anomalous (very different from neighbors).
    """
    if len(nodes) < 3:
        return []

    # Calculate average similarity to all other nodes
    anomalies = []

    for i, node in enumerate(nodes):
        similarities = []
        for j, other in enumerate(nodes):
            if i != j:
                sim = cosine_similarity(node["vec"], other["vec"])
                similarities.append(sim)

        avg_sim = np.mean(similarities) if similarities else 0.5

        # Low average similarity = anomalous
        if avg_sim < 0.3:
            node["anomaly_score"] = 1 - avg_sim
            anomalies.append(node)

    # Sort by anomaly score
    anomalies.sort(key=lambda x: x.get("anomaly_score", 0), reverse=True)

    return anomalies[:top_k]


def generate_insight_summary(
    nodes: List[dict],
    insight_type: str,
    payloads: Dict[str, str],
    use_llm: bool = True,
) -> Tuple[str, str]:
    """
    Generate title and description for an insight.

    Returns (title, description).
    """
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
            import os

            from groq import Groq

            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                client = Groq(api_key=api_key)

                sample = "\n---\n".join(contents[:3])

                if insight_type == "connection":
                    prompt = f"These concepts from different documents are surprisingly similar. Generate a brief insight title (5-8 words) and one sentence explaining the hidden connection.\n\nContent:\n{sample}"
                elif insight_type == "anomaly":
                    prompt = f"This concept is very different from everything else. Generate a brief title (5-8 words) and one sentence explaining why it might be unique.\n\nContent:\n{sample}"
                else:
                    prompt = f"Generate a brief insight title (5-8 words) and one sentence description for this pattern.\n\nContent:\n{sample}"

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
        from faim.api.production_state import get_faim_context

        ctx = get_faim_context(graph_id)
        store = ctx.get("store")

        if not store:
            return []

        # Get all nodes
        nodes_raw = list(store.iter_nodes(graph_id))

        if len(nodes_raw) < 3:
            return []

        # Build node data
        nodes = []
        payloads = {}

        for node in nodes_raw:
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
        connections = find_surprising_connections(
            nodes, top_k=max_insights // 2, min_surprise=min_surprise
        )

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

        for node in anomalies:
            title, description = generate_insight_summary([node], "anomaly", payloads, use_llm)

            insight = Insight(
                insight_id=uuid4().hex[:12],
                title=title,
                description=description,
                insight_type="anomaly",
                surprise_score=node.get("anomaly_score", 0.5),
                related_nodes=[node["id"]],
                evidence=f"Uniqueness: {node.get('anomaly_score', 0.5):.2%}",
            )
            insights.append(insight)

        # Sort by surprise score
        insights.sort(key=lambda x: x.surprise_score, reverse=True)
        insights = insights[:max_insights]

        # Store insights
        _insights[graph_id] = insights

        return insights

    except Exception as e:
        logger.error(f"Insight discovery failed: {e}")
        return []


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("/{graph_id}/discover-insights")
async def discover_graph_insights(graph_id: str, request: InsightRequest = None):
    """
    Discover hidden insights in a graph.
    
    Analyzes the knowledge graph to find surprising connections and patterns.
    
    Example:
        curl -X POST http://localhost:8000/api/v1/graphs/MAIN/discover-insights \
            -H "Content-Type: application/json" \
            -d '{"max_insights": 10, "min_surprise": 0.5}'
    """
    if request is None:
        request = InsightRequest()

    insights = discover_insights(
        graph_id=graph_id,
        max_insights=request.max_insights,
        min_surprise=request.min_surprise,
        use_llm=request.use_llm,
    )

    return {
        "graph_id": graph_id,
        "insights_found": len(insights),
        "insights": [
            {
                "insight_id": i.insight_id,
                "title": i.title,
                "description": i.description,
                "type": i.insight_type,
                "surprise_score": round(i.surprise_score, 4),
                "related_nodes": i.related_nodes,
                "evidence": i.evidence,
            }
            for i in insights
        ],
    }


@router.get("/{graph_id}/insights")
async def get_insights(
    graph_id: str,
    insight_type: Optional[str] = None,
    min_surprise: float = 0.0,
    limit: int = 50,
):
    """
    Get cached insights for a graph.

    Example:
        curl http://localhost:8000/api/v1/graphs/MAIN/insights?insight_type=connection
    """
    insights = _insights.get(graph_id, [])

    # Filter by type
    if insight_type:
        insights = [i for i in insights if i.insight_type == insight_type]

    # Filter by surprise
    if min_surprise > 0:
        insights = [i for i in insights if i.surprise_score >= min_surprise]

    # Limit
    insights = insights[:limit]

    return {
        "graph_id": graph_id,
        "count": len(insights),
        "insights": [
            {
                "insight_id": i.insight_id,
                "title": i.title,
                "description": i.description,
                "type": i.insight_type,
                "surprise_score": round(i.surprise_score, 4),
                "related_nodes": i.related_nodes,
                "evidence": i.evidence,
            }
            for i in insights
        ],
    }
