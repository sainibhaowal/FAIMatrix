import random
import string
import time

import numpy as np
import psutil
from faim.core.engine import FAIMEngine
from faim.index.ann import ANNIndex
from faim.index.radius import RadiusIndex
from faim.index.usage import UsageTracker
from faim.storage.sqlite_store import SqliteStore

GRAPH_ID = "synthetic_graph"
NODE_COUNT = 1_000_000
QUERY_COUNT = 100


def random_string(length: int = 100) -> str:
    """Generate a random ASCII payload."""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choices(alphabet, k=length))


def generate_payloads(count: int) -> list[str]:
    """Generate a list of random payload strings."""
    return [random_string() for _ in range(count)]


def get_memory_usage_mb() -> float:
    """Return current process RSS memory usage in megabytes."""
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)


def benchmark() -> None:
    """Run a synthetic 1M-node insertion + retrieval benchmark for FAIM P2."""
    store = SqliteStore.default()
    engine = FAIMEngine(
        store=store,
        ann_index=ANNIndex(dim=64),
        radius_index=RadiusIndex(dim=64),
        usage=UsageTracker(),
    )

    payloads = generate_payloads(NODE_COUNT)

    initial_memory = get_memory_usage_mb()
    print(f"Initial memory usage: {initial_memory:.2f} MB")

    start = time.time()
    for i, payload in enumerate(payloads):
        engine.add_memory(GRAPH_ID, payload, meta={})
        if i % 10_000 == 0:
            print(f"Inserted {i}/{NODE_COUNT} nodes.")
    insertion_time = time.time() - start

    final_memory = get_memory_usage_mb()
    print(f"Insertion complete. Time for {NODE_COUNT} nodes: {insertion_time:.2f} s")
    print(f"Memory after insertion: {final_memory:.2f} MB")
    print(f"Memory increase: {final_memory - initial_memory:.2f} MB")

    query_times: list[float] = []
    for _ in range(QUERY_COUNT):
        random_query = random.choice(payloads)
        start_q = time.time()
        engine.retrieve(GRAPH_ID, random_query, k=10)
        query_times.append(time.time() - start_q)

    avg_q = float(np.mean(query_times)) if query_times else 0.0
    print(f"Average retrieval time for {QUERY_COUNT} queries: {avg_q:.6f} s")


if __name__ == "__main__":
    benchmark()
