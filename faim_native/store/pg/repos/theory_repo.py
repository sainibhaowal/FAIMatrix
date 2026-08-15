"""Durable persistence for self-evolution theories.

The self-evolution loop derives bounded, deterministic theories from
observed graph structure (cross-galaxy correlations, redundancy clusters,
hierarchy composition, cognitive-type distribution) gated by evolution
pressure λ. Theories written here survive restarts and are surfaced
through the evolve API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from store.pg.models_faim import GraphTheoryModel
except (ImportError, RuntimeError, ModuleNotFoundError):  # pragma: no cover
    GraphTheoryModel = Any


class TheoryRepo:
    """Read/write access to durable graph theories."""

    def __init__(self, session, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def upsert(self, theory: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update a theory (idempotent on theory_id)."""
        theory_id = theory["theory_id"]
        graph_id = theory["graph_id"]
        row = (
            self.session.query(GraphTheoryModel)
            .filter(
                GraphTheoryModel.tenant_id == self.tenant_id,
                GraphTheoryModel.graph_id == graph_id,
                GraphTheoryModel.theory_id == theory_id,
            )
            .first()
        )

        now = datetime.now(timezone.utc)
        if row is None:
            row = GraphTheoryModel(
                theory_id=theory_id,
                tenant_id=self.tenant_id,
                graph_id=graph_id,
                theory_type=str(theory.get("theory_type", "generalization")),
                description=str(theory.get("description", "")),
                confidence=float(theory.get("confidence", 0.0)),
                evidence_node_ids=list(theory.get("evidence_node_ids", []) or []),
                metadata_json=theory.get("metadata", {}) or {},
                graph_version=int(theory.get("graph_version", 0) or 0),
                created_at=now,
            )
            self.session.add(row)
        else:
            row.theory_type = str(theory.get("theory_type", row.theory_type))
            row.description = str(theory.get("description", row.description))
            row.confidence = float(theory.get("confidence", row.confidence))
            row.evidence_node_ids = list(
                theory.get("evidence_node_ids", []) or row.evidence_node_ids or []
            )
            row.metadata_json = theory.get("metadata", {}) or row.metadata_json or {}
            row.graph_version = int(
                theory.get("graph_version", row.graph_version or 0)
            )

        self.session.flush()
        return row.to_dict()

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def list_theories(
        self,
        graph_id: str,
        limit: int = 50,
        theory_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return theories for a graph, newest first."""
        query = self.session.query(GraphTheoryModel).filter(
            GraphTheoryModel.tenant_id == self.tenant_id,
            GraphTheoryModel.graph_id == graph_id,
        )
        if theory_type:
            query = query.filter(GraphTheoryModel.theory_type == theory_type)
        rows = (
            query.order_by(
                GraphTheoryModel.created_at.desc(),
                GraphTheoryModel.id.desc(),
            )
            .limit(max(1, min(500, int(limit))))
            .all()
        )
        return [row.to_dict() for row in rows]

    def count_theories(
        self,
        graph_id: str,
        since_version: Optional[int] = None,
    ) -> int:
        """Count theories for a graph, optionally only at a version boundary."""
        query = self.session.query(GraphTheoryModel).filter(
            GraphTheoryModel.tenant_id == self.tenant_id,
            GraphTheoryModel.graph_id == graph_id,
        )
        if since_version is not None:
            query = query.filter(
                GraphTheoryModel.graph_version >= since_version
            )
        return int(query.count())