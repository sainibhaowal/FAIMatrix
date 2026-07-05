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

    @staticmethod
    def _normalize_signature_counts(
        raw_counts: Optional[Dict[str, Dict[str, Any]]],
    ) -> Dict[str, Dict[str, Any]]:
        """Normalize a persisted signature-count snapshot."""
        if not isinstance(raw_counts, dict):
            return {}

        normalized: Dict[str, Dict[str, Any]] = {}
        for signature, value in raw_counts.items():
            if not isinstance(signature, str) or not signature.strip():
                continue
            if not isinstance(value, dict):
                continue

            members = value.get("members")
            if not isinstance(members, list):
                continue
            clean_members = sorted(
                [str(m) for m in members if isinstance(m, str) and m.strip()]
            )
            if len(clean_members) < 2:
                continue

            normalized[signature] = {
                "count": int(max(0, int(value.get("count", 0) or 0))),
                "members": clean_members,
                "last_seq": int(max(0, int(value.get("last_seq", 0) or 0))),
                "invented": bool(value.get("invented", False)),
            }
        return normalized

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
        if int(row.last_event_seq or 0) > int(max(0, last_event_seq)):
            return row

        row.last_event_seq = int(max(0, last_event_seq))
        row.signature_counts = self._normalize_signature_counts(signature_counts)
        row.last_cycle_macros = int(max(0, last_cycle_macros))
        row.last_cycle_at = last_cycle_at or datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
        sess.flush()
        return row


__all__ = ["SelfInventionStateRepo"]
