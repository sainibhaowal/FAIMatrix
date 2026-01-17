"""FAIM-Native Graph.

Core graph operations and utilities.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import uuid7  # noqa: F401
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))


@dataclass
class GraphStats:
    """Statistics for a FAIM graph.

    Attributes:
        node_count: Total nodes.
        atom_count: Atom nodes (level 0).
        macro_count: Macro nodes (level > 0).
        edge_count: Total edges.
        inheritance_edges: Inheritance edges.
        opposition_edges: Opposition edges.
        graph_version: Current version.
        graph_hash: Current hash.
    """

    node_count: int = 0
    atom_count: int = 0
    macro_count: int = 0
    edge_count: int = 0
    inheritance_edges: int = 0
    opposition_edges: int = 0
    graph_version: int = 0
    graph_hash: str = ""


def compute_graph_hash(
    nodes: List[Tuple[str, str, int, float]],
    edges: List[Tuple[str, str, str, str, float]],
) -> str:
    """Compute deterministic hash of graph state.

    Args:
        nodes: List of (node_id, vector_hash, level, residual).
        edges: List of (edge_id, src, dst, kind, weight).

    Returns:
        SHA256 hash of canonical JSON.
    """
    # Sort for determinism
    nodes_sorted = sorted(nodes)
    edges_sorted = sorted(edges)

    canonical = {
        "nodes": nodes_sorted,
        "edges": edges_sorted,
    }

    json_str = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def compute_compression_ratio(atom_count: int, macro_count: int) -> float:
    """Compute compression ratio.

    CR = atoms / (atoms + macros)

    Lower = more compression (more macros).
    """
    total = atom_count + macro_count
    if total == 0:
        return 1.0
    return atom_count / total


def compute_redundancy_estimate(
    similarity_scores: List[float],
) -> float:
    """Compute redundancy estimate.

    R = mean of max similarities.
    Higher = more redundancy.
    """
    if not similarity_scores:
        return 0.0
    return sum(similarity_scores) / len(similarity_scores)


# Exports
__all__ = [
    "GraphStats",
    "compute_graph_hash",
    "compute_compression_ratio",
    "compute_redundancy_estimate",
]
