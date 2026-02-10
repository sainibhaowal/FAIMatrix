"""Store PG __init__.py for FAIM-Native."""

from __future__ import annotations

__all__ = [
    "SessionFactory",
    "get_engine",
    "atomic",
    "Base",
    "RawRefModel",
    "EventModel",
    "SnapshotModel",
    "GraphVersionModel",
    "TenantCryptoKey",
    "create_all_tables",
    "drop_all_tables",
]


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name in ("SessionFactory", "get_engine", "atomic"):
        from .session import SessionFactory, atomic, get_engine

        mapping = {
            "SessionFactory": SessionFactory,
            "get_engine": get_engine,
            "atomic": atomic,
        }
        return mapping[name]
    elif name in (
        "Base",
        "RawRefModel",
        "EventModel",
        "SnapshotModel",
        "GraphVersionModel",
        "TenantCryptoKey",
        "create_all_tables",
        "drop_all_tables",
    ):
        from . import models_crypto, models_faim

        if hasattr(models_faim, name):
            return getattr(models_faim, name)
        return getattr(models_crypto, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
