"""FAIM-Native API: Routers Package."""

from .api_keys import router as api_keys_router
from .auth import router as auth_router
from .benchmarks import router as benchmarks_router
from .cortex import router as cortex_router
from .domain import router as domain_router
from .embedding_providers import router as embedding_providers_router
from .events import router as events_router
from .evolve import router as evolve_router
from .graph import router as graph_router
from .health import router as health_router
from .ingest import router as ingest_router
from .memory import router as memory_router
from .metrics import router as metrics_router
from .node import router as node_router
from .ocr_providers import router as ocr_providers_router
from .query import router as query_router
from .reasoning import router as reasoning_router
from .reranker import router as reranker_router
from .storage import router as storage_router

__all__ = [
    "health_router",
    "api_keys_router",
    "auth_router",
    "events_router",
    "benchmarks_router",
    "cortex_router",
    "domain_router",
    "embedding_providers_router",
    "ingest_router",
    "ocr_providers_router",
    "query_router",
    "reasoning_router",
    "reranker_router",
    "memory_router",
    "node_router",
    "evolve_router",
    "graph_router",
    "metrics_router",
    "storage_router",
]

