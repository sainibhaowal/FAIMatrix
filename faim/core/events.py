"""
FAIM Core Event Bus
Decouples the Engine from the API layer for real-time updates.
"""

from typing import Callable, List

# Simple in-memory event subscribers
_subscribers: List[Callable[[str, str, float], None]] = []


def subscribe_node_created(callback: Callable[[str, str, float], None]) -> None:
    """Register a callback for node creation events."""
    _subscribers.append(callback)


def emit_node_created(graph_id: str, node_id: str, timestamp: float) -> None:
    """Emit a node creation event to all subscribers."""
    for callback in _subscribers:
        try:
            callback(graph_id, node_id, timestamp)
        except Exception:
            # Prevent subscriber errors from crashing the core engine
            pass


# Evolution Events
_evolution_subscribers: List[Callable[[str, dict], None]] = []


def subscribe_evolution_event(callback: Callable[[str, dict], None]) -> None:
    _evolution_subscribers.append(callback)


def emit_evolution_event(graph_id: str, event_type: str, data: dict) -> None:
    payload = {"type": event_type, **data}
    for callback in _evolution_subscribers:
        try:
            callback(graph_id, payload)
        except Exception:
            pass


# Invention Events
_invention_subscribers: List[Callable[[str, dict], None]] = []


def subscribe_invention_event(callback: Callable[[str, dict], None]) -> None:
    _invention_subscribers.append(callback)


def emit_invention_event(graph_id: str, event_type: str, data: dict) -> None:
    payload = {"type": event_type, **data}
    for callback in _invention_subscribers:
        try:
            callback(graph_id, payload)
        except Exception:
            pass


# =============================================================================
# Analytics Events (Clustering, Inference, Insights)
# =============================================================================

_cluster_subscribers: List[Callable[[str, list], None]] = []
_inference_subscribers: List[Callable[[str, list], None]] = []
_insight_subscribers: List[Callable[[str, list], None]] = []


def subscribe_cluster_updated(callback: Callable[[str, list], None]) -> None:
    """Register callback for cluster update events."""
    _cluster_subscribers.append(callback)


def emit_cluster_updated(graph_id: str, clusters: list) -> None:
    """Emit cluster update event to all subscribers.

    clusters = [{"cluster_id": "...", "label": "...", "color": "#...", "node_ids": [...]}]
    """
    for callback in _cluster_subscribers:
        try:
            callback(graph_id, clusters)
        except Exception:
            pass


def subscribe_inference_found(callback: Callable[[str, list], None]) -> None:
    """Register callback for inference events."""
    _inference_subscribers.append(callback)


def emit_inference_found(graph_id: str, inferences: list) -> None:
    """Emit inference event to all subscribers.

    inferences = [{"source": "...", "target": "...", "similarity": 0.85}]
    """
    for callback in _inference_subscribers:
        try:
            callback(graph_id, inferences)
        except Exception:
            pass


def subscribe_insight_discovered(callback: Callable[[str, list], None]) -> None:
    """Register callback for insight events."""
    _insight_subscribers.append(callback)


def emit_insight_discovered(graph_id: str, insights: list) -> None:
    """Emit insight event to all subscribers.

    insights = [{"insight_id": "...", "title": "...", "surprise_score": 0.8}]
    """
    for callback in _insight_subscribers:
        try:
            callback(graph_id, insights)
        except Exception:
            pass
