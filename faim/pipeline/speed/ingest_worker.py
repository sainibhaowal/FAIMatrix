from __future__ import annotations

"""
Background worker that drains the WriteQueue and hands batches to a writer
function. This is part of the P4 ingest path.
"""

import threading  # noqa: E402
import time  # noqa: E402
from typing import Any, Callable, Sequence  # noqa: E402

from faim.pipeline.speed.write_queue import WriteQueue, WriteTask  # noqa: E402

try:  # pragma: no cover - logging optional
    from loguru import logger
except Exception:  # pragma: no cover
    # pragma: no cover
    class _DummyLogger:
        def debug(self, *args: Any, **kwargs: Any) -> None: ...
        def info(self, *args: Any, **kwargs: Any) -> None: ...
        def warning(self, *args: Any, **kwargs: Any) -> None: ...
        def error(self, *args: Any, **kwargs: Any) -> None: ...
        def exception(self, *args: Any, **kwargs: Any) -> None: ...

    logger = _DummyLogger()  # type: ignore[assignment]


WriteBatchWriter = Callable[[Sequence[WriteTask]], None]


class IngestWorker(threading.Thread):
    """
    Background worker that drains the WriteQueue and persists batched writes.

    Typical wiring:

        self._write_queue = WriteQueue(speed_budget, maxsize=100_000)

        def writer(batch: Sequence[WriteTask]) -> None:
            # Example SQLite transaction:
            with conn:
                node_store.upsert_node_batch(batch)
                journal.append_batch(batch)
                # atomic commit on context exit

        self._ingest_worker = IngestWorker(
            name="FAIM-IngestWorker",
            write_queue=self._write_queue,
            writer=writer,
            batch_size=2000,
            max_batch_delay=0.05,
        )
        self._ingest_worker.start()

    On shutdown:

        self._ingest_worker.stop(graceful=True)
        self._ingest_worker.join()

    After each successful writer() call, the worker marks committed for all
    tasks in the batch (by last seq_id). This unlocks STRICT-mode callers
    waiting on WriteQueue.wait_until_committed().
    """

    def __init__(
        self,
        write_queue: WriteQueue,
        writer: WriteBatchWriter,
        *,
        name: str = "FAIM-IngestWorker",
        batch_size: int = 2000,
        max_batch_delay: float = 0.05,
        max_backoff: float = 5.0,
    ) -> None:
        super().__init__(name=name, daemon=True)
        self._write_queue = write_queue
        self._writer = writer
        self._batch_size = int(batch_size)
        self._max_batch_delay = float(max_batch_delay)
        self._max_backoff = float(max_backoff)
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------ public

    def stop(self, *, graceful: bool = True) -> None:
        """
        Request the worker to stop.

        Args:
            graceful:
                If True, the worker will finish processing any tasks already
                pulled into its local batch, but it will not drain the entire
                queue. For a full drain, call stop(graceful=True) and then
                wait for queue.qsize() to reach 0 in your shutdown logic.
        """
        # For now we simply set the stop flag; the run loop checks it.
        self._stop_event.set()
        # Any blocking waits will exit because take_batch uses timeouts.

    # ------------------------------------------------------------------ thread

    def run(self) -> None:  # pragma: no cover - behaviour tested via integration
        """
        Main worker loop.

        Continuously pulls batches from the queue, writes them, and advances
        commit sequence. Handles writer errors with exponential backoff.
        """
        logger.info("IngestWorker thread started (name={name})", name=self.name)

        backoff = 0.0

        while not self._stop_event.is_set():
            try:
                batch = self._write_queue.take_batch(
                    max_items=self._batch_size,
                    timeout=self._max_batch_delay,
                )
                if not batch:
                    # No items available within timeout; check stop flag and loop.
                    continue

                # Fast path: write the batch.
                self._writer(batch)

                # Mark all tasks in the batch as committed (by last seq_id).
                last_seq = batch[-1].seq_id
                self._write_queue.mark_committed(last_seq)

                # Reset backoff after successful write.
                backoff = 0.0

            except Exception as exc:
                logger.exception(
                    "IngestWorker encountered error in writer: {exc}",
                    exc=exc,
                )
                # Exponential backoff to avoid hammering a broken DB.
                if backoff == 0.0:
                    backoff = 0.1
                else:
                    backoff = min(backoff * 2.0, self._max_backoff)

                time.sleep(backoff)

        logger.info("IngestWorker thread stopping (name={name})", name=self.name)
