#!/usr/bin/env python
"""
Baseline RAG benchmark harness to compare against FAIM.

Reads the same queries + QA files as FAIM's benchmarks.py,
stores everything in a simple vector DB (FAISS-like in-memory),
and computes metrics roughly comparable to FAIM's:
- compression ratio (cr)
- redundancy
- drift (placeholder = 0.0 for baseline)
- latency (store_p50, retrieve_p50, retrieve_p95)

Outputs a single JSON record.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np


@dataclass
class QAPair:
    query: str
    answer: str


@dataclass
class RagRecord:
    system: str
    workload: str
    nodes: int
    cr: float
    redundancy: float
    drift: float
    latency_store_p50: float
    latency_retrieve_p50: float
    latency_retrieve_p95: float
    extra: dict


def load_qa(qa_path: Path) -> List[QAPair]:
    qa_pairs: List[QAPair] = []
    with qa_path.open("r", encoding="utf8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if "\t" not in line:
                continue  # skip malformed
            q, a = line.split("\t", 1)
            qa_pairs.append(QAPair(query=q, answer=a))
    return qa_pairs


def load_queries(q_path: Path) -> List[str]:
    with q_path.open("r", encoding="utf8") as f:
        return [line.rstrip("\n") for line in f if line.strip()]


def simple_embed(text: str) -> np.ndarray:
    # NOTE: Replace this with your actual encoder if you want a fairer baseline.
    # This version is deterministic but random-like, based on the hash of the text.
    np.random.seed(abs(hash(text)) % (2**32))
    return np.random.randn(768).astype("float32")


class RagStore:
    """Minimal in-memory RAG store for benchmarking."""

    def __init__(self) -> None:
        self.vectors: List[np.ndarray] = []
        self.payloads: List[str] = []

    def add(self, text: str) -> None:
        self.vectors.append(simple_embed(text))
        self.payloads.append(text)

    def search(self, query: str, k: int = 8) -> List[Tuple[str, float]]:
        if not self.vectors:
            return []
        qv = simple_embed(query)
        mat = np.stack(self.vectors, axis=0)
        sims = mat @ qv  # cosine-like if normalized; OK for ranking
        idx = np.argsort(-sims)[:k]
        return [(self.payloads[i], float(sims[i])) for i in idx]


def measure_latency(store: RagStore, queries: List[str], k: int = 8) -> Tuple[float, float]:
    times: List[float] = []
    for q in queries:
        t0 = time.perf_counter()
        _ = store.search(q, k=k)
        dt = (time.perf_counter() - t0) * 1000.0
        times.append(dt)
    times.sort()
    if not times:
        return 0.0, 0.0
    p50 = times[len(times) // 2]
    p95 = times[int(len(times) * 0.95) - 1]
    return p50, p95


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--qa", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workload", type=str, required=True)
    parser.add_argument("--k", type=int, default=8)
    args = parser.parse_args()

    queries = load_queries(args.queries)
    _ = load_qa(args.qa)  # currently unused; kept for future drift metric

    store = RagStore()

    # Measure store latency per insert
    store_latencies: List[float] = []
    for q in queries:
        t0 = time.perf_counter()
        store.add(q)
        dt = (time.perf_counter() - t0) * 1000.0
        store_latencies.append(dt)

    store_latencies.sort()
    store_p50 = store_latencies[len(store_latencies) // 2] if store_latencies else 0.0

    # Retrieve latency
    retrieve_p50, retrieve_p95 = measure_latency(store, queries, k=args.k)

    # Baseline storage: raw text + vectors (no compression)
    raw_bytes = sum(len(q.encode("utf8")) for q in queries)
    dim = 768
    vec_bytes = len(queries) * dim * 4  # float32
    total_bytes = raw_bytes + vec_bytes

    # For baseline, define compression ratio as 1.0 (no compression).
    cr = 1.0

    # Redundancy: max similarity to any other vector
    redundancy_vals: List[float] = []
    for i, v in enumerate(store.vectors):
        if len(store.vectors) < 2:
            break
        others = np.stack([vv for j, vv in enumerate(store.vectors) if j != i], axis=0)
        sims = others @ v
        redundancy_vals.append(float(np.max(sims)))
    redundancy = float(np.mean(redundancy_vals)) if redundancy_vals else 0.0

    # Drift: for now, we set 0.0 for baseline.
    drift = 0.0

    record = RagRecord(
        system="baseline_rag",
        workload=args.workload,
        nodes=len(queries),
        cr=cr,
        redundancy=redundancy,
        drift=drift,
        latency_store_p50=store_p50,
        latency_retrieve_p50=retrieve_p50,
        latency_retrieve_p95=retrieve_p95,
        extra={"total_bytes": total_bytes},
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf8") as f:
        json.dump(asdict(record), f, indent=2)

    print(f"Wrote baseline record to {args.out}")


if __name__ == "__main__":
    main()
