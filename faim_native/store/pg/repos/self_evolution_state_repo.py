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
    from store.pg.models_faim import (
        GraphVersionModel,
        JobModel,
        SelfEvolutionStateModel,
    )


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


@dataclass(frozen=True)
class SelfEvolutionControlState:
    """Resolved graph-scoped self-evolution control state."""

    self_evolve_enabled: bool
    self_evolve_trigger_mode: str
    self_invent_enabled: bool
    self_invent_on_evolve: bool
    self_invent_after_upload: bool
    source: str
    updated_at: Optional[datetime]
    updated_by: Optional[str]
    override_self_evolve_enabled: Optional[bool]
    override_self_evolve_trigger_mode: Optional[str]
    override_self_invent_enabled: Optional[bool]
    override_self_invent_on_evolve: Optional[bool]
    override_self_invent_after_upload: Optional[bool]


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

    @staticmethod
    def _default_trigger_mode() -> str:
        try:
            from runtime.feature_flags import get_feature_flags

            flags = get_feature_flags()
            value = str(flags.self_evolve_trigger_mode or "").strip().lower()
            if value in {"manual", "post_upload", "periodic", "hybrid"}:
                return value
        except Exception:  # nosec B110
            pass
        return "manual"

    @staticmethod
    def _default_bool(value: Optional[bool], fallback: bool) -> bool:
        if value is None:
            return bool(fallback)
        return bool(value)

    def resolve_control_state(
        self,
        graph_id: str,
        session: Optional[Session] = None,
    ) -> SelfEvolutionControlState:
        """Resolve the effective control state for one graph."""
        sess = self._resolve_session(session)
        row = self.get_or_create(graph_id=graph_id, session=sess)

        try:
            from runtime.feature_flags import get_feature_flags

            flags = get_feature_flags()
        except Exception:  # nosec B110
            flags = None

        default_self_evolve_enabled = bool(
            getattr(flags, "self_evolve_enabled", False) if flags else False
        )
        default_trigger_mode = self._default_trigger_mode()
        default_self_invent_enabled = bool(
            getattr(flags, "self_invent_enabled", False) if flags else False
        )
        default_self_invent_on_evolve = bool(
            getattr(flags, "self_invent_on_evolve", True) if flags else True
        )
        default_self_invent_after_upload = bool(
            getattr(flags, "self_invent_after_upload", False) if flags else False
        )

        trigger_mode = str(
            getattr(row, "control_self_evolve_trigger_mode", "") or ""
        ).strip().lower()
        if trigger_mode not in {"manual", "post_upload", "periodic", "hybrid"}:
            trigger_mode = default_trigger_mode

        return SelfEvolutionControlState(
            self_evolve_enabled=self._default_bool(
                getattr(row, "control_self_evolve_enabled", None),
                default_self_evolve_enabled,
            ),
            self_evolve_trigger_mode=trigger_mode,
            self_invent_enabled=self._default_bool(
                getattr(row, "control_self_invent_enabled", None),
                default_self_invent_enabled,
            ),
            self_invent_on_evolve=self._default_bool(
                getattr(row, "control_self_invent_on_evolve", None),
                default_self_invent_on_evolve,
            ),
            self_invent_after_upload=self._default_bool(
                getattr(row, "control_self_invent_after_upload", None),
                default_self_invent_after_upload,
            ),
            source="db_override" if any(
                value is not None
                for value in (
                    getattr(row, "control_self_evolve_enabled", None),
                    getattr(row, "control_self_evolve_trigger_mode", None),
                    getattr(row, "control_self_invent_enabled", None),
                    getattr(row, "control_self_invent_on_evolve", None),
                    getattr(row, "control_self_invent_after_upload", None),
                )
            )
            else "runtime_default",
            updated_at=self._normalize_dt(getattr(row, "control_updated_at", None)),
            updated_by=(
                str(getattr(row, "control_updated_by", "")).strip() or None
            ),
            override_self_evolve_enabled=getattr(
                row, "control_self_evolve_enabled", None
            ),
            override_self_evolve_trigger_mode=(
                str(getattr(row, "control_self_evolve_trigger_mode", "")).strip()
                or None
            ),
            override_self_invent_enabled=getattr(
                row, "control_self_invent_enabled", None
            ),
            override_self_invent_on_evolve=getattr(
                row, "control_self_invent_on_evolve", None
            ),
            override_self_invent_after_upload=getattr(
                row, "control_self_invent_after_upload", None
            ),
        )

    def update_control_state(
        self,
        graph_id: str,
        *,
        self_evolve_enabled: Optional[bool] = None,
        self_evolve_trigger_mode: Optional[str] = None,
        self_invent_enabled: Optional[bool] = None,
        self_invent_on_evolve: Optional[bool] = None,
        self_invent_after_upload: Optional[bool] = None,
        updated_by: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> SelfEvolutionStateModel:
        """Persist graph-scoped control overrides."""
        sess = self._resolve_session(session)
        row = self.get_or_create(graph_id=graph_id, session=sess)

        if self_evolve_enabled is not None:
            row.control_self_evolve_enabled = bool(self_evolve_enabled)
        if self_evolve_trigger_mode is not None:
            value = str(self_evolve_trigger_mode or "").strip().lower()
            row.control_self_evolve_trigger_mode = value or None
        if self_invent_enabled is not None:
            row.control_self_invent_enabled = bool(self_invent_enabled)
        if self_invent_on_evolve is not None:
            row.control_self_invent_on_evolve = bool(self_invent_on_evolve)
        if self_invent_after_upload is not None:
            row.control_self_invent_after_upload = bool(self_invent_after_upload)

        row.control_updated_at = datetime.now(timezone.utc)
        row.control_updated_by = str(updated_by or "").strip() or None
        row.updated_at = datetime.now(timezone.utc)
        sess.flush()
        return row

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

        row.last_evolved_at = self._normalize_dt(evolved_at) or datetime.now(
            timezone.utc
        )
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

            last_evolved_at = self._normalize_dt(
                getattr(state, "last_evolved_at", None)
            )
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
                        str(last_job_id_value)
                        if last_job_id_value is not None
                        else None
                    ),
                )
            )

        def _due_sort_key(item: SelfEvolutionDueGraph):
            # Prioritize graphs that never evolved; then oldest evolve timestamp; stable by graph.
            ts = item.last_evolved_at.timestamp() if item.last_evolved_at else -1.0
            return (ts, item.graph_id)

        due.sort(key=_due_sort_key)
        return due[:max_items]


__all__ = [
    "SelfEvolutionControlState",
    "SelfEvolutionDueGraph",
    "SelfEvolutionStateRepo",
]
