"""
FAIM Self-Inventing Concepts - AGI Feature #6

NEW MODULE - Does not modify any existing code.
Automatically synthesizes NEW concepts from existing knowledge.

Features:
- LLM-powered concept synthesis
- Creates new nodes with inheritance from sources
- Tracks provenance of invented concepts

Usage:
    POST /api/v1/graphs/{graph_id}/invent  - Run invention cycle
    GET /api/v1/graphs/{graph_id}/inventions  - Get invented concepts
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from faim.core.events import emit_invention_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graphs", tags=["Self-Invention"])


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class InventedConcept:
    """A newly invented concept synthesized from existing knowledge."""

    concept_id: str
    title: str
    description: str
    content: str
    source_nodes: List[str] = field(default_factory=list)
    confidence: float = 0.0
    node_id: Optional[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class InventionRequest(BaseModel):
    """Request to run invention."""

    max_inventions: int = 5
    min_sources: int = 2  # Minimum source nodes to combine
    max_sources: int = 4  # Maximum source nodes to combine
    create_nodes: bool = True  # Create actual nodes in graph


# In-memory invention storage
_inventions: Dict[str, List[InventedConcept]] = {}


# =============================================================================
# Invention Engine
# =============================================================================


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def find_synthesis_candidates(
    nodes: List[dict],
    payloads: Dict[str, str],
    n_groups: int = 10,
    group_size: int = 3,
) -> List[List[dict]]:
    """
    Find groups of nodes that could be synthesized into new concepts.

    Looks for nodes that are:
    - Related but not identical (similarity 0.4-0.8)
    - From different contexts/documents
    """
    if len(nodes) < 2:
        return []

    # Find pairs with moderate similarity (related but different)
    candidates = []

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            sim = cosine_similarity(nodes[i]["vec"], nodes[j]["vec"])

            # Sweet spot: related but not duplicate
            if 0.4 <= sim <= 0.8:
                # Different documents preferred
                is_cross_doc = nodes[i].get("doc") != nodes[j].get("doc")
                score = sim + (0.2 if is_cross_doc else 0)

                candidates.append(
                    {
                        "pair": [nodes[i], nodes[j]],
                        "score": score,
                    }
                )

    # Sort by score
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Build groups from top candidates
    groups = []
    used_ids = set()

    for cand in candidates[: n_groups * 2]:
        pair = cand["pair"]
        ids = [n["id"] for n in pair]

        # Skip if already used
        if any(id in used_ids for id in ids):
            continue

        # Try to extend to group_size
        group = list(pair)
        group_vecs = [n["vec"] for n in pair]

        for node in nodes:
            if len(group) >= group_size:
                break
            if node["id"] in used_ids or node["id"] in ids:
                continue

            # Check if node fits with group
            avg_sim = np.mean([cosine_similarity(node["vec"], v) for v in group_vecs])

            if 0.3 <= avg_sim <= 0.7:
                group.append(node)
                group_vecs.append(node["vec"])

        if len(group) >= 2:
            groups.append(group)
            for n in group:
                used_ids.add(n["id"])

        if len(groups) >= n_groups:
            break

    return groups


def synthesize_concept(
    source_nodes: List[dict],
    payloads: Dict[str, str],
) -> Tuple[str, str, str, float]:
    """
    Synthesize a new concept from source nodes using LLM.

    Returns (title, description, content, confidence).
    """
    # Get source content
    contents = []
    for node in source_nodes:
        nid = node["id"]
        if nid in payloads:
            contents.append(payloads[nid][:500])

    if not contents:
        return "", "", "", 0.0

    try:
        import os

        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return _fallback_synthesis(contents)

        client = Groq(api_key=api_key)

        source_text = "\n---\n".join(contents)

        prompt = f"""Analyze these {len(contents)} related knowledge fragments and synthesize a NEW insight or concept that combines their ideas in a novel way.

The new concept should:
1. Connect ideas that weren't explicitly connected before
2. Provide a useful abstraction or generalization
3. Be genuinely new (not just a summary)

Knowledge fragments:
{source_text}

