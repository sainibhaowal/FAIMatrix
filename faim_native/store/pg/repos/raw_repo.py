from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, asc
from sqlalchemy.orm import Session

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import RawRef
    from faim.Faim_Native.store.pg.models_faim import RawRefModel
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import RawRef

    from store.pg.models_faim import RawRefModel


class RawRepo:
    """Repository for raw blob tracking."""

    def __init__(self, session: Optional[Session] = None, tenant_id: str = "default"):
        self.session = session
        self.tenant_id = tenant_id

    def create(self, session: Session, raw_ref: RawRef) -> RawRef:
        """Create a new RawRef record.

        If a record with the same sha256 already exists, returns existing.

        Args:
            session: SQLAlchemy session.
            raw_ref: RawRef to create.

        Returns:
            Created or existing RawRef.
        """
        # Check for existing by sha256 (idempotent)
        existing = self.get_by_sha(session, raw_ref.sha256)
        if existing is not None:
            return existing

        model = RawRefModel.from_domain(raw_ref)
        model.tenant_id = self.tenant_id
        session.add(model)
        session.flush()
        return model.to_domain()

    def get_by_id(self, session: Session, id: UUID) -> Optional[RawRef]:
        """Get RawRef by UUID.

        Args:
            session: SQLAlchemy session.
            id: UUID to look up.

        Returns:
            RawRef if found, None otherwise.
        """
        model = (
            session.query(RawRefModel)
            .filter(and_(RawRefModel.tenant_id == self.tenant_id, RawRefModel.id == id))
            .first()
        )
        return model.to_domain() if model else None

    def get_by_sha(self, session: Session, sha256: str) -> Optional[RawRef]:
        """Get RawRef by SHA256 hash.

        Args:
            session: SQLAlchemy session.
            sha256: SHA256 hex digest.

        Returns:
            RawRef if found, None otherwise.
        """
        model = (
            session.query(RawRefModel)
            .filter(
                and_(
                    RawRefModel.tenant_id == self.tenant_id,
                    RawRefModel.sha256 == sha256,
                )
            )
            .first()
        )
        return model.to_domain() if model else None

    def list_all(
        self,
        session: Session,
        graph_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RawRef]:
        """List RawRefs with pagination and optional graph filter.

        Results are ordered by created_at ASC, id ASC for deterministic paging.

        Args:
            session: SQLAlchemy session.
            graph_id: Optional filter by graph.
            limit: Maximum records to return.
            offset: Number of records to skip.

        Returns:
            List of RawRef objects.
        """
        query = session.query(RawRefModel)

        if graph_id is not None:
            query = query.filter(
                and_(
                    RawRefModel.tenant_id == self.tenant_id,
                    RawRefModel.graph_id == graph_id,
                )
            )
        else:
            query = query.filter(RawRefModel.tenant_id == self.tenant_id)

        # Deterministic ordering
        query = query.order_by(asc(RawRefModel.created_at), asc(RawRefModel.id))
        query = query.limit(limit).offset(offset)

        return [model.to_domain() for model in query.all()]

    def count(self, session: Session, graph_id: Optional[str] = None) -> int:
        """Count RawRef records.

        Args:
            session: SQLAlchemy session.
            graph_id: Optional filter by graph.

        Returns:
            Number of records.
        """
        query = session.query(RawRefModel)

        if graph_id is not None:
            query = query.filter(
                and_(
                    RawRefModel.tenant_id == self.tenant_id,
                    RawRefModel.graph_id == graph_id,
                )
            )
        else:
            query = query.filter(RawRefModel.tenant_id == self.tenant_id)

        return query.count()

    def exists(self, session: Session, sha256: str) -> bool:
        """Check if a RawRef exists by SHA256.

        Args:
            session: SQLAlchemy session.
            sha256: SHA256 hex digest.

        Returns:
            True if exists, False otherwise.
        """
        return (
            session.query(RawRefModel)
            .filter(
                and_(
                    RawRefModel.tenant_id == self.tenant_id,
                    RawRefModel.sha256 == sha256,
                )
            )
            .first()
            is not None
        )

    def delete_by_id(self, session: Session, id: UUID) -> bool:
        """Delete RawRef by UUID.

        Returns:
            True if deleted, False if not found.
        """
        model = (
            session.query(RawRefModel)
            .filter(
                and_(
                    RawRefModel.tenant_id == self.tenant_id,
                    RawRefModel.id == id,
                )
            )
            .first()
        )
        if model is None:
            return False
        session.delete(model)
        session.flush()
        return True
