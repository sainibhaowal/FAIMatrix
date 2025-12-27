# ======================================================================
# FAIM HyperSpeed P4.2 – Warm Node Cache (RAM NodeRecords)
# Golden Edition – verifies LRU behaviour and basic stats.
# ======================================================================

from dataclasses import dataclass

from faim.speed.hot_cache import HotNodeCache
from faim.speed.spec import get_speed_budget


@dataclass
class DummyNode:
    node_id: str
    payload: str


def test_p42_hot_node_cache_lru_and_stats():
    """
    With max_warm_nodes=3:
    - inserting 4 keys should trigger at least one eviction
    - stats should reflect hits/misses/evictions sensibly.
    """
    budget = get_speed_budget("CORE_DEV")
    cache: HotNodeCache = HotNodeCache(speed_budget=budget, max_warm_nodes_override=3)

    # Fill cache
    for i in range(3):
        cache.put(f"n{i}", DummyNode(node_id=f"n{i}", payload=f"p{i}"))

    stats = cache.stats
    assert stats.size == 3
    assert stats.evictions == 0

    # Access n0 to make it most recently used
    node = cache.get("n0")
    assert node is not None
    assert node.node_id == "n0"

    # Insert a 4th entry, forcing eviction of one of the older ones
    cache.put("n3", DummyNode(node_id="n3", payload="p3"))
    stats = cache.stats
    assert stats.size == 3
    assert stats.evictions >= 1

    # n3 must be present
    assert cache.get("n3") is not None

    # Exactly 3 of n0..n3 exist; n0 must still be present (recently used).
    present_keys = [k for k in ("n0", "n1", "n2", "n3") if cache.get(k) is not None]
    assert "n0" in present_keys
    assert "n3" in present_keys
    assert len(present_keys) == 3


def test_p42_hot_node_cache_clear_and_reuse():
    """
    clear() should drop everything; we can reuse the cache afterward.
    """
    budget = get_speed_budget("CORE_DEV")
    cache = HotNodeCache(speed_budget=budget, max_warm_nodes_override=2)

    cache.put("x", DummyNode(node_id="x", payload="x1"))
    cache.put("y", DummyNode(node_id="y", payload="y1"))
    assert cache.stats.size == 2

    cache.clear()
    assert cache.stats.size == 0
    assert cache.get("x") is None
    assert cache.get("y") is None

    # Reuse after clear
    cache.put("z", DummyNode(node_id="z", payload="z1"))
    assert cache.stats.size == 1
    assert cache.get("z") is not None
