"""Edge Repository for FIG graph storage.

FAIM-native edge operations with deterministic ordering.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from sqlalchemy import and_, asc, desc, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import uuid7
    from faim.Faim_Native.store.pg.models_faim import EdgeModel
    from faim.Faim_Native.core.operators.semantic_typing import KNOWN_SEMANTIC_KINDS
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import uuid7
    from store.pg.models_faim import EdgeModel
    from core.operators.semantic_typing import KNOWN_SEMANTIC_KINDS


class EdgeRepo:
    """Repository for FIG graph edges.

    Handles inheritance and opposition edges.
    All operations are deterministic with stable ordering.
    """

    def __init__(self, session: Session, tenant_id: str = "__test__"):
        self.session = session
        self.tenant_id = tenant_id

    @staticmethod
    def _coerce_uuid(node_id: Union[UUID, str]) -> Optional[UUID]:
        """Normalize node_id input to UUID."""
        if isinstance(node_id, UUID):
            return node_id
        try:
            return UUID(str(node_id))
        except (ValueError, TypeError, AttributeError):
            return None

    def set_inheritance_parents(
        self,
        graph_id: str,
        child_id: UUID,
        parents: List[Tuple[UUID, float]],
        parents_meta: Optional[List[Optional[Dict]]] = None,
    ) -> List[UUID]:
        """Set inheritance parents for a child node.

        This replaces all existing inheritance edges for the child.
        Semantic edges are NOT touched (fully additive, separate lifecycle).

        Args:
            graph_id: Graph identifier.
            child_id: Child node ID.
            parents: List of (parent_id, fraction) tuples.
            parents_meta: Optional list of meta dicts parallel to parents.
                         If None or shorter than parents, defaults to None for that index.

        Returns:
            List of created edge IDs.
        """
        # Delete existing inheritance edges for this child ONLY (not semantic edges)
        self.session.query(EdgeModel).filter(
            and_(
                EdgeModel.tenant_id == self.tenant_id,
                EdgeModel.graph_id == graph_id,
                EdgeModel.dst_node_id == child_id,
                EdgeModel.kind == "inheritance",
            )
        ).delete()

        # Create new edges with optional meta (Layer A semantic typing)
        edge_ids = []
        now = datetime.now(timezone.utc)

        for idx, (parent_id, fraction) in enumerate(parents):
            # Get meta for this edge if provided
            meta_dict = None
            if parents_meta and idx < len(parents_meta):
                meta_dict = parents_meta[idx]

            edge = EdgeModel(
                edge_id=uuid7(),
                tenant_id=self.tenant_id,
                graph_id=graph_id,
                src_node_id=parent_id,
                dst_node_id=child_id,
                kind="inheritance",
                weight=int(fraction * 1e9),
                meta=meta_dict,
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
        scaled_weight = int(weight * 1e9)
        bind = self.session.get_bind()
        dialect_name = (getattr(bind, "dialect", None) and bind.dialect.name) or ""

        # Postgres path: avoid duplicate-key races by using a conflict-safe upsert.
        if dialect_name == "postgresql":
            statement = (
                pg_insert(EdgeModel)
                .values(
                    edge_id=uuid7(),
                    tenant_id=self.tenant_id,
                    graph_id=graph_id,
                    src_node_id=a_id,
                    dst_node_id=b_id,
                    kind="opposition",
                    weight=scaled_weight,
                    meta=meta,
                    created_at=now,
                )
                .on_conflict_do_update(
                    constraint="uq_edges_tenant_graph_src_dst_kind",
                    set_={
                        "weight": scaled_weight,
                        "meta": meta,
                        "created_at": now,
                    },
                )
                .returning(EdgeModel.edge_id)
            )
            edge_id = self.session.execute(statement).scalar_one()
            self.session.flush()
            return edge_id

        # Non-Postgres fallback (e.g. SQLite tests): update existing edge if present.
        existing = self.get_opposition_edge(graph_id=graph_id, a_id=a_id, b_id=b_id)
        if existing is not None:
            existing.weight = scaled_weight
            existing.meta = meta
            existing.created_at = now
            self.session.flush()
            return existing.edge_id

        edge = EdgeModel(
            edge_id=uuid7(),
            tenant_id=self.tenant_id,
            graph_id=graph_id,
            src_node_id=a_id,
            dst_node_id=b_id,
            kind="opposition",
            weight=scaled_weight,
            meta=meta,
            created_at=now,
        )
        self.session.add(edge)
        self.session.flush()
        return edge.edge_id

    def list_parents(
        self,
        graph_id: str,
        child_id: Union[UUID, str],
    ) -> List[Tuple[UUID, float]]:
        """List parents of a child node.

        Returns list of (parent_id, fraction) ordered by weight desc, parent_id asc.
        """
        child_uuid = self._coerce_uuid(child_id)
        if child_uuid is None:
            return []

        edges = (
            self.session.query(EdgeModel)
            .filter(
                and_(
                    EdgeModel.tenant_id == self.tenant_id,
                    EdgeModel.graph_id == graph_id,
                    EdgeModel.dst_node_id == child_uuid,
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

    def get_parents(
        self,
        graph_id: str,
        child_id: Union[UUID, str],
    ) -> List[EdgeModel]:
        """Compatibility helper returning edge models for parent inspection."""
        child_uuid = self._coerce_uuid(child_id)
        if child_uuid is None:
            return []

        return (
            self.session.query(EdgeModel)
            .filter(
                and_(
                    EdgeModel.tenant_id == self.tenant_id,
                    EdgeModel.graph_id == graph_id,
                    EdgeModel.dst_node_id == child_uuid,
                    EdgeModel.kind == "inheritance",
                )
            )
            .order_by(
                desc(EdgeModel.weight),
                asc(EdgeModel.src_node_id),
            )
            .all()
        )

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
                    EdgeModel.tenant_id == self.tenant_id,
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
                    EdgeModel.tenant_id == self.tenant_id,
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
                    EdgeModel.tenant_id == self.tenant_id,
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
                    EdgeModel.tenant_id == self.tenant_id,
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
                    EdgeModel.tenant_id == self.tenant_id,
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
            self.session.query(EdgeModel)
            .filter(
                and_(
                    EdgeModel.tenant_id == self.tenant_id,
                    EdgeModel.graph_id == graph_id,
                )
            )
            .count()
        )

    def count(self, graph_id: str) -> int:
        """Compatibility alias used by API routers."""
        return self.count_edges(graph_id)

    def count_inheritance_edges(self, graph_id: str) -> int:
        """Count inheritance edges in graph."""
        return (
            self.session.query(EdgeModel)
            .filter(
                and_(
                    EdgeModel.tenant_id == self.tenant_id,
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
            .filter(
                and_(
                    EdgeModel.tenant_id == self.tenant_id,
                    EdgeModel.graph_id == graph_id,
                )
            )
            .order_by(
                asc(EdgeModel.src_node_id),
                asc(EdgeModel.dst_node_id),
                asc(EdgeModel.kind),
            )
            .limit(limit)
            .all()
        )

    def add_semantic_edge(
        self,
        graph_id: str,
        src_node_id: UUID,
        dst_node_id: UUID,
        semantic_type: str,
        semantic_weight: float,
        meta: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """Create or update a semantic-typed edge (Layer B).

        Uses Postgres ON CONFLICT DO UPDATE for idempotency.
        Falls back to read-then-update on non-Postgres databases.

        Args:
            graph_id: Graph identifier.
            src_node_id: Source node ID (parent/neighbor).
            dst_node_id: Destination node ID (child/center).
            semantic_type: Kind value: "synonym", "hypernym", "hyponym", or "related".
            semantic_weight: Float weight (typically 0.95, 0.80, 0.75, 0.60).
                            Stored as int(semantic_weight * 1e9).
            meta: Optional metadata dict. If None, defaults to empty dict.

        Returns:
            UUID: The edge_id (new or updated).
        """
        now = datetime.now(timezone.utc)
        weight_int = int(semantic_weight * 1e9)
        edge_id = uuid7()
        bind = self.session.get_bind()
        dialect_name = (getattr(bind, "dialect", None) and bind.dialect.name) or ""

        # Postgres path: use the table-level unique constraint for idempotent upsert.
        if dialect_name == "postgresql":
            stmt = pg_insert(EdgeModel).values(
                edge_id=edge_id,
                tenant_id=self.tenant_id,
                graph_id=graph_id,
                src_node_id=src_node_id,
                dst_node_id=dst_node_id,
                kind=semantic_type,
                weight=weight_int,
                meta=meta or {},
                created_at=now,
            )
            # Postgres constraint: uq_edges_tenant_graph_src_dst_kind
            stmt = stmt.on_conflict_do_update(
                constraint="uq_edges_tenant_graph_src_dst_kind",
                set_={
                    EdgeModel.weight: weight_int,
                    EdgeModel.meta: meta or {},
                },
            )
            returned_edge_id = self.session.execute(stmt.returning(EdgeModel.edge_id)).scalar_one()
            self.session.flush()
            return returned_edge_id

        # Non-Postgres fallback (e.g. SQLite tests): update existing edge if present.
        existing = (
            self.session.query(EdgeModel)
            .filter(
                and_(
                    EdgeModel.tenant_id == self.tenant_id,
                    EdgeModel.graph_id == graph_id,
                    EdgeModel.src_node_id == src_node_id,
                    EdgeModel.dst_node_id == dst_node_id,
                    EdgeModel.kind == semantic_type,
                )
            )
            .first()
        )
        if existing is not None:
            existing.weight = weight_int
            existing.meta = meta or {}
            existing.created_at = now
            self.session.flush()
            return existing.edge_id

        edge = EdgeModel(
            edge_id=edge_id,
            tenant_id=self.tenant_id,
            graph_id=graph_id,
            src_node_id=src_node_id,
            dst_node_id=dst_node_id,
            kind=semantic_type,
            weight=weight_int,
            meta=meta or {},
            created_at=now,
        )
        self.session.add(edge)
        self.session.flush()
        return edge_id

    def list_semantic_neighbors(
        self,
        graph_id: str,
        node_ids: List[UUID],
        kinds: Optional[List[str]] = None,
    ) -> List[EdgeModel]:
        """Batch query: all semantic edges where src OR dst is in node_ids.

        Used by query engine to expand candidates via semantic edges.

        Args:
            graph_id: Graph identifier.
            node_ids: List of node IDs to find semantic neighbors for.
            kinds: Optional list of semantic kinds to filter by.
                   Defaults to all KNOWN_SEMANTIC_KINDS if None.

        Returns:
            List[EdgeModel]: Semantic edges, ordered by (kind, weight desc, edge_id asc).
        """
        if not node_ids:
            return []

        if kinds is None:
            kinds = sorted(list(KNOWN_SEMANTIC_KINDS))

        edges = (
            self.session.query(EdgeModel)
            .filter(
                and_(
                    EdgeModel.tenant_id == self.tenant_id,
                    EdgeModel.graph_id == graph_id,
                    EdgeModel.kind.in_(kinds),
                    or_(
                        EdgeModel.src_node_id.in_(node_ids),
                        EdgeModel.dst_node_id.in_(node_ids),
                    ),
                )
            )
            .order_by(
                asc(EdgeModel.kind),
                desc(EdgeModel.weight),
                asc(EdgeModel.edge_id),
            )
            .all()
        )
        return edges

    def list_graph_neighbors(
        self,
        graph_id: str,
        node_ids: List[UUID],
        kinds: Optional[List[str]] = None,
        limit: int = 1000,
    ) -> List[EdgeModel]:
        """List incident graph edges for a node set with deterministic ordering."""
        if not node_ids:
            return []

        query = self.session.query(EdgeModel).filter(
            and_(
                EdgeModel.tenant_id == self.tenant_id,
                EdgeModel.graph_id == graph_id,
                or_(
                    EdgeModel.src_node_id.in_(node_ids),
                    EdgeModel.dst_node_id.in_(node_ids),
                ),
            )
        )
        if kinds is not None:
            query = query.filter(EdgeModel.kind.in_(list(kinds)))

        return (
            query.order_by(
                asc(EdgeModel.src_node_id),
                asc(EdgeModel.dst_node_id),
                asc(EdgeModel.kind),
                desc(EdgeModel.weight),
                asc(EdgeModel.edge_id),
            )
            .limit(limit)
            .all()
        )

    def delete_edges_by_kinds(
        self,
        graph_id: str,
        kinds: List[str],
    ) -> int:
        """Delete only the specified edge kinds for a graph."""
        if not kinds:
            return 0
        deleted = (
            self.session.query(EdgeModel)
            .filter(
                and_(
                    EdgeModel.tenant_id == self.tenant_id,
                    EdgeModel.graph_id == graph_id,
                    EdgeModel.kind.in_(list(kinds)),
                )
            )
            .delete(synchronize_session=False)
        )
        self.session.flush()
        return int(deleted or 0)


# Exports
__all__ = ["EdgeRepo"]
