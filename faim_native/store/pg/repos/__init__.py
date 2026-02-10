"""Store PG repos __init__.py for FAIM-Native."""

from __future__ import annotations

__all__ = [
    "RawRepo",
    "EventRepo",
    "SnapshotRepo",
    "GraphVersionRepo",
    "StorageFileRepo",
]


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name == "RawRepo":
        from .raw_repo import RawRepo

        return RawRepo
    elif name == "EventRepo":
        from .event_repo import EventRepo

        return EventRepo
    elif name == "SnapshotRepo":
        from .snapshot_repo import SnapshotRepo

        return SnapshotRepo
    elif name == "GraphVersionRepo":
        from .graph_version_repo import GraphVersionRepo

        return GraphVersionRepo
    elif name == "StorageFileRepo":
        from .storage_file_repo import StorageFileRepo

        return StorageFileRepo
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
