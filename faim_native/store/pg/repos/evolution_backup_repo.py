"""Evolution backup journal: pre-action snapshots for safe undo.

Backups are written before any destructive evolution action (prune). Each
backup captures the full node row, its representation sidecar and the edges
touching it, so a restore can bring the node back exactly as it was.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

try:
    from faim.Faim_Native.core.contracts.types import uuid7
    from faim.Faim_Native.store.pg.models_faim import EvolutionBackupModel
except (ImportError, RuntimeError):
    from core.contracts.types import uuid7

    from store.pg.models_faim import EvolutionBackupModel


def _serialize_row(model: Any) -> Dict[str, Any]:
    """Serialize an ORM row to JSON-safe plain values."""
    data: Dict[str, Any] = {}
    for key, value in (getattr(model, "__dict__", {}) or {}).items():
        if key.startswith("_"):
            continue
        if isinstance(value, datetime):
            data[key] = value.isoformat()
        elif isinstance(value, UUID):
            data[key] = str(value)
        elif isinstance(value, (list, dict, tuple)):
            data[key] = value
        else:
            data[key] = value
    return data


class EvolutionBackupRepo:
    """Storage for evolution pre-action snapshots (tenant-scoped)."""

    def __init__(self, session: Session, tenant_id: str = "default"):
        self.session = session
        self.tenant_id = tenant_id

    def snapshot(
        self,
        *,
        graph_id: str,
        node_id: UUID,
        action_type: str = "prune",
        reason: Optional[str] = None,
        version: int = 0,
        node_json: Optional[Dict[str, Any]] = None,
        repr_json: Optional[Dict[str, Any]] = None,
        edges_json: Optional[List[Dict[str, Any]]] = None,
    ) -> UUID:
        """Write one pre-action snapshot; returns its backup_id."""
        backup = EvolutionBackupModel(
            backup_id=uuid7(),
            tenant_id=self.tenant_id,
            graph_id=graph_id,
            version=int(version or 0),
            action_type=action_type,
            node_id=node_id,
            reason=reason,
            node_json=node_json or {},
            repr_json=repr_json,
            edges_json=edges_json,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(backup)
        self.session.flush()
        return backup.backup_id

    def snapshot_model(
        self,
        *,
        graph_id: str,
        node: Any,
        action_type: str = "prune",
        reason: Optional[str] = None,
        version: int = 0,
        repr_json: Optional[Dict[str, Any]] = None,
        edges_json: Optional[List[Dict[str, Any]]] = None,
    ) -> UUID:
        """Snapshot an existing ORM node row plus its sidecars."""
        return self.snapshot(
            graph_id=graph_id,
            node_id=node.node_id,
            action_type=action_type,
            reason=reason,
            version=version,
            node_json=_serialize_row(node),
            repr_json=repr_json,
            edges_json=edges_json,
        )

    def list_by_graph(
        self,
        graph_id: str,
        version: Optional[int] = None,
        limit: int = 500,
    ) -> List[EvolutionBackupModel]:
        query = self.session.query(EvolutionBackupModel).filter(
            EvolutionBackupModel.tenant_id == self.tenant_id,
            EvolutionBackupModel.graph_id == graph_id,
        )
        if version is not None:
            query = query.filter(EvolutionBackupModel.version == int(version))
        return (
            query.order_by(EvolutionBackupModel.created_at.desc())
            .limit(limit)
            .all()
        )

    def count_for_version(self, graph_id: str, version: int) -> int:
        return (
            self.session.query(EvolutionBackupModel)
            .filter(
                EvolutionBackupModel.tenant_id == self.tenant_id,
                EvolutionBackupModel.graph_id == graph_id,
                EvolutionBackupModel.version == int(version),
            )
            .count()
        )

    def retag(self, graph_id: str, from_version: int, to_version: int) -> int:
        """Re-attribute snapshots taken before the version bump to the new version."""
        if int(from_version) == int(to_version):
            return 0
        rows = (
            self.session.query(EvolutionBackupModel)
            .filter(
                EvolutionBackupModel.tenant_id == self.tenant_id,
                EvolutionBackupModel.graph_id == graph_id,
                EvolutionBackupModel.version == int(from_version),
            )
            .all()
        )
        for row in rows:
            row.version = int(to_version)
        self.session.flush()
        return len(rows)