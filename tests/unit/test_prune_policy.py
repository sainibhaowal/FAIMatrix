"""Unit tests for prune policy."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

# Setup paths
_tests_dir = Path(__file__).parent.parent
_faim_native = _tests_dir.parent
if str(_faim_native) not in sys.path:
    sys.path.insert(0, str(_faim_native))

from core.operators.prune import PrunePolicy, can_prune  # noqa: E402


class MockNode:
    """Mock node for testing."""

    def __init__(
        self,
        node_id=None,
        kind="atom",
        touch_count=0,
        created_at=None,
    ):
        self.node_id = node_id or uuid4()
        self.kind = kind
        self.touch_count = touch_count
        self.created_at = created_at or datetime.now(timezone.utc)


class TestPrunePolicy:
    """Unit tests for prune policy."""

    def test_fresh_node_not_pruned(self):
        """Fresh nodes should not be pruned."""
        node = MockNode(created_at=datetime.now(timezone.utc))
        policy = PrunePolicy(min_age_days=7)

        assert can_prune(node, max_similarity=0.99, policy=policy) is False

    def test_old_low_usage_high_redundancy_pruned(self):
        """Old, low-usage, high-redundancy nodes should be pruned."""
        old_date = datetime.now(timezone.utc) - timedelta(days=30)
        node = MockNode(
            touch_count=0,
            created_at=old_date,
        )
        policy = PrunePolicy(
            min_age_days=7,
            max_touch_count=0,
            min_similarity_for_redundancy=0.98,
        )

        assert can_prune(node, max_similarity=0.99, policy=policy) is True

    def test_high_usage_not_pruned(self):
        """High-usage nodes should not be pruned."""
        old_date = datetime.now(timezone.utc) - timedelta(days=30)
        node = MockNode(
            touch_count=10,
            created_at=old_date,
        )
        policy = PrunePolicy(max_touch_count=0)

        assert can_prune(node, max_similarity=0.99, policy=policy) is False

    def test_low_redundancy_not_pruned(self):
        """Low-redundancy nodes should not be pruned."""
        old_date = datetime.now(timezone.utc) - timedelta(days=30)
        node = MockNode(
            touch_count=0,
            created_at=old_date,
        )
        policy = PrunePolicy(min_similarity_for_redundancy=0.98)

        assert can_prune(node, max_similarity=0.50, policy=policy) is False

    def test_macro_protected(self):
        """Macro nodes should be protected from pruning."""
        old_date = datetime.now(timezone.utc) - timedelta(days=30)
        node = MockNode(
            kind="macro",
            touch_count=0,
            created_at=old_date,
        )
        policy = PrunePolicy(protect_macros=True)

        assert can_prune(node, max_similarity=0.99, policy=policy) is False

    def test_macro_not_protected_when_disabled(self):
        """Macro nodes can be pruned when protection is disabled."""
        old_date = datetime.now(timezone.utc) - timedelta(days=30)
        node = MockNode(
            kind="macro",
            touch_count=0,
            created_at=old_date,
        )
        policy = PrunePolicy(
            protect_macros=False,
            min_age_days=7,
            max_touch_count=0,
            min_similarity_for_redundancy=0.98,
        )

        assert can_prune(node, max_similarity=0.99, policy=policy) is True

    def test_default_policy_conservative(self):
        """Default policy should be conservative."""
        policy = PrunePolicy()

        assert policy.min_age_days == 7.0
        assert policy.max_touch_count == 1
        assert policy.min_similarity_for_redundancy == 0.98
        assert policy.protect_macros is True
