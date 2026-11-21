"""FAIM-Native API: Routers Package."""

from .api_keys import router as api_keys_router
from .auth import router as auth_router
from .embedding_providers import router as embedding_providers_router
from .events import router as events_router
from .evolve import router as evolve_router
from .graph import router as graph_router
from .health import router as health_router
from .ingest import router as ingest_router
from .mcp import router as mcp_router
from .memory import router as memory_router
from .metrics import router as metrics_router
from .node import router as node_router
from .oauth import router as oauth_router
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
    "embedding_providers_router",
    "ingest_router",
    "mcp_router",
    "oauth_router",
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
