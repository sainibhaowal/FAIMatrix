from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

# Flexible imports
try:
    from faim.Faim_Native.store.pg.models_faim import SelfInventionStateModel
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from store.pg.models_faim import SelfInventionStateModel


class SelfInventionStateRepo:
    """Repository for self-invention runtime state."""

    def __init__(self, session: Optional[Session] = None, tenant_id: str = "default"):
        self.session = session
        self.tenant_id = tenant_id

    def _resolve_session(self, session: Optional[Session]) -> Session:
        resolved = session or self.session
        if resolved is None:
            from store.pg.session import get_session

            resolved = get_session()
        return resolved

    def get(
        self,
        graph_id: str,
        session: Optional[Session] = None,
    ) -> Optional[SelfInventionStateModel]:
        """Get persisted invention state for tenant+graph."""
        sess = self._resolve_session(session)
        return (
            sess.query(SelfInventionStateModel)
            .filter(
                and_(
                    SelfInventionStateModel.tenant_id == self.tenant_id,
                    SelfInventionStateModel.graph_id == graph_id,
                )
            )
            .first()
        )

    def get_or_create(
        self,
        graph_id: str,
        session: Optional[Session] = None,
    ) -> SelfInventionStateModel:
        """Get state row or create an initialized one."""
        sess = self._resolve_session(session)
        row = self.get(graph_id, session=sess)
        if row is not None:
            return row

        now = datetime.now(timezone.utc)
        row = SelfInventionStateModel(
            tenant_id=self.tenant_id,
            graph_id=graph_id,
            last_event_seq=0,
            signature_counts={},
            last_cycle_macros=0,
            last_cycle_at=None,
            updated_at=now,
        )
        sess.add(row)
        sess.flush()
        return row

    def save(
        self,
        graph_id: str,
        *,
        last_event_seq: int,
        signature_counts: Dict[str, Dict[str, Any]],
        last_cycle_macros: int,
        last_cycle_at: Optional[datetime] = None,
        session: Optional[Session] = None,
    ) -> SelfInventionStateModel:
        """Persist state updates for a completed invention cycle."""
        sess = self._resolve_session(session)
        row = self.get_or_create(graph_id, session=sess)
        row.last_event_seq = int(max(0, last_event_seq))
        row.signature_counts = signature_counts
        row.last_cycle_macros = int(max(0, last_cycle_macros))
        row.last_cycle_at = last_cycle_at or datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
        sess.flush()
        return row


__all__ = ["SelfInventionStateRepo"]
