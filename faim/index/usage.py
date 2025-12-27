"""Usage index utilities for FAIM.

P2 baseline: thin wrapper around NodeRecord.use_count / last_used_at.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import time

from faim.core.types import NodeRecord


@dataclass
class UsageTracker:
    """Tracks usage by updating NodeRecord fields.

    For P2 we keep it simple:
    - touch(node) increments use_count and sets last_used_at.
    - score(node) returns a monotonic function of use_count.
    """

    def touch(self, node: NodeRecord, *, at: float | None = None) -> None:
        now = time() if at is None else at
        node.use_count += 1
        node.last_used_at = now

    def score(self, node: NodeRecord, *, now: float | None = None) -> float:
        """Compute a simple usage score for retrieval ranking."""
        _ = now  # reserved for future recency weighting
        return float(node.use_count)
