from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import Session

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import SnapshotRecord
    from faim.Faim_Native.store.pg.models_faim import SnapshotModel
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import SnapshotRecord
    from store.pg.models_faim import SnapshotModel


class SnapshotRepo:
    """Repository for graph snapshots and integrity receipts."""

    def __init__(self, session: Optional[Session] = None, tenant_id: str = "default"):
        self.session = session
        self.tenant_id = tenant_id

    def create(self, session: Session, snapshot: SnapshotRecord) -> SnapshotRecord:
        """Create a new snapshot record.

        Args:
            session: SQLAlchemy session.
            snapshot: SnapshotRecord to create.

        Returns:
            Created SnapshotRecord.
        """
        model = SnapshotModel.from_domain(snapshot)
        model.tenant_id = self.tenant_id  # Force override
        session.add(model)
        session.flush()
        return model.to_domain()

    def get_by_id(self, session: Session, id: UUID) -> Optional[SnapshotRecord]:
        """Get snapshot by UUID.

        Args:
            session: SQLAlchemy session.
            id: Snapshot UUID.

        Returns:
            SnapshotRecord if found, None otherwise.
        """
        model = session.query(SnapshotModel).filter(
            and_(
                SnapshotModel.tenant_id == self.tenant_id,
                SnapshotModel.id == id
            )
        ).first()
        return model.to_domain() if model else None

    def get_latest(self, session: Session, graph_id: str) -> Optional[SnapshotRecord]:
        """Get the most recent snapshot for a graph.

        Args:
            session: SQLAlchemy session.
            graph_id: Graph to filter by.

        Returns:
            Most recent SnapshotRecord, or None if no snapshots.
        """
        model = (
            session.query(SnapshotModel)
            .filter(
                and_(
                    SnapshotModel.tenant_id == self.tenant_id,
                    SnapshotModel.graph_id == graph_id
                )
            )
            .order_by(desc(SnapshotModel.created_at))
            .first()
        )

        return model.to_domain() if model else None

    def list_by_graph(
        self,
        session: Session,
        graph_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SnapshotRecord]:
        """List snapshots for a graph.

        Results are ordered by created_at DESC (newest first).

        Args:
            session: SQLAlchemy session.
            graph_id: Graph to filter by.
            limit: Maximum records to return.
            offset: Number of records to skip.

        Returns:
            List of SnapshotRecords.
        """
        query = (
            session.query(SnapshotModel)
            .filter(
                and_(
                    SnapshotModel.tenant_id == self.tenant_id,
                    SnapshotModel.graph_id == graph_id
                )
            )
            .order_by(desc(SnapshotModel.created_at))
            .limit(limit)
            .offset(offset)
        )

        return [model.to_domain() for model in query.all()]

    def list_by_version_range(
        self,
        session: Session,
        graph_id: str,
        min_version: int,
        max_version: int,
    ) -> List[SnapshotRecord]:
        """List snapshots within a graph version range.

        Args:
            session: SQLAlchemy session.
            graph_id: Graph to filter by.
            min_version: Minimum graph_version (inclusive).
            max_version: Maximum graph_version (inclusive).

        Returns:
            List of SnapshotRecords ordered by graph_version ASC.
        """
        query = (
            session.query(SnapshotModel)
            .filter(
                and_(
                    SnapshotModel.tenant_id == self.tenant_id,
                    SnapshotModel.graph_id == graph_id,
                    SnapshotModel.graph_version >= min_version,
                    SnapshotModel.graph_version <= max_version
                )
            )
            .order_by(asc(SnapshotModel.graph_version))
        )

        return [model.to_domain() for model in query.all()]

    def count(self, session: Session, graph_id: str) -> int:
        """Count snapshots for a graph.

        Args:
            session: SQLAlchemy session.
            graph_id: Graph to filter by.

        Returns:
            Number of snapshots.
        """
        return (
            session.query(SnapshotModel)
            .filter(
                and_(
                    SnapshotModel.tenant_id == self.tenant_id,
                    SnapshotModel.graph_id == graph_id
                )
            )
            .count()
        )

    def get_by_version(
        self,
        session: Session,
        graph_id: str,
        graph_version: int,
    ) -> Optional[SnapshotRecord]:
        """Get snapshot by exact graph version.

        Args:
            session: SQLAlchemy session.
            graph_id: Graph to filter by.
            graph_version: Exact version to find.

        Returns:
            SnapshotRecord if found, None otherwise.
        """
        model = (
            session.query(SnapshotModel)
            .filter(
                and_(
                    SnapshotModel.tenant_id == self.tenant_id,
                    SnapshotModel.graph_id == graph_id,
                    SnapshotModel.graph_version == graph_version
                )
            )
            .first()
        )

        return model.to_domain() if model else None
