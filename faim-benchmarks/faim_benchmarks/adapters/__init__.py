"""Black-box system adapters for FAIM and local open-source baselines."""

from faim_benchmarks.adapters.base import (
    AdapterConfigError,
    IngestOutcome,
    MemorySystemAdapter,
    QueryOutcome,
)
from faim_benchmarks.adapters.competitors import (
    BM25BaselineAdapter,
    build_all_adapters,
)
from faim_benchmarks.adapters.faim_http import FaimHttpAdapter

__all__ = [
    "AdapterConfigError",
    "BM25BaselineAdapter",
    "FaimHttpAdapter",
    "IngestOutcome",
    "MemorySystemAdapter",
    "QueryOutcome",
    "build_all_adapters",
]
