from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, asc
from sqlalchemy.orm import Session

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import EventRecord
    from faim.Faim_Native.store.pg.models_faim import EventModel
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import EventRecord
    from store.pg.models_faim import EventModel


class EventRepoError(Exception):
    """Base exception for EventRepo errors."""

    pass


class AppendOnlyViolation(EventRepoError):
    """Raised when attempting to modify or delete events."""

    pass


class EventRepo:
    """Repository for append-only event journal operations.

    Events are strictly append-only:
    - append() adds new events
    - No update or delete operations
    - Results are always ordered by seq (auto-assigned by database)

    The seq column provides strict total ordering across all events
    in a graph, enabling reliable pagination and replay.
    """

    def __init__(self, session: Optional[Session] = None, tenant_id: str = "default"):
        self.session = session
        self.tenant_id = tenant_id

    def append(self, session: Session, event: EventRecord) -> EventRecord:
        """Append a pre-built EventRecord to the journal.

        Args:
            session: SQLAlchemy session.
            event: EventRecord instance.

        Returns:
            Updated EventRecord with seq.
        """
        model = EventModel.from_domain(event)
        model.tenant_id = self.tenant_id  # Force override for safety
        session.add(model)
        session.flush()
        return replace(event, seq=model.seq)

    def emit(
        self, session: Session, graph_id: str, kind: str, payload: Dict[str, Any]
    ) -> EventRecord:
        """Build and append an event in one call (Orchestrator friendly).

        Args:
            session: SQLAlchemy session.
            graph_id: Graph identifier.
            kind: Event type.
            payload: Event data.

        Returns:
            Persisted EventRecord.
        """
        from core.contracts.types import EventRecord

        event = EventRecord.create(graph_id=graph_id, kind=kind, payload=payload)
        return self.append(session, event)

    def get_by_id(self, session: Session, id: UUID) -> Optional[EventRecord]:
        """Get event by UUID.

        Args:
            session: SQLAlchemy session.
            id: Event UUID.

        Returns:
            EventRecord if found, None otherwise.
        """
        model = session.query(EventModel).filter(
            and_(
                EventModel.tenant_id == self.tenant_id,
                EventModel.id == id
            )
        ).first()
        return model.to_domain() if model else None

    def get_by_seq(
        self,
        session: Session,
        graph_id: str,
        after_seq: int = 0,
        limit: int = 100,
    ) -> List[EventRecord]:
        """Get events after a sequence number.

        Returns events where seq > after_seq, ordered by seq ASC.
        This enables efficient cursor-based pagination.

        Args:
            session: SQLAlchemy session.
            graph_id: Graph to filter by.
            after_seq: Return events with seq greater than this.
            limit: Maximum events to return.

        Returns:
            List of EventRecords ordered by seq.
        """
        query = (
            session.query(EventModel)
            .filter(
                and_(
                    EventModel.tenant_id == self.tenant_id,
                    EventModel.graph_id == graph_id,
                    EventModel.seq > after_seq
                )
            )
            .order_by(asc(EventModel.seq))
            .limit(limit)
        )

        return [model.to_domain() for model in query.all()]

    def get_latest(self, session: Session, graph_id: str) -> Optional[EventRecord]:
        """Get the most recent event for a graph.

        Args:
            session: SQLAlchemy session.
            graph_id: Graph to filter by.

        Returns:
            Most recent EventRecord, or None if no events.
        """
        model = (
            session.query(EventModel)
            .filter(
                and_(
                    EventModel.tenant_id == self.tenant_id,
                    EventModel.graph_id == graph_id
                )
            )
            .order_by(EventModel.seq.desc())
            .first()
        )

        return model.to_domain() if model else None

    def get_all(
        self,
        session: Session,
        graph_id: str,
        kind: Optional[str] = None,
        limit: int = 1000,
    ) -> List[EventRecord]:
        """Get all events for a graph.

        Results are ordered by seq ASC for deterministic replay.

        Args:
            session: SQLAlchemy session.
            graph_id: Graph to filter by.
            kind: Optional filter by event kind.
            limit: Maximum events to return.

        Returns:
            List of EventRecords ordered by seq.
        """
        query = session.query(EventModel).filter(
            and_(
                EventModel.tenant_id == self.tenant_id,
                EventModel.graph_id == graph_id
            )
        )

        if kind is not None:
            query = query.filter(EventModel.kind == kind)

        query = query.order_by(asc(EventModel.seq)).limit(limit)

        return [model.to_domain() for model in query.all()]

    def count(self, session: Session, graph_id: str) -> int:
        """Count events for a graph.

        Args:
            session: SQLAlchemy session.
            graph_id: Graph to filter by.

        Returns:
            Number of events.
        """
        return session.query(EventModel).filter(
            and_(
                EventModel.tenant_id == self.tenant_id,
                EventModel.graph_id == graph_id
            )
        ).count()

    def get_max_seq(self, session: Session, graph_id: str) -> int:
        """Get the highest sequence number for a graph.

        Args:
            session: SQLAlchemy session.
            graph_id: Graph to filter by.

        Returns:
            Highest seq value, or 0 if no events.
        """
        from sqlalchemy import func

        result = (
            session.query(func.max(EventModel.seq))
            .filter(
                and_(
                    EventModel.tenant_id == self.tenant_id,
                    EventModel.graph_id == graph_id
                )
            )
            .scalar()
        )

        return result or 0
