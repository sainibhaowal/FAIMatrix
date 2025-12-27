"""Core type definitions for FAIM.

Golden Edition: explicit ids, dataclasses, and lightweight records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, NewType, Optional

import numpy as np

Vector = np.ndarray

NodeId = NewType("NodeId", str)
GraphId = NewType("GraphId", str)
PayloadRef = NewType("PayloadRef", str)


@dataclass
class ParentRef:
    """Reference to a parent node with inheritance fraction."""

    parent_id: NodeId
    fraction: float


@dataclass
class NodeRecord:
    """A single node in the Fractal Inheritance Graph (FIG)."""

    id: NodeId
    graph_id: GraphId
    vec: Vector
    parents: List[ParentRef] = field(default_factory=list)
    children: List[NodeId] = field(default_factory=list)
    payload_ref: Optional[PayloadRef] = None
    created_at: float = 0.0
    last_used_at: float = 0.0
    use_count: int = 0
    merged_count: int = 0
    flags: int = 0  # bitset for future use


@dataclass
class GraphState:
    """In-memory representation of a FIG for a single graph id."""

    graph_id: GraphId
    nodes: Dict[NodeId, NodeRecord] = field(default_factory=dict)
