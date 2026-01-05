"""
FAIM Graph Filters - Topic, Date, and Relationship Filtering

NEW MODULE - Does not modify any existing code.
Provides filtering functions for FIG view exploration.

Usage:
    from faim.api.graph_filters import filter_snapshot, FilterOptions
    filtered = filter_snapshot(snapshot, FilterOptions(topic="AI", date_from=...))
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class FilterOptions:
    """Options for filtering graph snapshots."""

    # Topic/keyword filter (searches in node labels and payloads)
    topic: Optional[str] = None

    # Date range filter
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    # Relationship type filter (e.g., "parent", "child", "sibling")
    relationship_type: Optional[str] = None

    # Node kind filter (e.g., "document", "chunk", "concept")
    node_kind: Optional[str] = None

    # Minimum usage count filter (hide cold nodes)
    min_usage: int = 0

    # Maximum depth from root nodes
    max_depth: Optional[int] = None

    # Include connected nodes that don't match filters
    include_neighbors: bool = True

    # Limit results
    limit: int = 500


@dataclass
class FilterStats:
    """Statistics about the filtering operation."""

    total_nodes: int = 0
    filtered_nodes: int = 0
    total_links: int = 0
    filtered_links: int = 0
    topics_found: List[str] = field(default_factory=list)
    date_range: Optional[str] = None


def _extract_topics(text: str, max_topics: int = 5) -> List[str]:
    """
    Extract potential topics from text using simple keyword extraction.

    This is a lightweight approach that doesn't require external ML models.
    For production, you could plug in a proper NLP pipeline.
    """
    if not text:
        return []

    # Remove common words and extract significant terms
    stop_words = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "need",
        "dare",
        "ought",
        "used",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "under",
        "again",
        "further",
        "then",
        "once",
        "and",
        "but",
        "or",
        "nor",
        "so",
        "yet",
        "both",
        "either",
        "neither",
        "not",
        "only",
        "own",
        "same",
        "than",
        "too",
        "very",
        "just",
        "also",
        "now",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "every",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "any",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "they",
        "them",
        "their",
        "i",
        "me",
        "my",
        "we",
        "us",
        "our",
        "you",
        "your",
        "he",
        "him",
        "his",
        "she",
        "her",
        "what",
        "which",
        "who",
        "whom",
        "whose",
    }

    # Extract words (alphanumeric, 3+ chars)
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

    # Filter and count
    word_counts: Dict[str, int] = {}
    for word in words:
        if word not in stop_words:
            word_counts[word] = word_counts.get(word, 0) + 1

    # Sort by frequency and return top N
    sorted_words = sorted(word_counts.items(), key=lambda x: -x[1])
    return [word for word, _ in sorted_words[:max_topics]]


def _parse_node_timestamp(node: Dict[str, Any]) -> Optional[datetime]:
    """Extract timestamp from node metadata."""
    # Try common timestamp fields
    for field_name in ["created_at", "timestamp", "date", "created", "ts"]:
        value = node.get(field_name) or node.get("meta", {}).get(field_name)
        if value:
            try:
                if isinstance(value, datetime):
                    return value
                if isinstance(value, (int, float)):
                    return datetime.fromtimestamp(value)
                if isinstance(value, str):
                    # Try ISO format first
                    try:
                        return datetime.fromisoformat(value.replace("Z", "+00:00"))
                    except ValueError:
                        pass
                    # Try common formats
                    for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d"]:
                        try:
                            return datetime.strptime(value, fmt)
                        except ValueError:
                            continue
            except Exception:
                continue
    return None


def _get_node_label(node: Dict[str, Any]) -> str:
    """Extract label/text from node."""
    for field_name in ["label", "text", "payload", "content", "name", "title"]:
        value = node.get(field_name)
        if value and isinstance(value, str):
            return value
    return ""


def _get_node_kind(node: Dict[str, Any]) -> str:
    """Extract node kind/type."""
    for field_name in ["kind", "type", "node_type", "category"]:
        value = node.get(field_name) or node.get("meta", {}).get(field_name)
        if value and isinstance(value, str):
            return value.lower()
    return "unknown"


def _get_node_usage(node: Dict[str, Any]) -> int:
    """Extract usage count from node."""
    for field_name in ["use_count", "usage", "hits", "access_count"]:
        value = node.get(field_name) or node.get("meta", {}).get(field_name)
        if value is not None:
            try:
                return int(value)
            except (ValueError, TypeError):
                continue
    return 0


def _matches_topic(node: Dict[str, Any], topic: str) -> bool:
    """Check if node matches topic filter."""
    topic_lower = topic.lower()
    label = _get_node_label(node).lower()

    # Direct substring match
    if topic_lower in label:
        return True

    # Check metadata fields
    meta = node.get("meta", {})
    for _key, value in meta.items():
        if isinstance(value, str) and topic_lower in value.lower():
            return True
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and topic_lower in item.lower():
                    return True

    return False


def filter_nodes(
    nodes: List[Dict[str, Any]],
    options: FilterOptions,
) -> tuple[List[Dict[str, Any]], FilterStats]:
    """
    Filter nodes based on FilterOptions.

    Returns filtered nodes and statistics.
    """
    stats = FilterStats(total_nodes=len(nodes))

    if not nodes:
        return [], stats

    filtered: List[Dict[str, Any]] = []
    matched_ids: Set[str] = set()
    all_topics: List[str] = []
    min_date: Optional[datetime] = None
    max_date: Optional[datetime] = None

    for node in nodes:
        node_id = node.get("id", "")

        # Topic filter
        if options.topic and not _matches_topic(node, options.topic):
            continue

        # Date range filter
        if options.date_from or options.date_to:
            node_date = _parse_node_timestamp(node)
            if node_date:
                if min_date is None or node_date < min_date:
                    min_date = node_date
                if max_date is None or node_date > max_date:
                    max_date = node_date

                if options.date_from and node_date < options.date_from:
                    continue
                if options.date_to and node_date > options.date_to:
                    continue

        # Node kind filter
        if options.node_kind:
            if _get_node_kind(node) != options.node_kind.lower():
                continue

        # Usage filter
        if options.min_usage > 0:
            if _get_node_usage(node) < options.min_usage:
                continue

        # Node passed all filters
        filtered.append(node)
        matched_ids.add(node_id)

        # Extract topics for stats
        label = _get_node_label(node)
        topics = _extract_topics(label, max_topics=3)
        all_topics.extend(topics)

        # Apply limit
        if len(filtered) >= options.limit:
            break

    # Collect topic stats (most common)
    topic_counts: Dict[str, int] = {}
    for t in all_topics:
        topic_counts[t] = topic_counts.get(t, 0) + 1
    stats.topics_found = [t for t, _ in sorted(topic_counts.items(), key=lambda x: -x[1])[:10]]

    # Date range stats
    if min_date and max_date:
        stats.date_range = f"{min_date.isoformat()} to {max_date.isoformat()}"

    stats.filtered_nodes = len(filtered)
    return filtered, stats


def filter_links(
    links: List[Dict[str, Any]],
    valid_node_ids: Set[str],
    options: FilterOptions,
) -> List[Dict[str, Any]]:
    """
    Filter links to only include those between valid nodes.

    Also applies relationship type filter if specified.
    """
    filtered: List[Dict[str, Any]] = []

    for link in links:
        source = link.get("source", "")
        target = link.get("target", "")

        # Both endpoints must be in valid nodes
        if source not in valid_node_ids or target not in valid_node_ids:
            continue

        # Relationship type filter
        if options.relationship_type:
            link_type = link.get("type", "") or link.get("relationship", "") or link.get("kind", "")
            if link_type.lower() != options.relationship_type.lower():
                continue

        filtered.append(link)

    return filtered


def filter_snapshot(
    snapshot: Dict[str, Any],
    options: FilterOptions,
) -> Dict[str, Any]:
    """
    Filter a complete graph snapshot.

    Args:
        snapshot: Graph snapshot with 'nodes', 'links', 'meta' keys
        options: Filtering options

    Returns:
        Filtered snapshot with same structure plus 'filter_stats' key
    """
    nodes = snapshot.get("nodes", [])
    links = snapshot.get("links", [])
    meta = snapshot.get("meta", {}).copy()

    # Filter nodes
    filtered_nodes, stats = filter_nodes(nodes, options)

    # Get valid node IDs
    valid_ids = {n.get("id", "") for n in filtered_nodes}

    # Filter links
    filtered_links = filter_links(links, valid_ids, options)

    stats.total_links = len(links)
    stats.filtered_links = len(filtered_links)

    # Build result
    result = {
        "graph_id": snapshot.get("graph_id", ""),
        "nodes": filtered_nodes,
        "links": filtered_links,
        "meta": meta,
        "filter_stats": {
            "total_nodes": stats.total_nodes,
            "filtered_nodes": stats.filtered_nodes,
            "total_links": stats.total_links,
            "filtered_links": stats.filtered_links,
            "topics_found": stats.topics_found,
            "date_range": stats.date_range,
            "filter_applied": {
                "topic": options.topic,
                "date_from": options.date_from.isoformat() if options.date_from else None,
                "date_to": options.date_to.isoformat() if options.date_to else None,
                "relationship_type": options.relationship_type,
                "node_kind": options.node_kind,
                "min_usage": options.min_usage,
            },
        },
    }

    return result


# =============================================================================
# FastAPI Endpoint Extension
# =============================================================================

from fastapi import APIRouter, Depends, Query

from faim.api.auth import allow_dev_mode

router = APIRouter(prefix="/graphs", tags=["Graph Filters"])


@router.get("/{graph_id}/filtered")
async def get_filtered_snapshot(
    graph_id: str,
    topic: Optional[str] = Query(None, description="Filter by topic/keyword"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    relationship: Optional[str] = Query(None, description="Filter by relationship type"),
    kind: Optional[str] = Query(None, description="Filter by node kind"),
    min_usage: int = Query(0, description="Minimum usage count"),
    limit: int = Query(500, description="Maximum nodes to return"),
    _=Depends(allow_dev_mode),
):
    """
    Get a filtered graph snapshot.

    Filters nodes by topic, date range, relationship type, node kind, and usage.
    Returns both the filtered snapshot and statistics about what was filtered.

    Example:
        /api/v1/graphs/my-graph/filtered?topic=machine+learning&min_usage=2
    """
    # Parse dates
    parsed_date_from = None
    parsed_date_to = None

    if date_from:
        try:
            parsed_date_from = datetime.fromisoformat(date_from)
        except ValueError:
            pass

    if date_to:
        try:
            parsed_date_to = datetime.fromisoformat(date_to)
        except ValueError:
            pass

    options = FilterOptions(
        topic=topic,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
        relationship_type=relationship,
        node_kind=kind,
        min_usage=min_usage,
        limit=limit,
    )

    # Get the base snapshot using existing infrastructure
    # Import here to avoid circular imports
    try:
        from faim.api.graphs import _build_snapshot

        snapshot = _build_snapshot(graph_id)
    except ImportError:
        # Fallback: build manually from store
        try:
            from faim.api.production_state import get_store

            store = get_store()
        except ImportError:
            from faim.api import state as S

            store = getattr(S, "STORE", None)

        if store is None:
            return {
                "error": "Store not available",
                "graph_id": graph_id,
                "nodes": [],
                "links": [],
            }

        # Build minimal snapshot
        nodes = []
        for node in store.iter_nodes(graph_id):
            nodes.append(
                {
                    "id": node.id,
                    "label": node.payload_ref[:50] if node.payload_ref else "",
                    "use_count": node.use_count,
                    "created_at": node.created_at,
                }
            )

        snapshot = {
            "graph_id": graph_id,
            "nodes": nodes,
            "links": [],
            "meta": {},
        }

    # Apply filters
    result = filter_snapshot(snapshot, options)

    return result


@router.get("/{graph_id}/topics")
async def get_graph_topics(
    graph_id: str,
    limit: int = Query(20, description="Maximum topics to return"),
    _=Depends(allow_dev_mode),
):
    """
    Extract and return the most common topics in a graph.

    Useful for building topic filter dropdowns in the UI.
    """
    try:
        from faim.api.graphs import _build_snapshot

        snapshot = _build_snapshot(graph_id)
    except ImportError:
        return {"graph_id": graph_id, "topics": [], "error": "Could not load snapshot"}

    nodes = snapshot.get("nodes", [])

    all_topics: List[str] = []
    for node in nodes:
        label = _get_node_label(node)
        topics = _extract_topics(label, max_topics=5)
        all_topics.extend(topics)

    # Count and sort
    topic_counts: Dict[str, int] = {}
    for t in all_topics:
        topic_counts[t] = topic_counts.get(t, 0) + 1

    sorted_topics = sorted(topic_counts.items(), key=lambda x: -x[1])[:limit]

    return {
        "graph_id": graph_id,
        "topics": [{"topic": t, "count": c} for t, c in sorted_topics],
        "total_nodes": len(nodes),
    }
