from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import GraphVersion
    from faim.Faim_Native.store.pg.models_faim import GraphVersionModel
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import GraphVersion
    from store.pg.models_faim import GraphVersionModel


class GraphVersionRepo:
    """Repository for graph versioning and locking."""

    def __init__(self, session: Optional[Session] = None, tenant_id: str = "default"):
        self.session = session
        self.tenant_id = tenant_id

    def _resolve_session(self, session: Optional[Session]) -> Session:
        """Get a usable session from arg, instance, or new session."""
        resolved = session or self.session
        if resolved is None:
            from store.pg.session import get_session

            resolved = get_session()
        return resolved

    def get_version(self, session: Optional[Session], graph_id: str) -> int:
        """Get the current version for a graph.

        Returns 0 if the graph has no version record yet.

        Args:
            session: SQLAlchemy session (optional, uses self.session if None).
            graph_id: Graph identifier.

        Returns:
            Current version number (0 if none).
        """
        session = self._resolve_session(session)
        model = (
            session.query(GraphVersionModel)
            .filter(
                and_(
                    GraphVersionModel.tenant_id == self.tenant_id,
                    GraphVersionModel.graph_id == graph_id,
                )
            )
            .first()
        )

        return model.version if model else 0

    def get(
        self,
        session: Optional[Session] = None,
        graph_id: Optional[str] = None,
    ) -> Optional[GraphVersion]:
        """Get the full GraphVersion record.

        Args:
            session: SQLAlchemy session (optional).
            graph_id: Graph identifier.

        Returns:
            GraphVersion if exists, None otherwise.
        """
        if graph_id is None and isinstance(session, str):
            graph_id = session
            session = None
        if graph_id is None:
            raise ValueError("graph_id is required")

        session = self._resolve_session(session)
        model = (
            session.query(GraphVersionModel)
            .filter(
                and_(
                    GraphVersionModel.tenant_id == self.tenant_id,
                    GraphVersionModel.graph_id == graph_id,
                )
            )
            .first()
        )

        return model.to_domain() if model else None

    def get_or_create(
        self,
        session: Optional[Session],
        graph_id: str,
    ) -> GraphVersionModel:
        """Get graph version row; create version=0 row if missing."""
        session = self._resolve_session(session)
        model = (
            session.query(GraphVersionModel)
            .filter(
                and_(
                    GraphVersionModel.tenant_id == self.tenant_id,
                    GraphVersionModel.graph_id == graph_id,
                )
            )
            .first()
        )
        if model is None:
            model = GraphVersionModel(
                tenant_id=self.tenant_id,
                graph_id=graph_id,
                version=0,
                reason="init",
                updated_at=datetime.now(timezone.utc),
            )
            session.add(model)
            session.flush()
        return model

    def bump(
        self,
        session: Optional[Session],
        graph_id: str,
        reason: str,
        tenant_id: str = "__test__",
    ) -> int:
        """Increment the graph version.

        Creates a new record if none exists, otherwise increments.

        Args:
            session: SQLAlchemy session (optional).
            graph_id: Graph identifier.
            reason: Reason for the version bump.
            tenant_id: Tenant identifier.

        Returns:
            New version number after bump.
        """
        session = self._resolve_session(session)
        model = (
            session.query(GraphVersionModel)
            .filter(
                and_(
                    GraphVersionModel.tenant_id == self.tenant_id,
                    GraphVersionModel.graph_id == graph_id,
                )
            )
            .first()
        )

        now = datetime.now(timezone.utc)

        if model:
            model.version += 1
            model.reason = reason
            model.updated_at = now
            new_version = model.version
        else:
            new_version = 1
            model = GraphVersionModel(
                tenant_id=self.tenant_id,
                graph_id=graph_id,
                version=new_version,
                reason=reason,
                updated_at=now,
            )
            session.add(model)

        session.flush()
        return new_version

    def set_version(
        self,
        session: Session,
        graph_id: str,
        version: int,
        reason: str,
        tenant_id: str = "__test__",
    ) -> None:
        """Set the graph version explicitly (use with caution).

        This is primarily for testing or migration scenarios.

        Args:
            session: SQLAlchemy session.
            graph_id: Graph identifier.
            version: Version to set.
            reason: Reason for setting.
        """
        now = datetime.now(timezone.utc)

        model = (
            session.query(GraphVersionModel)
            .filter(
                and_(
                    GraphVersionModel.tenant_id == self.tenant_id,
                    GraphVersionModel.graph_id == graph_id,
                )
            )
            .first()
        )

        if model:
            model.version = version
            model.reason = reason
            model.updated_at = now
        else:
            model = GraphVersionModel(
                tenant_id=self.tenant_id,
                graph_id=graph_id,
                version=version,
                reason=reason,
                updated_at=now,
            )
            session.add(model)

        session.flush()
