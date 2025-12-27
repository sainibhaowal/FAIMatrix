# ======================================================================
# FAIM HyperSpeed P4.4 – Parallelism & Write Queue
# Golden Edition – validate WriteQueue commit sequencing and blocking.
# ======================================================================

import time

from faim.speed.spec import get_speed_budget
from faim.speed.write_queue import WriteQueue


def test_p44_write_queue_commit_sequence_and_stats():
    """
    Put a few writes into the WriteQueue and ensure:

    - seq_id is monotonically increasing (no duplicates, strictly increasing)
    - take_batch returns them in FIFO order
    - mark_committed + wait_until_committed cooperate correctly
    - stats reflect queue emptiness and last committed seq.
    """
    budget = get_speed_budget("CORE_DEV")
    queue = WriteQueue(speed_budget=budget, maxsize=budget.write_queue_maxsize)

    now = time.time()

    # Enqueue a handful of writes.
    seq_ids = [
        queue.enqueue_write(
            op="upsert",
            graph_id="G-BENCH",
            node_id=f"n{i}",
            data={"idx": i},
            ts=now + i * 0.001,
        )
        for i in range(5)
    ]

    # Sequence IDs should be strictly increasing and unique.
    assert seq_ids == sorted(seq_ids)
    assert len(seq_ids) == len(set(seq_ids))

    # Take them all back in one batch.
    batch = queue.take_batch(max_items=10, timeout=0.0)
    assert len(batch) == 5
    # FIFO order on node_id.
    assert [t.node_id for t in batch] == [f"n{i}" for i in range(5)]

    last_seq = batch[-1].seq_id

    # Mark committed and ensure wait_until_committed returns True quickly.
    queue.mark_committed(last_seq)
    ok = queue.wait_until_committed(last_seq, timeout=1.0)
    assert ok

    # Check stats snapshot.
    stats = queue.stats
    assert stats.queued == 0
    assert stats.last_commit_seq == last_seq
