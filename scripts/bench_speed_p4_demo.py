#!/usr/bin/env python
"""
scripts/bench_speed_p4_demo.py

Ad-hoc P4 HyperSpeed demo:
- Build a synthetic FAIM graph with N nodes.
- Show per-chunk insert speed (e.g. every 10,000 nodes).
- Measure retrieve latency over many queries.
- Report mean / p50 / p95 / p99 in milliseconds.

Run:

    cd ~/FAIM
    source .venv/bin/activate
    python scripts/bench_speed_p4_demo.py
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# Ensure repo root is on sys.path so "import faim" works even when running
# "python scripts/bench_speed_p4_demo.py".
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from faim.core.engine import FAIMEngine  # type: ignore[import]  # noqa: E402, I001


def percentile_from_sorted(values: List[float], p: float) -> float:
    """
    Compute a percentile from a sorted list (0 <= p <= 1) using a simple
    nearest-rank style index. Good enough for benchmark logging.
    """
    if not values:
        raise ValueError("Cannot compute percentile of empty list")

    n = len(values)
    if p <= 0.0:
        return values[0]
    if p >= 1.0:
        return values[-1]

    idx = int(p * (n - 1))
    return values[idx]


def bench_retrieve(engine: FAIMEngine, graph_id: str, n_queries: int = 500, k: int = 16) -> None:
    print(f"[bench] Measuring retrieve latency over {n_queries} queries...")

    latencies_ms: List[float] = []

    # warm-up
    engine.retrieve(graph_id=graph_id, query="warmup query", k=k)

    t0 = time.perf_counter()
    for i in range(n_queries):
        q = f"benchmark query {i % 100}"
        q_start = time.perf_counter()
        _ = engine.retrieve(graph_id=graph_id, query=q, k=k)
        q_end = time.perf_counter()
        latencies_ms.append((q_end - q_start) * 1000.0)
    t1 = time.perf_counter()

    total_s = t1 - t0
    qps = n_queries / total_s if total_s > 0 else float("inf")

    latencies_ms.sort()
    mean = statistics.mean(latencies_ms)
    p50 = percentile_from_sorted(latencies_ms, 0.50)
    p95 = percentile_from_sorted(latencies_ms, 0.95)
    p99 = percentile_from_sorted(latencies_ms, 0.99)

    print(f"[bench] TOTAL retrieve: {n_queries} queries in {total_s:.2f}s ({qps:.1f} qps)")
    print(
        f"[bench] retrieve latency mean={mean:.2f} ms, "
        f"p50={p50:.2f} ms, p95={p95:.2f} ms, p99={p99:.2f} ms"
    )


def main() -> None:
    # -----------------------------------------------------------------------
    # 1) Create engine
    # -----------------------------------------------------------------------
    engine = FAIMEngine(profile="CORE_DEV", persist_mode="relaxed")
    graph_id = "BENCH_GRAPH"

    # -----------------------------------------------------------------------
    # 2) Insert N synthetic nodes, with per-chunk stats
    # -----------------------------------------------------------------------
    n_nodes = 40_000
    chunk_size = 10_000  # print stats every 10k nodes
    num_chunks = n_nodes // chunk_size

    print(f"[bench] Inserting {n_nodes:,} nodes into graph '{graph_id}'...")

    total_start = time.perf_counter()
    for chunk_idx in range(num_chunks):
        chunk_start = time.perf_counter()
        start_i = chunk_idx * chunk_size
        end_i = start_i + chunk_size

        for i in range(start_i, end_i):
            payload = f"synthetic node {i}"
            meta = {"i": i}
            engine.add_memory(graph_id=graph_id, payload=payload, meta=meta)

        chunk_end = time.perf_counter()
        chunk_sec = chunk_end - chunk_start
        chunk_qps = chunk_size / chunk_sec if chunk_sec > 0 else float("inf")

        print(
            f"[bench] Inserted {chunk_size:,} nodes "
            f"(nodes {start_i:,}–{end_i - 1:,}) "
            f"in {chunk_sec:.2f} s ({chunk_qps:,.1f} inserts/sec)"
        )

    total_end = time.perf_counter()
    total_sec = total_end - total_start
    total_qps = n_nodes / total_sec if total_sec > 0 else float("inf")

    print(
        f"[bench] TOTAL: Inserted {n_nodes:,} nodes in "
        f"{total_sec:.2f} s ({total_qps:,.1f} inserts/sec)"
    )

    # -----------------------------------------------------------------------
    # 3) Measure retrieval latency & QPS
    # -----------------------------------------------------------------------
    bench_retrieve(engine, graph_id=graph_id, n_queries=500, k=10)

    # Clean shutdown
    if hasattr(engine, "shutdown"):
        engine.shutdown()


if __name__ == "__main__":
    main()
