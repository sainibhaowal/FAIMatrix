# =============================================================================
# FAIM — BACKENDS FACTORY
# =============================================================================
# File: faim/config/backends.py
#
# PURPOSE
#   - Production-ready state factory that creates backends based on environment
#   - Supports Postgres, Qdrant, Redis backends
#   - Multi-tenant isolation via project_id
#
# USAGE
#   from faim.config.backends import get_faim_context
#   ctx = get_faim_context(project_id, db_session)
# =============================================================================

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from faim.data.redis.redis_client import RedisCache
    from faim.data.storage.postgres_store import PostgresStore as FAIMStore
    from faim.data.storage.qdrant_store import QdrantVectorStore

logger = logging.getLogger(__name__)


# =============================================================================
# BACKEND CONFIGURATION
# =============================================================================


def _get_storage_backend() -> str:
    """Get storage backend from environment."""
    return os.getenv("FAIM_STORAGE_BACKEND", "postgres").lower()


def _get_vector_backend() -> str:
    """Get vector backend from environment."""
    return os.getenv("FAIM_VECTOR_BACKEND", "qdrant").lower()


def _get_cache_backend() -> str:
    """Get cache backend from environment."""
    return os.getenv("FAIM_CACHE_BACKEND", "redis").lower()


def _is_production() -> bool:
    """Check if running in production mode."""
    mode = os.getenv("FAIM_MODE", "dev").lower()
    return mode in ("production", "prod", "staging")


# =============================================================================
# CONTEXT DATACLASS
# =============================================================================


@dataclass
class FAIMContext:
    """Production FAIM context with all backends initialized for a project.

    This provides tenant-isolated access to:
    - Node/Payload storage (Postgres or SQLite)
    - Vector search (Qdrant or in-memory)
    - Caching (Redis or in-memory)
    """

    project_id: UUID
    db: Session
    store: "FAIMStore"
    vectors: Optional["QdrantVectorStore"]
    cache: Optional["RedisCache"]


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def get_faim_context(
    project_id: UUID,
    db: Session,
    *,
    dim: int = 384,
) -> FAIMContext:
    """Create a production FAIM context for a project.

    Args:
        project_id: The project UUID for tenant isolation
        db: SQLAlchemy database session
        dim: Vector dimension (default 384 for MiniLM)

    Returns:
        FAIMContext with all backends initialized
    """
    # ==========================================================================
    # STORAGE BACKEND (Postgres only)
    # ==========================================================================
    from faim.data.storage.postgres_store import PostgresStore

    store = PostgresStore(db=db, project_id=project_id)
    logger.info(f"Using Postgres storage backend for project {project_id}")

    # ==========================================================================
    # VECTOR BACKEND
    # ==========================================================================
    vectors = None
    if _get_vector_backend() == "qdrant":
        try:
            from faim.data.storage.qdrant_store import QdrantVectorStore

            vectors = QdrantVectorStore(project_id=project_id, dim=dim)
            logger.info(f"Using Qdrant vector backend for project {project_id}")
        except Exception as e:
            logger.warning(f"Failed to initialize Qdrant: {e}, using in-memory fallback")

    # ==========================================================================
    # CACHE BACKEND
    # ==========================================================================
    cache = None
    if _get_cache_backend() == "redis":
        try:
            from faim.data.redis.redis_client import RedisCache

            cache = RedisCache(project_id=project_id)
            logger.info(f"Using Redis cache backend for project {project_id}")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache: {e}")

    return FAIMContext(
        project_id=project_id,
        db=db,
        store=store,
        vectors=vectors,
        cache=cache,
    )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def get_postgres_store(project_id: UUID, db: Session):
    """Get a Postgres store instance directly."""
    from faim.data.storage.postgres_store import PostgresStore

    return PostgresStore(db=db, project_id=project_id)


def get_qdrant_store(project_id: UUID, dim: int = 384):
    """Get a Qdrant store instance directly."""
    from faim.data.storage.qdrant_store import QdrantVectorStore

    return QdrantVectorStore(project_id=project_id, dim=dim)


def get_redis_cache(project_id: UUID):
    """Get a Redis cache instance directly."""
    from faim.data.redis.redis_client import RedisCache

    return RedisCache(project_id=project_id)


# Alias for backwards compatibility
get_store = get_postgres_store
