"""
================================================================================
 FAIM HyperSpeed – Write Queue (P4.4)
--------------------------------------------------------------------------------
 This module implements a durable write queue for TRUE FAIM.

 Purpose:
   * Decouple FAIMEngine.add_memory() from slow disk writes.
   * Allow the hot path to:
       - embed, inheritance, antisym, VectorBank add, HotNodeCache put
       - enqueue a small write struct to a background pipeline
       - optionally wait (STRICT mode) until the write is durably committed.
   * Provide:
       - Monotonic sequence IDs for writes
       - Batching-friendly 'take_batch' API for ingest workers
       - 'wait_until_committed' API for FAIM_PERSIST_MODE=strict

 Design:
   * Internal data structure:
       - deque[WriteTask] protected by RLock + Conditions
       - maxsize to bound memory usage
   * API:
       - enqueue_write(op, graph_id, node_id, data, ts) -> seq_id
       - take_batch(max_items, timeout) -> List[WriteTask]
       - mark_committed(seq_id)   # called by ingest worker after durable write
       - wait_until_committed(seq_id, timeout) -> bool

 Notes:
   * This module does NOT touch disk or know about SQLite/LMDB; it is purely
     an in-memory queue and coordination primitive.
   * The ingest worker (P4.4) will call into your NodeStore / Journal layer
     and then mark writes committed.

================================================================================
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from queue import Empty, Full  # reuse standard exceptions for familiarity
from threading import Condition, RLock
from typing import Any, Deque, Dict, Hashable, List, Optional, Union

from faim.speed.spec import SpeedBudget

GraphId = Union[int, str]
NodeId = Hashable


@dataclass(frozen=True)
class WriteTask:
    """
    Single write operation destined for the cold durability layer.

    Fields:
        seq_id:
            Monotonic sequence number assigned by WriteQueue.
        op:
            Operation type, e.g. "upsert", "delete". The meaning is defined
            by the ingest worker / NodeStore.
        graph_id:
            Identifier for the FAIM graph this node belongs to.
        node_id:
            Node identifier. Stable across FAIM.
        data:
            Minimal metadata payload needed for persistence and journaling.
            This is intentionally compact (no huge blobs).
        ts:
            Event timestamp in seconds since epoch (float).
    """

    seq_id: int
    op: str
    graph_id: GraphId
    node_id: NodeId
    data: Dict[str, Any]
    ts: float


@dataclass(frozen=True)
class WriteQueueStats:
    """
    Lightweight snapshot of WriteQueue state.

    queued:
        Number of tasks currently waiting in the queue.
    last_commit_seq:
        Highest seq_id that has been marked committed.
    """

    queued: int
    last_commit_seq: int


class WriteQueue:
    """
    Thread-safe write queue with batching and commit tracking.

    Typical engine usage:

        self._write_queue = WriteQueue(speed_budget, maxsize=100_000)

        # In add_memory (hot path):
        seq = self._write_queue.enqueue_write(
            op="upsert",
            graph_id=graph_id,
            node_id=node_id,
            data=minimal_payload,
        )
        if self._persist_mode is PersistMode.STRICT:
            self._write_queue.wait_until_committed(seq, timeout=self._strict_timeout)

        # In background ingest worker:
        batch = self._write_queue.take_batch(max_items=2000, timeout=0.1)
        if batch:
            node_store.write_batch(batch)  # your implementation
            self._write_queue.mark_committed(batch[-1].seq_id)

    Invariants:
      * seq_id is strictly increasing per WriteQueue instance.
      * mark_committed() is called in FIFO order (batches preserve order).
      * wait_until_committed() blocks until last_committed_seq >= seq_id
        or the timeout elapses.
    """

    __slots__ = (
        "_speed_budget",
        "_maxsize",
        "_queue",
        "_lock",
        "_not_empty",
        "_not_full",
        "_committed",
        "_next_seq",
        "_last_committed_seq",
    )

    def __init__(
        self,
        speed_budget: SpeedBudget,
        *,
        maxsize: int = 100_000,
    ) -> None:
        """
        Args:
            speed_budget:
                Active SpeedBudget (not used directly yet, but kept for
                future policies and metrics).
            maxsize:
                Maximum number of enqueued tasks. 0 or negative means
                'unbounded' (beware of memory growth in that case).
        """
        self._speed_budget = speed_budget
        self._maxsize = int(maxsize)

        self._queue: Deque[WriteTask] = deque()
        self._lock: RLock = RLock()
        self._not_empty: Condition = Condition(self._lock)
        self._not_full: Condition = Condition(self._lock)
        self._committed: Condition = Condition(self._lock)

        self._next_seq: int = 1
        self._last_committed_seq: int = 0

    @property
    def stats(self) -> WriteQueueStats:
        """
        Return a lightweight snapshot of the queue state.

        This is safe to call from any thread; it holds the internal lock
        briefly to read the size and last_committed_seq.
        """
        with self._lock:
            return WriteQueueStats(
                queued=len(self._queue),
                last_commit_seq=self._last_committed_seq,
            )

    # ------------------------------------------------------------------ public

    @property
    def maxsize(self) -> int:
        """Return maximum number of tasks allowed in the queue (0 = unbounded)."""
        return self._maxsize

    def qsize(self) -> int:
        """Return the approximate size of the queue."""
        with self._lock:
            return len(self._queue)

    def last_committed_seq(self) -> int:
        """Return the highest seq_id that has been marked committed."""
        with self._lock:
            return self._last_committed_seq

    # ------------------------------- enqueue / dequeue ------------------------

    def enqueue_write(
        self,
        op: str,
        graph_id: GraphId,
        node_id: NodeId,
        data: Dict[str, Any],
        *,
        ts: Optional[float] = None,
        block: bool = True,
        timeout: Optional[float] = None,
    ) -> int:
        """
        Enqueue a write task.

        Args:
            op:
                Operation type ("upsert", "delete", ...).
            graph_id:
                Graph identifier.
            node_id:
                Node identifier.
            data:
                Minimal persistence payload.
            ts:
                Optional timestamp; defaults to time.time().
            block:
                If True, block when the queue is full until space is available
                or timeout expires. If False and the queue is full, raise Full.
            timeout:
                Maximum time in seconds to block when queue is full. None
                means 'wait indefinitely'.

        Returns:
            seq_id assigned to this write, to be used with wait_until_committed.

        Raises:
            Full:
                If the queue is full and block=False or the timeout expires.
        """
        tstamp = float(time.time() if ts is None else ts)

        with self._lock:
            if self._maxsize > 0:
                # capacity-bounded
                if not block and len(self._queue) >= self._maxsize:
                    raise Full("WriteQueue is full")

                if block:
                    end = None if timeout is None else time.monotonic() + timeout
                    while len(self._queue) >= self._maxsize:
                        remaining = None if end is None else end - time.monotonic()
                        if remaining is not None and remaining <= 0.0:
                            raise Full("WriteQueue.put timed out waiting for free slot")
                        self._not_full.wait(remaining)

            seq_id = self._next_seq
            self._next_seq += 1

            task = WriteTask(
                seq_id=seq_id,
                op=op,
                graph_id=graph_id,
                node_id=node_id,
                data=data,
                ts=tstamp,
            )
            self._queue.append(task)
            self._not_empty.notify()
            return seq_id

    def take_batch(
        self,
        max_items: int,
        *,
        timeout: Optional[float] = None,
    ) -> List[WriteTask]:
        """
        Take up to max_items tasks from the head of the queue.

        This is intended for ingest workers. It returns a list that is:
          * empty if no items are available within timeout, or
          * size in [1, max_items].

        Args:
            max_items:
                Maximum number of tasks to return.
            timeout:
                Maximum time to wait for at least one item. None means
                'wait indefinitely'.

        Returns:
            List of WriteTask.

        Raises:
            Empty:
                If timeout is 0 and the queue is empty immediately.
        """
        if max_items <= 0:
            raise ValueError(f"max_items must be positive, got {max_items}")

        with self._lock:
            if not self._queue:
                if timeout == 0:
                    raise Empty("WriteQueue is empty")
                end = None if timeout is None else time.monotonic() + timeout
                while not self._queue:
                    remaining = None if end is None else end - time.monotonic()
                    if remaining is not None and remaining <= 0.0:
                        # Timed out with no items.
                        return []
                    self._not_empty.wait(remaining)

            n = min(max_items, len(self._queue))
            batch: List[WriteTask] = [self._queue.popleft() for _ in range(n)]
            # Notify potential producers waiting on full queue.
            if self._maxsize > 0:
                self._not_full.notify_all()
            return batch

    # ------------------------------- commit tracking -------------------------

    def mark_committed(self, seq_id: int) -> None:
        """
        Mark all tasks up to seq_id as durably written.

        This is normally called by the ingest worker AFTER a batch has been
        successfully written to the persistent store and journal.

        Assumes that batches are processed in FIFO order, so seq_id will
        be monotonically increasing.
        """
        with self._lock:
            if seq_id > self._last_committed_seq:
                self._last_committed_seq = seq_id
                self._committed.notify_all()

    def wait_until_committed(
        self,
        seq_id: int,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Block until seq_id has been marked committed or timeout elapses.

        This is the key primitive for FAIM_PERSIST_MODE=STRICT:

            seq = queue.enqueue_write(...)
            ok = queue.wait_until_committed(seq, timeout=0.5)

        Args:
            seq_id:
                Sequence number to wait for.
            timeout:
                Maximum time in seconds to wait. None means wait indefinitely.

        Returns:
            True if seq_id is committed; False if timeout elapsed first.
        """
        with self._lock:
            if self._last_committed_seq >= seq_id:
                return True

            end = None if timeout is None else time.monotonic() + timeout
            while self._last_committed_seq < seq_id:
                remaining = None if end is None else end - time.monotonic()
                if remaining is not None and remaining <= 0.0:
                    return False
                self._committed.wait(remaining)

            return True
