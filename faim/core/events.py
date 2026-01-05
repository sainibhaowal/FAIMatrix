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
