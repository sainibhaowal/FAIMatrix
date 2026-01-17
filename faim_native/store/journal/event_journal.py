from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import EventRecord
    from faim.Faim_Native.store.pg.repos.event_repo import EventRepo
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import EventRecord
    from store.pg.repos.event_repo import EventRepo


logger = logging.getLogger(__name__)


# =============================================================================
# Stage-9: Payload Bounds
# =============================================================================

# Default max payload size (can be overridden via FAIM_EVENT_PAYLOAD_MAX_BYTES)
DEFAULT_MAX_PAYLOAD_BYTES = 4096


def get_max_payload_bytes() -> int:
    """Get max payload size from config or env."""
    try:
        return int(
            os.getenv("FAIM_EVENT_PAYLOAD_MAX_BYTES", str(DEFAULT_MAX_PAYLOAD_BYTES))
        )
    except ValueError:
        return DEFAULT_MAX_PAYLOAD_BYTES


def truncate_payload(
    payload: Dict[str, Any], max_bytes: Optional[int] = None
) -> Dict[str, Any]:
    """Truncate payload to fit within max bytes.

    Args:
        payload: Event payload dict.
        max_bytes: Max size in bytes (default from config).

    Returns:
        Truncated payload dict.
    """
    if max_bytes is None:
        max_bytes = get_max_payload_bytes()

    # Serialize to check size
    payload_json = json.dumps(payload, default=str)

    if len(payload_json) <= max_bytes:
        return payload

    # Truncate by removing large string values
    truncated = {}
    for key, value in payload.items():
        if isinstance(value, str) and len(value) > 100:
            truncated[key] = value[:100] + "...[truncated]"
        elif isinstance(value, list) and len(value) > 10:
            truncated[key] = value[:10] + ["...[truncated]"]
        elif isinstance(value, dict):
            # Keep first 5 keys
            truncated[key] = dict(list(value.items())[:5])
        else:
            truncated[key] = value

    truncated["_truncated"] = True
    truncated["_original_size"] = len(payload_json)

    logger.warning(
        f"Payload truncated: {len(payload_json)} bytes -> {len(json.dumps(truncated))} bytes"
    )

    return truncated


class EventJournalError(Exception):
    """Base exception for EventJournal errors."""

    pass


class ChecksumMismatchError(EventJournalError):
    """Raised when event checksum verification fails."""

    pass


class EventJournal:
    """High-level append-only event journal.

    Provides a clean interface for appending and reading events
    with automatic checksum verification.

    The journal enforces:
    - Append-only writes (no updates or deletes)
    - Strict ordering by sequence number
    - Checksum integrity for all events

    Usage:
        journal = EventJournal(session)

        # Append an event
        event = EventRecord.create("graph1", "node_created", {"node_id": "abc"})
        saved = journal.append(event)

        # Read events
        events = journal.read("graph1", after_seq=0, limit=100)
    """

    def __init__(self, session: Session) -> None:
        """Initialize journal with a database session.

        Args:
            session: SQLAlchemy session for database operations.
        """
        self._session = session
        self._repo = EventRepo()

    def append(self, event: EventRecord) -> EventRecord:
        """Append an event to the journal.

        The event's checksum is verified before writing.
        The seq field will be auto-assigned by the database.

        Args:
            event: EventRecord to append.

        Returns:
            EventRecord with seq populated.

        Raises:
            ChecksumMismatchError: If event checksum is invalid.
        """
        # Verify checksum before storing
        if not event.verify_checksum():
            raise ChecksumMismatchError(
                f"Event checksum verification failed: {event.id}"
            )

        return self._repo.append(self._session, event)

    def read(
        self,
        graph_id: str,
        after_seq: int = 0,
        limit: int = 100,
    ) -> List[EventRecord]:
        """Read events from the journal.

        Returns events where seq > after_seq, ordered by seq ASC.
        Enables efficient cursor-based pagination.

        Args:
            graph_id: Graph to read events for.
            after_seq: Return events with seq > this value.
            limit: Maximum events to return.

        Returns:
            List of EventRecords ordered by seq.
        """
        return self._repo.get_by_seq(
            self._session,
            graph_id,
            after_seq=after_seq,
            limit=limit,
        )

    def get_latest(self, graph_id: str) -> Optional[EventRecord]:
        """Get the most recent event for a graph.

        Args:
            graph_id: Graph to get latest event for.

        Returns:
            Most recent EventRecord, or None if no events.
        """
        return self._repo.get_latest(self._session, graph_id)

    def get_all(
        self,
        graph_id: str,
        kind: Optional[str] = None,
        limit: int = 1000,
    ) -> List[EventRecord]:
        """Get all events for a graph.

        Args:
            graph_id: Graph to get events for.
            kind: Optional filter by event kind.
            limit: Maximum events to return.

        Returns:
            List of all events ordered by seq.
        """
        return self._repo.get_all(
            self._session,
            graph_id,
            kind=kind,
            limit=limit,
        )

    def count(self, graph_id: str) -> int:
        """Count events for a graph.

        Args:
            graph_id: Graph to count events for.

        Returns:
            Number of events.
        """
        return self._repo.count(self._session, graph_id)

    def verify_integrity(self, graph_id: str) -> bool:
        """Verify all events in a graph have valid checksums.

        Args:
            graph_id: Graph to verify.

        Returns:
            True if all checksums valid, False otherwise.
        """
        events = self.get_all(graph_id, limit=10000)
        return all(e.verify_checksum() for e in events)
