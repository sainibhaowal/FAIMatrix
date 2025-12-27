"""In-memory Fractal Inheritance Graph (FIG) utilities.

Minimal, deterministic in-memory graph used for P1.
Persistent storage and indices will be added later.
"""

from __future__ import annotations

from typing import Dict, Optional

from .types import GraphId, GraphState, NodeId, NodeRecord


class InMemoryGraphRegistry:
    """Registry managing GraphState objects keyed by GraphId."""

    def __init__(self) -> None:
        self._graphs: Dict[GraphId, GraphState] = {}

    def get_or_create(self, graph_id: GraphId) -> GraphState:
        if graph_id not in self._graphs:
            self._graphs[graph_id] = GraphState(graph_id=graph_id)
        return self._graphs[graph_id]

    def get(self, graph_id: GraphId) -> Optional[GraphState]:
        return self._graphs.get(graph_id)


def attach_child(parent: NodeRecord, child_id: NodeId) -> None:
    """Attach child_id to parent if not already present."""
    if child_id not in parent.children:
        parent.children.append(child_id)


def detach_child(parent: NodeRecord, child_id: NodeId) -> None:
    """Detach child_id from parent if present."""
    if child_id in parent.children:
        parent.children.remove(child_id)
