"""Storage interfaces for FAIM.

Defines the abstract FAIMStore for NodeTable persistence.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from faim.core.types import GraphId, NodeId, NodeRecord, PayloadRef


class FAIMStore(ABC):
    """Abstract storage backend for NodeRecord persistence.

    Implementations must be deterministic and safe for long-running usage.
    """

    @abstractmethod
    def get_node(self, graph_id: GraphId, node_id: NodeId) -> NodeRecord | None:
        """Fetch a node by id, or None if missing."""

    @abstractmethod
    def upsert_node(self, node: NodeRecord) -> None:
        """Insert or update a node in the store."""

    @abstractmethod
    def delete_node(self, graph_id: GraphId, node_id: NodeId) -> None:
        """Delete a node from the store (hard delete)."""

    @abstractmethod
    def iter_nodes(self, graph_id: GraphId) -> Iterator[NodeRecord]:
        """Iterate over all nodes in a graph."""

    @abstractmethod
    def count_nodes(self, graph_id: GraphId) -> int:
        """Return number of nodes for a given graph."""
    
    @abstractmethod
    def find_node_id_by_payload_ref(self, graph_id: GraphId, payload_ref: PayloadRef) -> NodeId | None:
        """Return an existing node id for this payload_ref (exact dedupe), or None."""
