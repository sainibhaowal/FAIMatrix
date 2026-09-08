"""FAIM-Native Runtime: Context.

Wire repositories, engine, index, and cache for API operations.
"""

from __future__ import annotations

import logging
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
_engine_db_url = None
_SessionLocal = None
_raw_store_plain = None
_raw_store_by_tenant: Dict[str, Any] = {}
logger = logging.getLogger(__name__)


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _is_production_env() -> bool:
    env = os.getenv("FAIM_ENV", "").strip().lower()
    return env in {"prod", "production"}


def _get_engine():
    """Get or create SQLAlchemy engine."""
    global _engine, _engine_db_url, _SessionLocal
    db_url = os.getenv("DATABASE_URL", "sqlite:///Runtime/faim_test.db")
    if _engine is None or _engine_db_url != db_url:
        if _engine is not None:
            try:
                _engine.dispose()
            except Exception:  # nosec B110
                pass
        from sqlalchemy import create_engine

        _engine = create_engine(db_url, echo=False)
        _engine_db_url = db_url
        _SessionLocal = None

        from store.pg.models_faim import create_all_tables

        create_all_tables(_engine)

    return _engine


def _get_session_factory():
    """Get the SQLAlchemy session factory, creating if needed."""
    global _SessionLocal
    current_engine = _get_engine()

    # Recreate session factory if it doesn't exist or is bound to a stale engine
    if _SessionLocal is None or _SessionLocal.kw.get("bind") is not current_engine:
        from sqlalchemy.orm import sessionmaker

        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=current_engine,
        )
    return _SessionLocal


def get_session():
    """Get a new database session."""
    SessionLocal = _get_session_factory()
    return SessionLocal()


def _get_raw_store(tenant_id: str):
    """Get raw store for tenant, optionally wrapped with encryption-at-rest."""
    global _raw_store_plain

    path = os.getenv("FAIM_RAW_STORE_PATH")
    if not path:
        path = str(Path(__file__).resolve().parent.parent / "store" / "raw" / "blobs")

    if _raw_store_plain is None:
        from store.raw.raw_store import RawStore

        _raw_store_plain = RawStore(path)

    production = _is_production_env()
    mode = os.getenv("FAIM_PAYLOAD_CIPHER", "").strip().lower()
    if not mode and _flag("FAIM_ENCRYPTION_AT_REST", default=False):
        mode = "envelope"
    if production and mode in {"", "none", "plain"}:
        raise RuntimeError(
            "Production mode requires encrypted raw store (FAIM_PAYLOAD_CIPHER=envelope and FAIM_ENCRYPTION_AT_REST=true)"
        )
    if mode in {"", "none", "plain"}:
        return _raw_store_plain

    tid = str(tenant_id or "").strip()
    if not tid:
        if production:
            raise RuntimeError(
                "Production mode requires non-empty tenant_id for raw store"
            )
        return _raw_store_plain

    cached = _raw_store_by_tenant.get(tid)
    if cached is not None:
        return cached

    fail_closed = _flag("FAIM_ENCRYPTION_FAIL_CLOSED", default=False)
    try:
        from store.raw.crypto import NoopCipher, build_cipher_from_env
        from store.raw.encrypted_payload_store import EncryptedRawStore

        cipher = build_cipher_from_env(
            mode_override=mode,
            tenant_id=tid,
            session_factory=get_session,
        )
        if isinstance(cipher, NoopCipher):
            if production:
                raise RuntimeError(
                    "Production mode forbids plaintext/noop payload cipher"
                )
            return _raw_store_plain

        wrapped = EncryptedRawStore(
            inner=_raw_store_plain,
            cipher=cipher,
            graph_id=tid,
        )
        _raw_store_by_tenant[tid] = wrapped
        return wrapped
    except Exception as exc:
        if production or fail_closed:
            raise RuntimeError(
                f"Encryption-at-rest initialization failed for tenant={tid}"
            ) from exc
        logger.warning(
            "Encryption-at-rest unavailable for tenant=%s, falling back to plain raw store: %s",
            tid,
            exc,
        )
        return _raw_store_plain


# =============================================================================
# Repository Factory
# =============================================================================


def get_repos(tenant_id: str, session: Any = None) -> Dict[str, Any]:
    """Get all repositories for a tenant.

    Args:
        tenant_id: Tenant identifier.

    Returns:
        Dict with session and all repos.
    """
    # Callers that already own a transaction (for example Cortex writeback)
    # must be able to bind repositories to that exact session.  Creating a
    # second runtime session here can trigger an unnecessary schema bootstrap
    # and breaks transaction atomicity under read-only or externally managed
    # database connections.  Preserve the old behavior when no session is
    # supplied.
    session = session or get_session()

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
        from cache.query_cache import QueryCache

        cache = QueryCache(tenant_id)
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
        "raw_store": _get_raw_store(tenant_id),
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
