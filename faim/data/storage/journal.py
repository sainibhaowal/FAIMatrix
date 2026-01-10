"""Event journal interfaces for FAIM.

Implements an append-only EventJournal used for audit and replay.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict

from faim.core.types import GraphId


@dataclass(frozen=True)
class JournalEvent:
    """Single journal entry representing a state-changing operation."""

    ts: float
    graph_id: GraphId
    op: str
    data: Dict[str, Any]


class EventJournal(ABC):
    """Abstract append-only journal."""

    @abstractmethod
    def append(self, event: JournalEvent) -> None:
        """Append a new journal event."""
