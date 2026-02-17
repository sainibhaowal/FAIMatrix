from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union
from uuid import UUID

from sqlalchemy import and_, asc
from sqlalchemy.orm import Session

# Flexible imports
try:
    from faim.Faim_Native.store.pg.models_faim import (
        GraphVersionModel,
        JobModel,
        SelfEvolutionStateModel,
    )
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from store.pg.models_faim import GraphVersionModel, JobModel, SelfEvolutionStateModel


@dataclass(frozen=True)
class SelfEvolutionDueGraph:
    """Derived due-graph candidate from durable scheduler state."""

    graph_id: str
    current_version: int
    last_seen_version: int
    last_evolved_version: int
    version_delta: int
    last_evolved_at: Optional[datetime]
    last_enqueued_job_id: Optional[str]


class SelfEvolutionStateRepo:
    """Repository for durable self-evolution scheduler state."""

    def __init__(self, session: Optional[Session] = None, tenant_id: str = "default"):
        self.session = session
        self.tenant_id = tenant_id

    def _resolve_session(self, session: Optional[Session]) -> Session:
        resolved = session or self.session
        if resolved is None:
            from store.pg.session import get_session

            resolved = get_session()
        return resolved

    @staticmethod
    def _coerce_uuid(value: Union[UUID, str, None]) -> Optional[UUID]:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            return None

    @staticmethod
    def _normalize_dt(value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def get(
        self,
        graph_id: str,
        session: Optional[Session] = None,
    ) -> Optional[SelfEvolutionStateModel]:
        """Get persisted scheduler state for tenant+graph."""
        sess = self._resolve_session(session)
        return (
            sess.query(SelfEvolutionStateModel)
            .filter(
                and_(
                    SelfEvolutionStateModel.tenant_id == self.tenant_id,
                    SelfEvolutionStateModel.graph_id == graph_id,
                )
            )
            .first()
        )

    def get_or_create(
        self,
        graph_id: str,
        session: Optional[Session] = None,
    ) -> SelfEvolutionStateModel:
        """Get state row or create initialized defaults."""
        sess = self._resolve_session(session)
        row = self.get(graph_id, session=sess)
        if row is not None:
            return row

        now = datetime.now(timezone.utc)
        row = SelfEvolutionStateModel(
            tenant_id=self.tenant_id,
            graph_id=graph_id,
            last_seen_version=0,
            last_evolved_version=0,
            last_evolved_at=None,
            last_enqueued_job_id=None,
            updated_at=now,
        )
        sess.add(row)
        sess.flush()
        return row

    def mark_seen_version(
        self,
        graph_id: str,
        seen_version: int,
        session: Optional[Session] = None,
    ) -> SelfEvolutionStateModel:
        """Monotonically record last seen graph version."""
        sess = self._resolve_session(session)
        row = self.get_or_create(graph_id=graph_id, session=sess)
        normalized = max(0, int(seen_version))
        if normalized > int(row.last_seen_version or 0):
            row.last_seen_version = normalized
        row.updated_at = datetime.now(timezone.utc)
        sess.flush()
        return row

    def mark_enqueued(
        self,
        graph_id: str,
        job_id: Union[UUID, str],
        *,
        seen_version: Optional[int] = None,
        session: Optional[Session] = None,
    ) -> SelfEvolutionStateModel:
        """Record enqueue metadata idempotently for a graph."""
        sess = self._resolve_session(session)
        row = self.get_or_create(graph_id=graph_id, session=sess)

        if seen_version is not None:
            normalized_seen = max(0, int(seen_version))
            if normalized_seen > int(row.last_seen_version or 0):
                row.last_seen_version = normalized_seen

        normalized_job_id = self._coerce_uuid(job_id)
        if normalized_job_id is not None:
            row.last_enqueued_job_id = normalized_job_id

        row.updated_at = datetime.now(timezone.utc)
        sess.flush()
        return row

    def mark_evolved(
        self,
        graph_id: str,
        evolved_version: int,
        *,
        evolved_at: Optional[datetime] = None,
        session: Optional[Session] = None,
    ) -> SelfEvolutionStateModel:
        """Record completion of an evolve cycle idempotently."""
        sess = self._resolve_session(session)
        row = self.get_or_create(graph_id=graph_id, session=sess)

        normalized_version = max(0, int(evolved_version))
        if normalized_version > int(row.last_evolved_version or 0):
            row.last_evolved_version = normalized_version
        if normalized_version > int(row.last_seen_version or 0):
            row.last_seen_version = normalized_version

        row.last_evolved_at = self._normalize_dt(evolved_at) or datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
        sess.flush()
        return row

    def select_due_graphs(
        self,
        *,
        min_version_delta: int = 1,
        min_interval_seconds: int = 300,
        limit: int = 100,
        now: Optional[datetime] = None,
        session: Optional[Session] = None,
    ) -> List[SelfEvolutionDueGraph]:
        """Select due graphs using version delta + interval + active-job exclusion."""
        sess = self._resolve_session(session)
        now_ts = self._normalize_dt(now) or datetime.now(timezone.utc)
        delta_required = max(1, int(min_version_delta))
        interval_required = max(0, int(min_interval_seconds))
        max_items = max(1, int(limit))

        versions = (
            sess.query(GraphVersionModel)
            .filter(GraphVersionModel.tenant_id == self.tenant_id)
            .order_by(asc(GraphVersionModel.graph_id))
            .all()
        )
        if not versions:
            return []

        graph_ids = [str(row.graph_id) for row in versions]

        states = (
            sess.query(SelfEvolutionStateModel)
            .filter(
                and_(
                    SelfEvolutionStateModel.tenant_id == self.tenant_id,
                    SelfEvolutionStateModel.graph_id.in_(graph_ids),
                )
            )
            .all()
        )
        state_map = {str(row.graph_id): row for row in states}

        active_job_rows = (
            sess.query(JobModel.graph_id)
            .filter(
                and_(
                    JobModel.tenant_id == self.tenant_id,
                    JobModel.kind == "evolve",
                    JobModel.status.in_(["pending", "running"]),
                    JobModel.graph_id.in_(graph_ids),
                )
            )
            .all()
        )
        active_graph_ids = {str(row[0]) for row in active_job_rows}

        due: List[SelfEvolutionDueGraph] = []
        for version_row in versions:
            graph_id = str(version_row.graph_id)
            if graph_id in active_graph_ids:
                continue

            state = state_map.get(graph_id)
            current_version = int(version_row.version or 0)
            last_seen_version = int(getattr(state, "last_seen_version", 0) or 0)
            last_evolved_version = int(getattr(state, "last_evolved_version", 0) or 0)
            version_delta = current_version - last_evolved_version
            if version_delta < delta_required:
                continue

            last_evolved_at = self._normalize_dt(getattr(state, "last_evolved_at", None))
            if last_evolved_at is not None:
                elapsed = (now_ts - last_evolved_at).total_seconds()
                if elapsed < interval_required:
                    continue

            last_job_id_value = getattr(state, "last_enqueued_job_id", None)
            due.append(
                SelfEvolutionDueGraph(
                    graph_id=graph_id,
                    current_version=current_version,
                    last_seen_version=last_seen_version,
                    last_evolved_version=last_evolved_version,
                    version_delta=version_delta,
                    last_evolved_at=last_evolved_at,
                    last_enqueued_job_id=(
                        str(last_job_id_value) if last_job_id_value is not None else None
                    ),
                )
            )

        def _due_sort_key(item: SelfEvolutionDueGraph):
            # Prioritize graphs that never evolved; then oldest evolve timestamp; stable by graph.
            ts = item.last_evolved_at.timestamp() if item.last_evolved_at else -1.0
            return (ts, item.graph_id)

        due.sort(key=_due_sort_key)
        return due[:max_items]


__all__ = ["SelfEvolutionDueGraph", "SelfEvolutionStateRepo"]
