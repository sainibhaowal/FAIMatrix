# =============================================================================
# FAIM — PRODUCTION STATE
# =============================================================================
# File: faim/api/state.py
#
# PURPOSE
#   - Process-wide state using PostgresStore (no SQLite)
#   - Canonical GraphId coercion helpers
#   - Store helpers used by API layer
#
# NOTE: This file provides backward compatibility for code that imports
# from state.py. For new code, use production_state.py directly.
# =============================================================================

from __future__ import annotations

from typing import Iterable, cast

from faim.core.graph import InMemoryGraphRegistry
from faim.core.types import GraphId, NodeRecord

# =============================================================================
# SECTION 0 — REGISTRY (OPTIONAL CACHE)
# =============================================================================

GRAPH_REGISTRY = InMemoryGraphRegistry()


# =============================================================================
# SECTION 1 — TYPE COERCION
# =============================================================================


def _gid(s: str) -> GraphId:
    """Canonical coercion to GraphId."""
    try:
        v = s if isinstance(s, str) else str(s)
    except Exception:
        v = ""
    return cast(GraphId, v)


# =============================================================================
# SECTION 2 — STORE HELPERS (DEPRECATED - Use production_state.py)
# =============================================================================
# These functions exist for backward compatibility only.
# New code should use get_faim_context() from production_state.py.

_lazy_store = None


def _get_default_store():
    """Get default PostgresStore (lazy initialization).

    DEPRECATED: Use get_faim_context() from production_state.py for proper
    multi-tenant isolation with project_id.
    """
    global _lazy_store
    if _lazy_store is None:
        import logging

        logging.warning(
            "Using legacy state.py store. "
            "For multi-tenant isolation, use production_state.get_faim_context()."
        )
        # Import here to avoid circular imports
        from faim.db import SessionLocal
        from faim.storage.postgres_store import PostgresStore
        from uuid import UUID

        # Use a default project ID for legacy compatibility
        # In production, always use get_faim_context() with proper project_id
        default_project_id = UUID("00000000-0000-0000-0000-000000000000")
        db = SessionLocal()
        _lazy_store = PostgresStore(db=db, project_id=default_project_id)
    return _lazy_store


def iter_nodes_from_store(graph_id: str) -> Iterable[NodeRecord]:
    """Iterate nodes from store.

    DEPRECATED: Use get_faim_context() for proper multi-tenant access.
    """
    store = _get_default_store()
    return store.iter_graph(_gid(graph_id))


def count_nodes_from_store(graph_id: str) -> int:
    """Count nodes in store.

    DEPRECATED: Use get_faim_context() for proper multi-tenant access.
    """
    try:
        store = _get_default_store()
        return store.count(_gid(graph_id))
    except Exception:
        return 0


def ensure_registry_loaded(graph_id: str) -> None:
    """Best-effort cache warmup.

    DEPRECATED: Use get_faim_context() for proper multi-tenant access.
    """
    try:
        g = GRAPH_REGISTRY.get_or_create(_gid(graph_id))
        nodes_map = getattr(g, "nodes", None)
        if nodes_map is None or len(nodes_map) > 0:
            return

        raw_nodes = list(iter_nodes_from_store(graph_id))

        def _node_key(n: object) -> str:
            v = getattr(n, "id", None) or getattr(n, "node_id", None)
            try:
                return str(v) if v is not None else ""
            except Exception:
                return ""

        raw_nodes.sort(key=_node_key)

        for n in raw_nodes:
            nid = getattr(n, "id", None) or getattr(n, "node_id", None)
            if nid is None:
                continue
            nodes_map[nid] = n
    except Exception:
        return
