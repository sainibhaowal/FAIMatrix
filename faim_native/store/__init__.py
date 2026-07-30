"""Store module __init__.py for FAIM-Native.

Uses lazy imports to avoid circular dependency issues.
"""

from __future__ import annotations

# Lazy imports - only import when accessed
__all__ = [
    # Core store
    "RawStore",
    # Session management
    "SessionFactory",
    "get_engine",
    "atomic",
    # ORM models
    "Base",
    "RawRefModel",
    "EventModel",
    "SnapshotModel",
    "GraphVersionModel",
    "StorageFileModel",
    "TenantCryptoKey",
    "create_all_tables",
    # Repositories
    "RawRepo",
    "EventRepo",
    "SnapshotRepo",
    "GraphVersionRepo",
    "StorageFileRepo",
    # Journal
    "EventJournal",
]


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name == "RawStore":
        from .raw.raw_store import RawStore

        return RawStore
    elif name == "SessionFactory":
        from .pg.session import SessionFactory

        return SessionFactory
    elif name == "get_engine":
        from .pg.session import get_engine

        return get_engine
    elif name == "atomic":
        from .pg.session import atomic

        return atomic
    elif name in (
        "Base",
        "RawRefModel",
        "EventModel",
        "SnapshotModel",
        "GraphVersionModel",
        "StorageFileModel",
        "TenantCryptoKey",
        "create_all_tables",
    ):
        from . import pg  # noqa: F401
        from .pg import models_crypto, models_faim

        if hasattr(models_faim, name):
            return getattr(models_faim, name)
        return getattr(models_crypto, name)
    elif name == "RawRepo":
        from .pg.repos.raw_repo import RawRepo

        return RawRepo
    elif name == "EventRepo":
        from .pg.repos.event_repo import EventRepo

        return EventRepo
    elif name == "SnapshotRepo":
        from .pg.repos.snapshot_repo import SnapshotRepo

        return SnapshotRepo
    elif name == "GraphVersionRepo":
        from .pg.repos.graph_version_repo import GraphVersionRepo

        return GraphVersionRepo
    elif name == "StorageFileRepo":
        from .pg.repos.storage_file_repo import StorageFileRepo

        return StorageFileRepo
    elif name == "EventJournal":
        from .journal.event_journal import EventJournal

        return EventJournal
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
