"""FAIM-Native Prune Operator.

Deterministic pruning of low-value nodes.

Rules:
- Never delete RawTruth (raw store unchanged)
- Only prune nodes meeting ALL criteria:
  - Low usage (touch_count below threshold)
  - High redundancy (similar to another node)
  - Old enough (created_at before threshold)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
from uuid import UUID

# Flexible imports
try:
    from faim.Faim_Native.store.pg.models_faim import NodeModel
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from store.pg.models_faim import NodeModel


@dataclass(frozen=True)
class PruneCandidate:
    """A node candidate for pruning.

    Attributes:
        node_id: Node identifier.
        reason: Why it's a candidate.
        touch_count: Usage count.
        age_days: Days since creation.
        max_similarity: Highest similarity to other nodes.
    """

    node_id: UUID
    reason: str
    touch_count: int
    age_days: float
    max_similarity: float


@dataclass
class PrunePolicy:
    """Pruning policy configuration.

    Attributes:
        min_age_days: Minimum age in days before eligible.
        max_touch_count: Maximum touch_count to be eligible.
        min_similarity_for_redundancy: Minimum similarity to consider redundant.
        protect_macros: Whether to protect macro nodes from pruning.
    """

    min_age_days: float = 7.0
    max_touch_count: int = 0
    min_similarity_for_redundancy: float = 0.98
    protect_macros: bool = True


def can_prune(
    node: NodeModel,
    max_similarity: float,
    policy: PrunePolicy,
    now: Optional[datetime] = None,
) -> bool:
    """Check if a node can be pruned.

    Node must meet ALL criteria:
    1. Old enough (age > min_age_days)
    2. Low usage (touch_count <= max_touch_count)
    3. Redundant (max_similarity >= min_similarity_for_redundancy)
    4. Not a protected macro (if protect_macros=True)

    Args:
        node: Node to check.
        max_similarity: Maximum similarity to any other node.
        policy: Prune policy configuration.
        now: Current time (default: now).

    Returns:
        True if node can be pruned.
    """
    now = now or datetime.now(timezone.utc)

    # Check macro protection
    if policy.protect_macros and node.kind == "macro":
        return False

    # Check age
    if node.created_at:
        created = node.created_at
        # Handle naive datetime (SQLite) by assuming UTC
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age = now - created
        if age < timedelta(days=policy.min_age_days):
            return False
    else:
        return False  # No created_at, don't prune

    # Check usage
    if node.touch_count > policy.max_touch_count:
        return False

    # Check redundancy
    if max_similarity < policy.min_similarity_for_redundancy:
        return False

    return True


def find_prune_candidates(
    nodes: List[NodeModel],
    similarity_matrix: dict,
    policy: PrunePolicy,
    max_candidates: int = 10,
    now: Optional[datetime] = None,
) -> List[PruneCandidate]:
    """Find nodes that are candidates for pruning.

    Args:
        nodes: List of nodes to check.
        similarity_matrix: Dict of {node_id: max_similarity}.
        policy: Prune policy.
        max_candidates: Maximum candidates to return.
        now: Current time.

    Returns:
        List of PruneCandidate objects.
    """
    now = now or datetime.now(timezone.utc)
    candidates = []

    for node in nodes:
        node_id = node.node_id
        max_sim = similarity_matrix.get(node_id, 0.0)

        if can_prune(node, max_sim, policy, now):
            age_days = (now - node.created_at).days if node.created_at else 0
            candidates.append(
                PruneCandidate(
                    node_id=node_id,
                    reason="low_usage_high_redundancy",
                    touch_count=node.touch_count,
                    age_days=age_days,
                    max_similarity=max_sim,
                )
            )

    # Sort by similarity desc (most redundant first), then age desc
    candidates.sort(key=lambda x: (-x.max_similarity, -x.age_days))

    return candidates[:max_candidates]


def compute_similarity_matrix(
    nodes: List[NodeModel],
    cosine_fn,
) -> dict:
    """Compute max similarity for each node.

    Args:
        nodes: List of nodes.
        cosine_fn: Function to compute cosine similarity.

    Returns:
        Dict of {node_id: max_similarity}.
    """
    result = {}

    for i, node_a in enumerate(nodes):
        max_sim = 0.0
        v_a = node_a.v_native

        for j, node_b in enumerate(nodes):
            if i == j:
                continue
            v_b = node_b.v_native
            sim = cosine_fn(v_a, v_b)
            max_sim = max(max_sim, sim)

        result[node_a.node_id] = max_sim

    return result


# Exports
__all__ = [
    "PruneCandidate",
    "PrunePolicy",
    "can_prune",
    "find_prune_candidates",
    "compute_similarity_matrix",
]
