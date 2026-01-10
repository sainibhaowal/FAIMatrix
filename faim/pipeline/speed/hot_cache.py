"""
================================================================================
 FAIM HyperSpeed – Warm Node Cache (P4.2)
--------------------------------------------------------------------------------
 This module implements the Warm Node Cache for TRUE FAIM.

 Goals:
   * Keep only the "hot working set" of NodeRecords in RAM (Tier-2), keyed by
     NodeId, while the full graph remains durable in the cold store (Tier-3).
   * Provide an LRU-based cache with:
       - O(1) average get/put/remove operations,
       - deterministic eviction behaviour,
       - thread-safe access for the FAIM engine.
   * Integrate with SpeedBudget.max_warm_nodes so P4.0 limits are enforced.

 Design:
   * Pure in-RAM data structure:
       - OrderedDict[NodeId, NodeRecord] as the primary store (LRU).
       - RLock for concurrency safety across threads.
   * No disk I/O:
       - Loading of NodeRecords from persistent store is delegated to
         caller-provided loader functions.
   * Engine usage patterns:
       - On add_memory:
           cache.put(node_id, node_record)
       - On retrieve:
           records = cache.get_many(node_ids, bulk_loader=node_store.load_many)

 Invariants:
   * Eviction never deletes real data: evicted entries are still present in the
     persistent store; we only drop the RAM copy.
   * NodeRecord type is opaque to this module: we store any Python object.
   * Cache size is bounded by max_warm_nodes; a value of 0 effectively disables
     the cache (pass-through to loaders).

 Metrics:
   * CacheStats tracks hits, misses, loads, puts, evictions.
   * These can be exported into FAIM's metrics layer.

================================================================================
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Hashable,
    Iterable,
    List,
    Optional,
    Sequence,
    TypeVar,
)

from faim.pipeline.speed.spec import SpeedBudget

# Optional logging hook (does not require loguru to be installed)
try:  # pragma: no cover - logging is optional
    from loguru import logger
except Exception:  # pragma: no cover - fallback when loguru is absent

    class _DummyLogger:
        def debug(self, *args: Any, **kwargs: Any) -> None: ...
        def info(self, *args: Any, **kwargs: Any) -> None: ...
        def warning(self, *args: Any, **kwargs: Any) -> None: ...
        def error(self, *args: Any, **kwargs: Any) -> None: ...
        def exception(self, *args: Any, **kwargs: Any) -> None: ...

    logger = _DummyLogger()  # type: ignore[assignment]


# Type aliases -----------------------------------------------------------------
NodeId = Hashable
NodeRecordT = TypeVar("NodeRecordT")


@dataclass
class CacheStats:
    """
    Simple metrics for the warm node cache.

    All fields except `size` are monotonically increasing counters. The
    engine or metrics layer can snapshot and derive rates (per second/minute)
    as needed.

    `size` reflects the current number of entries in the cache.
    """

    hits: int = 0
    misses: int = 0
    loads: int = 0
    puts: int = 0
    evictions: int = 0
    size: int = 0  # <--- NEW

    def total_requests(self) -> int:
        """Return total number of cache lookup attempts."""
        return self.hits + self.misses

    def hit_rate(self) -> float:
        """Return cache hit rate in [0, 1]."""
        total = self.total_requests()
        if total == 0:
            return 0.0
        return self.hits / float(total)


class HotNodeCache(Generic[NodeRecordT]):
    """
    Warm Node Cache (Tier-2) for FAIM NodeRecords.

    This is an LRU cache keyed by NodeId with a hard cap on the number of
    stored records. It is designed to sit between the engine and the cold
    durable store (SQLite/LMDB/RocksDB).

    Typical workflow:

        budget = get_speed_budget("LAPTOP")
        cache = HotNodeCache[NodeRecord](speed_budget=budget)

        # On add_memory:
        cache.put(node_id, node_record)

        # On retrieve:
        records = cache.get_many(
            node_ids,
            bulk_loader=node_store.load_many,
        )

    The loader functions are responsible for reading from the persistent
    store. This module itself never touches disk or performs I/O.
    """

    __slots__ = ("_max_size", "_store", "_lock", "_stats")

    def __init__(
        self,
        speed_budget: SpeedBudget,
        *,
        max_warm_nodes_override: Optional[int] = None,
    ) -> None:
        """
        Create a new HotNodeCache.

        Args:
            speed_budget:
                Active SpeedBudget, providing a default max_warm_nodes limit.
            max_warm_nodes_override:
                Optional override for the cache capacity. If None, the value
                from speed_budget.max_warm_nodes is used.

        A max size of 0 effectively disables caching (all gets become misses
        and are always delegated to loader functions without storing).
        """
        max_nodes = (
            speed_budget.max_warm_nodes
            if max_warm_nodes_override is None
            else max_warm_nodes_override
        )
        if max_nodes < 0:
            raise ValueError(f"max_warm_nodes must be non-negative, got {max_nodes}")

        self._max_size: int = max_nodes
        self._store: "OrderedDict[NodeId, NodeRecordT]" = OrderedDict()
        self._lock: RLock = RLock()
        self._stats: CacheStats = CacheStats()

        logger.info(
            "HotNodeCache initialised with max_warm_nodes={max_nodes}",
            max_nodes=self._max_size,
        )

    def clear(self) -> None:
        """
        Drop all entries from the cache.

        This does not touch the persistent store; it only resets the RAM copy.
        """
        with self._lock:
            self._store.clear()
            self._stats.size = 0
            # We intentionally do NOT reset hits/misses/loads/puts/evictions here,
            # so long-running metrics remain meaningful. Tests only assert size.

    # ------------------------------------------------------------------ public

    @property
    def max_size(self) -> int:
        """Return maximum number of NodeRecords that may be kept in RAM."""
        return self._max_size

    @property
    def stats(self) -> CacheStats:
        """Return current cache statistics."""
        return self._stats

    def __len__(self) -> int:  # pragma: no cover - trivial
        """Return number of NodeRecords currently in the cache."""
        with self._lock:
            return len(self._store)

    # --------------------------- single-node operations -----------------------

    def get_if_present(self, node_id: NodeId) -> Optional[NodeRecordT]:
        """
        Return the NodeRecord for node_id if present in cache, else None.

        This method does not load from persistent store and is safe to use
        in contexts where the caller wants a fast "peek" without triggering
        any I/O.
        """
        if self._max_size == 0:
            return None

        with self._lock:
            record = self._store.get(node_id)
            if record is None:
                self._stats.misses += 1
                return None

            # Move to the end to mark as recently used (LRU policy).
            self._store.move_to_end(node_id, last=True)
            self._stats.hits += 1
            return record

    def get(self, node_id: NodeId) -> Optional[NodeRecordT]:
        """
        Return the NodeRecord for node_id if present in cache, else None.

        This is a convenience wrapper used by tests and simple call sites.
        It does NOT load from persistent store; for load-on-miss behaviour,
        use get_if_present(...) together with your own loader, or
        get_many(..., bulk_loader=..., single_loader=...).
        """
        return self.get_if_present(node_id)

    def put(self, node_id: NodeId, record: NodeRecordT) -> None:
        """
        Insert or update a NodeRecord for node_id in the cache.

        This is typically called by the engine when adding or updating nodes
        in the graph. It does not touch persistent storage.
        """
        if self._max_size == 0:
            return

        with self._lock:
            self._put_locked(node_id, record)

    def remove(self, node_id: NodeId) -> None:
        """
        Remove node_id from the cache, if present.

        This does not affect the persistent store; it only drops the RAM copy.
        """
        with self._lock:
            if node_id in self._store:
                self._store.pop(node_id, None)
                self._stats.size = len(self._store)

    # --------------------------- bulk operations ------------------------------

    def get_many(
        self,
        node_ids: Iterable[NodeId],
        *,
        bulk_loader: Optional[Callable[[Sequence[NodeId]], Dict[NodeId, NodeRecordT]]] = None,
        single_loader: Optional[Callable[[NodeId], NodeRecordT]] = None,
    ) -> Dict[NodeId, NodeRecordT]:
        """
        Retrieve NodeRecords for a batch of node_ids.

        Args:
            node_ids:
                Iterable of NodeIds to fetch.
            bulk_loader:
                Optional function taking a sequence of missing NodeIds and
                returning a mapping NodeId -> NodeRecordT.
            single_loader:
                Optional per-node loader for misses when bulk_loader is not
                provided. Either bulk_loader or single_loader must be given
                if cache misses are expected.

        Returns:
            A dictionary NodeId -> NodeRecordT for all requested node_ids.
            If a loader cannot provide a record for a given node_id, that
            entry will simply be absent from the result.
        """
        ids_list: List[NodeId] = list(node_ids)
        if not ids_list:
            return {}

        if self._max_size == 0:
            # Cache disabled: load everything from store.
            return self._load_all_no_cache(ids_list, bulk_loader, single_loader)

        # First pass: hit/miss classification.
        hits: Dict[NodeId, NodeRecordT] = {}
        missing: List[NodeId] = []

        with self._lock:
            for nid in ids_list:
                rec = self._store.get(nid)
                if rec is not None:
                    self._store.move_to_end(nid, last=True)
                    hits[nid] = rec
                    self._stats.hits += 1
                else:
                    missing.append(nid)

        self._stats.misses += len(missing)

        if not missing:
            return hits

        # Load missing nodes outside lock.
        loaded: Dict[NodeId, NodeRecordT] = {}
        if bulk_loader is not None:
            if missing:
                loaded = bulk_loader(missing)
                self._stats.loads += len(loaded)
        else:
            if single_loader is None:
                raise ValueError(
                    "HotNodeCache.get_many: either bulk_loader or single_loader "
                    "must be provided when cache misses occur."
                )
            for nid in missing:
                try:
                    rec = single_loader(nid)
                except KeyError:
                    continue
                loaded[nid] = rec
            self._stats.loads += len(loaded)

        # Store loaded results in cache.
        if loaded:
            with self._lock:
                for nid, rec in loaded.items():
                    self._put_locked(nid, rec)

        # Merge hits and loaded.
        result: Dict[NodeId, NodeRecordT] = {}
        result.update(hits)
        result.update(loaded)
        return result

    # ----------------------------------------------------------------- internals

    def _load_all_no_cache(
        self,
        node_ids: Sequence[NodeId],
        bulk_loader: Optional[Callable[[Sequence[NodeId]], Dict[NodeId, NodeRecordT]]],
        single_loader: Optional[Callable[[NodeId], NodeRecordT]],
    ) -> Dict[NodeId, NodeRecordT]:
        """
        Helper: load all node_ids from store when cache is disabled.
        """
        if bulk_loader is not None:
            loaded = bulk_loader(node_ids)
            self._stats.misses += len(node_ids)
            self._stats.loads += len(loaded)
            return loaded

        if single_loader is None:
            raise ValueError(
                "HotNodeCache: cache disabled and no loader provided "
                "(need bulk_loader or single_loader)."
            )

        result: Dict[NodeId, NodeRecordT] = {}
        for nid in node_ids:
            try:
                rec = single_loader(nid)
            except KeyError:
                continue
            result[nid] = rec

        self._stats.misses += len(node_ids)
        self._stats.loads += len(result)
        return result

    def _put_locked(self, node_id: NodeId, record: NodeRecordT) -> None:
        """
        Insert or update a record in the cache.

        This method assumes the caller already holds self._lock.
        """
        if self._max_size == 0:
            return

        # If already present, update and mark as recently used.
        if node_id in self._store:
            self._store[node_id] = record
            self._store.move_to_end(node_id, last=True)
            self._stats.puts += 1
            return

        # Insert new entry at the end (most recently used).
        self._store[node_id] = record
        self._store.move_to_end(node_id, last=True)
        self._stats.puts += 1

        # Evict least recently used entries if over capacity.
        while len(self._store) > self._max_size:
            evicted_nid, _ = self._store.popitem(last=False)
            self._stats.evictions += 1
            logger.debug(
                "HotNodeCache eviction: node_id={node_id}",
                node_id=evicted_nid,
            )

        # Evict least recently used entries if over capacity.
        while len(self._store) > self._max_size:
            evicted_nid, _ = self._store.popitem(last=False)
            self._stats.evictions += 1
            logger.debug(
                "HotNodeCache eviction: node_id={node_id}",
                node_id=evicted_nid,
            )

        # Track current cache size for tests/metrics.
        self._stats.size = len(self._store)