Generate:
TITLE: <A concise 5-10 word title for the new concept>
DESCRIPTION: <One sentence describing what this concept represents>
CONTENT: <2-3 paragraphs explaining the synthesized concept in detail>
CONFIDENCE: <A number 0.0-1.0 indicating how confident you are in this synthesis>"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a knowledge synthesis AI that discovers new insights by combining existing knowledge.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0.7,
        )

        result = response.choices[0].message.content

        title = ""
        description = ""
        content = ""
        confidence = 0.5

        current_field = None
        content_lines = []

        for line in result.split("\n"):
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
                current_field = None
            elif line.startswith("DESCRIPTION:"):
                description = line.replace("DESCRIPTION:", "").strip()
                current_field = None
            elif line.startswith("CONTENT:"):
                current_field = "content"
                content_lines.append(line.replace("CONTENT:", "").strip())
            elif line.startswith("CONFIDENCE:"):
                try:
                    conf_str = line.replace("CONFIDENCE:", "").strip()
                    confidence = float(conf_str)
                except Exception:
                    pass
                current_field = None
            elif current_field == "content":
                content_lines.append(line)

        content = "\n".join(content_lines).strip()

        return title, description, content, confidence

    except Exception as e:
        logger.warning(f"LLM synthesis failed: {e}")
        return _fallback_synthesis(contents)


def _fallback_synthesis(contents: List[str]) -> Tuple[str, str, str, float]:
    """Fallback synthesis without LLM."""
    title = "Synthesized Concept"
    description = f"Concept derived from {len(contents)} related ideas"
    content = "This concept connects the following ideas:\n\n"
    content += "\n\n".join(f"• {c[:200]}..." for c in contents)
    return title, description, content, 0.3


def run_invention(
    graph_id: str,
    max_inventions: int = 5,
    min_sources: int = 2,
    max_sources: int = 4,
    create_nodes: bool = True,
) -> List[InventedConcept]:
    """
    Run invention cycle on a graph.

    Returns list of invented concepts.
    """
    try:
        from faim.config.backends import get_faim_context

        ctx = get_faim_context(graph_id)
        store = ctx.get("store")
        engine = ctx.get("engine")

        if not store:
            return []

        emit_invention_event(str(graph_id), "INVENTION_STARTED", {"max": max_inventions, "min_sources": min_sources})

        # Get all nodes
        nodes_raw = list(store.iter_nodes(graph_id))

        if len(nodes_raw) < min_sources:
            return []

        # Build node data and payloads
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

        # Find synthesis candidates
        groups = find_synthesis_candidates(nodes, payloads, n_groups=max_inventions * 2, group_size=max_sources)

        inventions = []

        for group in groups[:max_inventions]:
            # Synthesize new concept
            title, description, content, confidence = synthesize_concept(group, payloads)

            if not title or not content:
                continue

            source_ids = [n["id"] for n in group]

            invention = InventedConcept(
                concept_id=uuid4().hex[:12],
                title=title,
                description=description,
                content=content,
                source_nodes=source_ids,
                confidence=confidence,
            )

            # Create actual node in graph
            if create_nodes and engine:
                try:
                    # Full payload with provenance
                    full_payload = "[INVENTED CONCEPT]\n\n"
                    full_payload += f"Title: {title}\n\n"
                    full_payload += f"Description: {description}\n\n"
                    full_payload += f"{content}\n\n"
                    full_payload += f"---\nSynthesized from: {', '.join(source_ids[:3])}"

                    node_id = engine.add_memory(
                        graph_id=graph_id,
                        payload=full_payload,
                    )
                    invention.node_id = str(node_id) if node_id else None

                except Exception as e:
                    logger.warning(f"Failed to create invention node: {e}")

            inventions.append(invention)

        # Store inventions
        if graph_id not in _inventions:
            _inventions[graph_id] = []
        _inventions[graph_id].extend(inventions)

        for inv in inventions:
            emit_invention_event(
                str(graph_id),
                "CONCEPT_INVENTED",
                {"title": inv.title, "confidence": inv.confidence, "node_id": inv.node_id},
            )

        return inventions

    except Exception as e:
        logger.error(f"Invention failed: {e}")
        return []

    finally:
        emit_invention_event(
            str(graph_id), "INVENTION_COMPLETED", {"count": len(inventions) if "inventions" in locals() else 0}
        )


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("/{graph_id}/invent")
async def invent_concepts(graph_id: str, request: InventionRequest = None):
    """
    Run self-invention to synthesize new concepts.
    
    Analyzes existing knowledge and creates new concepts that connect ideas
    in novel ways.
    
    Example:
        curl -X POST http://localhost:8000/api/v1/graphs/MAIN/invent \
            -H "Content-Type: application/json" \
            -d '{"max_inventions": 3, "create_nodes": true}'
    """
    if request is None:
        request = InventionRequest()

    inventions = run_invention(
        graph_id=graph_id,
        max_inventions=request.max_inventions,
        min_sources=request.min_sources,
        max_sources=request.max_sources,
        create_nodes=request.create_nodes,
    )

    return {
        "graph_id": graph_id,
        "inventions_created": len(inventions),
        "inventions": [
            {
                "concept_id": inv.concept_id,
                "title": inv.title,
                "description": inv.description,
                "content": inv.content[:500] + "..." if len(inv.content) > 500 else inv.content,
                "source_nodes": inv.source_nodes,
                "confidence": round(inv.confidence, 4),
                "node_id": inv.node_id,
            }
            for inv in inventions
        ],
    }


