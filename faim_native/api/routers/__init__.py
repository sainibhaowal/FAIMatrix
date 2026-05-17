"""FAIM-Native API: Routers Package."""

from .admin import router as admin_router
from .api_keys import router as api_keys_router
from .auth import router as auth_router
from .benchmarks import router as benchmarks_router
from .cortex import router as cortex_router
from .events import router as events_router
from .evolve import router as evolve_router
from .graph import router as graph_router
from .health import router as health_router
from .ingest import router as ingest_router
from .memory import router as memory_router
from .metrics import router as metrics_router
from .node import router as node_router
from .query import router as query_router
from .storage import router as storage_router

__all__ = [
    "health_router",
    "api_keys_router",
    "auth_router",
    "events_router",
    "benchmarks_router",
    "cortex_router",
    "ingest_router",
    "query_router",
    "memory_router",
    "node_router",
    "evolve_router",
    "graph_router",
    "metrics_router",
    "admin_router",
    "storage_router",
]
