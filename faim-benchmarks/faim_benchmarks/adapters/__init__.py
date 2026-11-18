"""Black-box system adapters for FAIM and competitor memory systems."""

from faim_benchmarks.adapters.base import (
    AdapterConfigError,
    IngestOutcome,
    MemorySystemAdapter,
    QueryOutcome,
)
from faim_benchmarks.adapters.competitors import (
    BM25BaselineAdapter,
    LettaAdapter,
    Mem0Adapter,
    OpenAIFullContextAdapter,
    SuperMemoryAdapter,
    ZepAdapter,
    build_all_adapters,
)
from faim_benchmarks.adapters.faim_http import FaimHttpAdapter

__all__ = [
    "AdapterConfigError",
    "BM25BaselineAdapter",
    "FaimHttpAdapter",
    "IngestOutcome",
    "LettaAdapter",
    "Mem0Adapter",
    "MemorySystemAdapter",
    "OpenAIFullContextAdapter",
    "QueryOutcome",
    "SuperMemoryAdapter",
    "ZepAdapter",
    "build_all_adapters",
]
