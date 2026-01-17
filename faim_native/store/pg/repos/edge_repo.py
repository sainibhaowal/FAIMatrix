"""Edge Repository for FIG graph storage.

FAIM-native edge operations with deterministic ordering.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import Session

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import uuid7
    from faim.Faim_Native.store.pg.models_faim import EdgeModel
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import uuid7
    from store.pg.models_faim import EdgeModel


class EdgeRepo:
    """Repository for FIG graph edges.

    Handles inheritance and opposition edges.
    All operations are deterministic with stable ordering.
    """

    def __init__(self, session: Session, tenant_id: str = "__test__"):
        self.session = session
        self.tenant_id = tenant_id

    def set_inheritance_parents(
        self,
        graph_id: str,
        child_id: UUID,
        parents: List[Tuple[UUID, float]],
    ) -> List[UUID]:
        """Set inheritance parents for a child node.

        This replaces all existing inheritance edges for the child.

        Args:
            graph_id: Graph identifier.
            child_id: Child node ID.
            parents: List of (parent_id, fraction) tuples.

        Returns:
            List of created edge IDs.
        """
        # Delete existing inheritance edges for this child
        self.session.query(EdgeModel).filter(
            and_(
                EdgeModel.graph_id == graph_id,
                EdgeModel.dst_node_id == child_id,
                EdgeModel.kind == "inheritance",
            )
        ).delete()

        # Create new edges
        edge_ids = []
        now = datetime.now(timezone.utc)

        for parent_id, fraction in parents:
            edge = EdgeModel(
                edge_id=uuid7(),
                tenant_id=self.tenant_id,
                graph_id=graph_id,
                src_node_id=parent_id,
                dst_node_id=child_id,
                kind="inheritance",
                weight=int(fraction * 1e9),
                meta=None,
                created_at=now,
            )
            self.session.add(edge)
            edge_ids.append(edge.edge_id)

        self.session.flush()
        return edge_ids

    def add_opposition_edge(
        self,
        graph_id: str,
        a_id: UUID,
        b_id: UUID,
        weight: float,
        meta: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """Add an opposition edge between two nodes.

        Args:
            graph_id: Graph identifier.
            a_id: First node ID.
            b_id: Second node ID.
            weight: Opposition magnitude.
            meta: Optional metadata.

        Returns:
            edge_id of created edge.
        """
        # Sort IDs for deterministic ordering
        if str(a_id) > str(b_id):
            a_id, b_id = b_id, a_id

        now = datetime.now(timezone.utc)
        edge = EdgeModel(
            edge_id=uuid7(),
            tenant_id=self.tenant_id,
            graph_id=graph_id,
            src_node_id=a_id,
            dst_node_id=b_id,
            kind="opposition",
            weight=int(weight * 1e9),
            meta=meta,
            created_at=now,
        )
        self.session.add(edge)
        self.session.flush()
        return edge.edge_id

    def list_parents(
        self,
        graph_id: str,
        child_id: UUID,
    ) -> List[Tuple[UUID, float]]:
        """List parents of a child node.

        Returns list of (parent_id, fraction) ordered by weight desc, parent_id asc.
        """
        edges = (
            self.session.query(EdgeModel)
            .filter(
                and_(
                    EdgeModel.graph_id == graph_id,
                    EdgeModel.dst_node_id == child_id,
                    EdgeModel.kind == "inheritance",
                )
            )
            .order_by(
                desc(EdgeModel.weight),
                asc(EdgeModel.src_node_id),
            )
            .all()
        )

        return [(e.src_node_id, e.weight / 1e9) for e in edges]

    def list_children(
        self,
        graph_id: str,
        parent_id: UUID,
    ) -> List[UUID]:
        """List children of a parent node."""
        edges = (
            self.session.query(EdgeModel)
            .filter(
                and_(
                    EdgeModel.graph_id == graph_id,
                    EdgeModel.src_node_id == parent_id,
                    EdgeModel.kind == "inheritance",
                )
            )
            .order_by(
                asc(EdgeModel.dst_node_id),
            )
            .all()
        )

        return [e.dst_node_id for e in edges]

    def get_opposition_edge(
        self,
        graph_id: str,
        a_id: UUID,
        b_id: UUID,
    ) -> Optional[EdgeModel]:
        """Get opposition edge between two nodes."""
        # Sort IDs for deterministic lookup
        if str(a_id) > str(b_id):
            a_id, b_id = b_id, a_id

        return (
            self.session.query(EdgeModel)
            .filter(
                and_(
                    EdgeModel.graph_id == graph_id,
                    EdgeModel.src_node_id == a_id,
                    EdgeModel.dst_node_id == b_id,
                    EdgeModel.kind == "opposition",
                )
            )
            .first()
        )

    def list_opposition_edges(
        self,
        graph_id: str,
        limit: int = 100,
    ) -> List[EdgeModel]:
        """List all opposition edges in graph."""
        return (
            self.session.query(EdgeModel)
            .filter(
                and_(
                    EdgeModel.graph_id == graph_id,
                    EdgeModel.kind == "opposition",
                )
            )
            .order_by(
                desc(EdgeModel.weight),
                asc(EdgeModel.edge_id),
            )
            .limit(limit)
            .all()
        )

    def delete_edges_for_node(
        self,
        graph_id: str,
        node_id: UUID,
    ) -> int:
        """Delete all edges involving a node (both as src or dst).

        Returns number of deleted edges.
        """
        count = 0

        # Delete where node is source
        count += (
            self.session.query(EdgeModel)
            .filter(
                and_(
                    EdgeModel.graph_id == graph_id,
                    EdgeModel.src_node_id == node_id,
                )
            )
            .delete()
        )

        # Delete where node is destination
        count += (
            self.session.query(EdgeModel)
            .filter(
                and_(
                    EdgeModel.graph_id == graph_id,
                    EdgeModel.dst_node_id == node_id,
                )
            )
            .delete()
        )

        self.session.flush()
        return count

    def count_edges(self, graph_id: str) -> int:
        """Count all edges in graph."""
        return (
            self.session.query(EdgeModel).filter(EdgeModel.graph_id == graph_id).count()
        )

    def count_inheritance_edges(self, graph_id: str) -> int:
        """Count inheritance edges in graph."""
        return (
            self.session.query(EdgeModel)
            .filter(
                and_(
                    EdgeModel.graph_id == graph_id,
                    EdgeModel.kind == "inheritance",
                )
            )
            .count()
        )

    def list_all_edges(
        self,
        graph_id: str,
        limit: int = 1000,
    ) -> List[EdgeModel]:
        """List all edges for graph hash computation.

        Ordered by (src_node_id, dst_node_id, kind) for determinism.
        """
        return (
            self.session.query(EdgeModel)
            .filter(EdgeModel.graph_id == graph_id)
            .order_by(
                asc(EdgeModel.src_node_id),
                asc(EdgeModel.dst_node_id),
                asc(EdgeModel.kind),
            )
            .limit(limit)
            .all()
        )


# Exports
__all__ = ["EdgeRepo"]
