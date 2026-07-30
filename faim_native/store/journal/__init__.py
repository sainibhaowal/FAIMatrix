"""Store journal __init__.py for FAIM-Native."""

from __future__ import annotations

__all__ = [
    "EventJournal",
    "EventJournalError",
    "ChecksumMismatchError",
]


def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name in ("EventJournal", "EventJournalError", "ChecksumMismatchError"):
        from .event_journal import (
            ChecksumMismatchError,
            EventJournal,
            EventJournalError,
        )

        mapping = {
            "EventJournal": EventJournal,
            "EventJournalError": EventJournalError,
            "ChecksumMismatchError": ChecksumMismatchError,
        }
        return mapping[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
