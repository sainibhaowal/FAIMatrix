"""FAIM-Native Runtime: Context.

Wire repositories, engine, index, and cache for API operations.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict
from uuid import UUID

# Flexible imports
_parent = Path(__file__).parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))


# =============================================================================
# Database Session Management
# =============================================================================

_engine = None
_SessionLocal = None
_raw_store = None


def _get_engine():
    """Get or create SQLAlchemy engine."""
    global _engine
    if _engine is None:
        from sqlalchemy import create_engine

        db_url = os.getenv("DATABASE_URL", "sqlite:///./faim_test.db")
        _engine = create_engine(db_url, echo=False)

        # Create tables if needed
        from store.pg.models_faim import create_all_tables

        create_all_tables(_engine)

    return _engine


def _get_session_factory():
    """Get or create session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        from sqlalchemy.orm import sessionmaker

        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_get_engine(),
        )
    return _SessionLocal


def get_session():
    """Get a new database session."""
    SessionLocal = _get_session_factory()
    return SessionLocal()


def _get_raw_store():
    """Get or create the shared immutable raw store."""
    global _raw_store
    if _raw_store is None:
        from store.raw.raw_store import RawStore

        path = os.getenv("FAIM_RAW_STORE_PATH")
        if not path:
            path = str(Path(__file__).resolve().parent.parent / "store" / "raw" / "blobs")
        _raw_store = RawStore(path)
    return _raw_store


# =============================================================================
# Repository Factory
# =============================================================================


def get_repos(tenant_id: str) -> Dict[str, Any]:
    """Get all repositories for a tenant.

    Args:
        tenant_id: Tenant identifier.

    Returns:
        Dict with session and all repos.
    """
    session = get_session()

    # Import repos
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.graph_version_repo import GraphVersionRepo
    from store.pg.repos.node_repo import NodeRepo
    from store.pg.repos.raw_repo import RawRepo
    from store.pg.repos.snapshot_repo import SnapshotRepo
    from store.pg.repos.storage_file_repo import StorageFileRepo

    # Try to get index and cache
    index = None
    cache = None

    try:
        # Use a deterministic UUID for the project
        import hashlib

        from index.qdrant_index import FAIMIndex

        project_hash = hashlib.sha256(tenant_id.encode()).digest()[:16]
        project_id = UUID(bytes=project_hash)
        index = FAIMIndex(project_id)
    except Exception:  # nosec B110 - Graceful degradation if index not available
        pass

    try:
        import hashlib

        from cache.query_cache import QueryCache

        cache_hash = hashlib.sha256(tenant_id.encode()).digest()[:16]
        cache_id = UUID(bytes=cache_hash)
        cache = QueryCache(cache_id)
    except Exception:  # nosec B110 - Graceful degradation if cache not available
        pass

    return {
        "session": session,
        "tenant_id": tenant_id,
        "node_repo": NodeRepo(session, tenant_id=tenant_id),
        "edge_repo": EdgeRepo(session, tenant_id=tenant_id),
        "event_repo": EventRepo(tenant_id=tenant_id),
        "gv_repo": GraphVersionRepo(tenant_id=tenant_id),
        "snapshot_repo": SnapshotRepo(tenant_id=tenant_id),
        "raw_repo": RawRepo(tenant_id=tenant_id),
        "storage_file_repo": StorageFileRepo(tenant_id=tenant_id),
        "raw_store": _get_raw_store(),
        "index": index,
        "cache": cache,
    }


def close_session(session) -> None:
    """Close a database session."""
    if session:
        session.close()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "get_session",
    "get_repos",
    "close_session",
]
