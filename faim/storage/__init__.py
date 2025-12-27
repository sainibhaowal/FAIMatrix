"""Storage backends for FAIM."""

from __future__ import annotations

from .sqlite_store import SqliteStore

__all__ = ["SqliteStore"]