@router.get("/{graph_id}/inventions")
async def get_inventions(
    graph_id: str,
    min_confidence: float = 0.0,
    limit: int = 50,
):
    """
    Get previously invented concepts.

    Example:
        curl http://localhost:8000/api/v1/graphs/MAIN/inventions?min_confidence=0.5
    """
    inventions = _inventions.get(graph_id, [])

    # Filter by confidence
    if min_confidence > 0:
        inventions = [inv for inv in inventions if inv.confidence >= min_confidence]

    # Sort by confidence
    inventions.sort(key=lambda x: x.confidence, reverse=True)
    inventions = inventions[:limit]

    return {
        "graph_id": graph_id,
        "count": len(inventions),
        "inventions": [
            {
                "concept_id": inv.concept_id,
                "title": inv.title,
                "description": inv.description,
                "confidence": round(inv.confidence, 4),
                "source_nodes": inv.source_nodes,
                "node_id": inv.node_id,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            }
            for inv in inventions
        ],
    }


@router.get("/{graph_id}/inventions/{concept_id}")
async def get_invention_detail(graph_id: str, concept_id: str):
    """Get details of a specific invented concept."""
    inventions = _inventions.get(graph_id, [])

    for inv in inventions:
        if inv.concept_id == concept_id:
            return {
                "concept_id": inv.concept_id,
                "title": inv.title,
                "description": inv.description,
                "content": inv.content,
                "source_nodes": inv.source_nodes,
                "confidence": round(inv.confidence, 4),
                "node_id": inv.node_id,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            }

    raise HTTPException(status_code=404, detail="Invention not found")


# =============================================================================
# InventionScheduler - Built-in Autonomous Loop
# =============================================================================


class InventionScheduler:
    """
    Background scheduler for periodic self-invention.

    Similar to EvolutionScheduler, this runs autonomously without external watchers.
    When started, it will periodically run invention cycles for the specified graph.

    Usage:
        scheduler = InventionScheduler()
        scheduler.start_in_background(graph_id, interval_seconds=300)
        ...
        scheduler.stop()
    """

    def __init__(
        self,
        *,
        max_inventions: int = 3,
        min_sources: int = 2,
        max_sources: int = 4,
        create_nodes: bool = True,
    ) -> None:
        import threading

        self._max_inventions = max_inventions
        self._min_sources = min_sources
        self._max_sources = max_sources
        self._create_nodes = create_nodes
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def run_once(self, graph_id: str) -> List[InventedConcept]:
        """Run a single invention pass synchronously."""
        return run_invention(
            graph_id=graph_id,
            max_inventions=self._max_inventions,
            min_sources=self._min_sources,
            max_sources=self._max_sources,
            create_nodes=self._create_nodes,
        )

    def run_forever(self, graph_id: str, interval_seconds: float = 300.0) -> None:
        """
        Run invention in a blocking loop until stop() is called.

        Default interval is 5 minutes (300 seconds) since invention
        is more resource-intensive than evolution.
        """

        # Perform an immediate pass, then sleep between subsequent passes.
        self.run_once(graph_id)
        while not self._stop.wait(interval_seconds):
            try:
                inventions = self.run_once(graph_id)
                logger.info(f"[InventionScheduler] Created {len(inventions)} inventions for {graph_id}")
            except Exception as e:
                logger.error(f"[InventionScheduler] Error: {e}")

    def start_in_background(
        self,
        graph_id: str,
        interval_seconds: float = 300.0,
    ) -> "threading.Thread":
        """
        Spawn a daemon thread running run_forever.
        """
        import threading

        self._thread = threading.Thread(
            target=self.run_forever,
            args=(graph_id, interval_seconds),
            daemon=True,
        )
        self._thread.start()
        return self._thread

    def stop(self) -> None:
        """Signal the scheduler to stop."""
        self._stop.set()

    def join(self, timeout: Optional[float] = None) -> None:
        """Wait for the background thread to finish."""
        if self._thread is not None:
            self._thread.join(timeout=timeout)
