"""Node Repository for FIG graph storage.

FAIM-native node operations with deterministic ordering.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import and_, asc
from sqlalchemy.orm import Session

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import uuid7
    from faim.Faim_Native.encoding.vector_schema import FAIMVector
    from faim.Faim_Native.store.pg.models_faim import NodeModel
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import uuid7
    from encoding.vector_schema import FAIMVector
    from store.pg.models_faim import NodeModel


class NodeRepo:
    """Repository for FIG graph nodes.

    All operations are deterministic with stable ordering.
    """

    def __init__(self, session: Session, tenant_id: str = "__test__"):
        self.session = session
        self.tenant_id = tenant_id

    def upsert_atom_node(
        self,
        graph_id: str,
        vector: FAIMVector,
    ) -> UUID:
        """Upsert an atom node from FAIMVector.

        If node with same vector_hash exists, update it.
        Otherwise create new node.

        Args:
            graph_id: Graph identifier.
            vector: FAIMVector to store.

        Returns:
            node_id of upserted node.
        """
        existing = self.get_by_vector_hash(graph_id, vector.vector_hash)
        now = datetime.now(timezone.utc)

        if existing:
            # Update existing node
            existing.touch_count += 1
            existing.last_access = now
            existing.updated_at = now
            self.session.flush()
            return existing.node_id

        # Create new node
        node = NodeModel(
            node_id=uuid7(),
            tenant_id=self.tenant_id,
            graph_id=graph_id,
            kind="atom",
            vector_hash=vector.vector_hash,
            raw_id=vector.raw_id,
            block_id=vector.block_id,
            anchor_json=vector.anchor_dict,
            v_native=list(vector.v_native),
            opp_signature=vector.opp_signature,
            residual=int(vector.residual * 1e9),
            level=vector.level,
            touch_count=1,
            last_access=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(node)
        self.session.flush()
        return node.node_id

    def create_macro_node(
        self,
        graph_id: str,
        v_native: List[float],
        vector_hash: str,
        opp_signature: Dict[str, float],
        level: int = 1,
        residual: float = 0.0,
    ) -> UUID:
        """Create a macro node (level > 0).

        Args:
            graph_id: Graph identifier.
            v_native: Vector values.
            vector_hash: Computed hash.
            opp_signature: Opposition signature.
            level: Hierarchy level (default 1).
            residual: Residual value.

        Returns:
            node_id of created node.
        """
        now = datetime.now(timezone.utc)
        node = NodeModel(
            node_id=uuid7(),
            tenant_id=self.tenant_id,
            graph_id=graph_id,
            kind="macro",
            vector_hash=vector_hash,
            raw_id=None,
            block_id=None,
            anchor_json=None,
            v_native=v_native,
            opp_signature=opp_signature,
            residual=int(residual * 1e9),
            level=level,
            touch_count=1,
            last_access=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(node)
        self.session.flush()
        return node.node_id

    def get_node(self, graph_id: str, node_id: UUID) -> Optional[NodeModel]:
        """Get node by ID."""
        return (
            self.session.query(NodeModel)
            .filter(
                and_(
                    NodeModel.tenant_id == self.tenant_id,
                    NodeModel.graph_id == graph_id,
                    NodeModel.node_id == node_id,
                )
            )
            .first()
        )

    @staticmethod
    def _coerce_uuid(node_id: Union[UUID, str]) -> Optional[UUID]:
        """Normalize node_id input to UUID."""
        if isinstance(node_id, UUID):
            return node_id
        try:
            return UUID(str(node_id))
        except (ValueError, TypeError, AttributeError):
            return None

    def get_by_id(self, graph_id: str, node_id: Union[UUID, str]) -> Optional[NodeModel]:
        """Compatibility alias used by API routers."""
        parsed = self._coerce_uuid(node_id)
        if parsed is None:
            return None
        return self.get_node(graph_id, parsed)

    def get_by_vector_hash(
        self, graph_id: str, vector_hash: str
    ) -> Optional[NodeModel]:
        """Get node by vector hash."""
        return (
            self.session.query(NodeModel)
            .filter(
                and_(
                    NodeModel.tenant_id == self.tenant_id,
                    NodeModel.graph_id == graph_id,
                    NodeModel.vector_hash == vector_hash,
                )
            )
            .first()
        )

    def list_nodes(
        self,
        graph_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[NodeModel]:
        """List nodes with deterministic ordering.

        Ordered by (created_at, node_id) for stability.
        """
        return (
            self.session.query(NodeModel)
            .filter(
                and_(
                    NodeModel.tenant_id == self.tenant_id,
                    NodeModel.graph_id == graph_id,
                )
            )
            .order_by(
                asc(NodeModel.created_at),
                asc(NodeModel.node_id),
            )
            .limit(limit)
            .offset(offset)
            .all()
        )

    def list_by_graph(
        self,
        graph_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[NodeModel]:
        """Compatibility alias used by API routers."""
        return self.list_nodes(graph_id=graph_id, limit=limit, offset=offset)

    def list_atoms(self, graph_id: str, limit: int = 100) -> List[NodeModel]:
        """List atom nodes only."""
        return (
            self.session.query(NodeModel)
            .filter(
                and_(
                    NodeModel.tenant_id == self.tenant_id,
                    NodeModel.graph_id == graph_id,
                    NodeModel.kind == "atom",
                )
            )
            .order_by(
                asc(NodeModel.created_at),
                asc(NodeModel.node_id),
            )
            .limit(limit)
            .all()
        )

    def count_nodes(self, graph_id: str) -> int:
        """Count nodes in graph."""
        return (
            self.session.query(NodeModel)
            .filter(
                and_(
                    NodeModel.tenant_id == self.tenant_id,
                    NodeModel.graph_id == graph_id,
                )
            )
            .count()
        )

    def count(self, graph_id: str) -> int:
        """Compatibility alias used by API routers."""
        return self.count_nodes(graph_id)

    def count_atoms(self, graph_id: str) -> int:
        """Count atom nodes in graph."""
        return (
            self.session.query(NodeModel)
            .filter(
                and_(
                    NodeModel.tenant_id == self.tenant_id,
                    NodeModel.graph_id == graph_id,
                    NodeModel.kind == "atom",
                )
            )
            .count()
        )

    def count_macros(self, graph_id: str) -> int:
        """Count macro nodes in graph."""
        return (
            self.session.query(NodeModel)
            .filter(
                and_(
                    NodeModel.tenant_id == self.tenant_id,
                    NodeModel.graph_id == graph_id,
                    NodeModel.kind == "macro",
                )
            )
            .count()
        )

    def delete_node(self, graph_id: str, node_id: UUID) -> bool:
        """Delete a node.

        Returns True if deleted, False if not found.
        """
        node = self.get_node(graph_id, node_id)
        if node:
            self.session.delete(node)
            self.session.flush()
            return True
        return False

    def touch_node(self, graph_id: str, node_id: UUID) -> None:
        """Increment touch_count and update last_access."""
        node = self.get_node(graph_id, node_id)
        if node:
            node.touch_count += 1
            node.last_access = datetime.now(timezone.utc)
            self.session.flush()

    def get_all_vectors(self, graph_id: str) -> List[tuple]:
        """Get all (node_id, v_native) pairs for similarity computation.

        Returns list of (node_id, v_native).
        """
        nodes = (
            self.session.query(
                NodeModel.node_id,
                NodeModel.v_native,
            )
            .filter(
                and_(
                    NodeModel.tenant_id == self.tenant_id,
                    NodeModel.graph_id == graph_id,
                )
            )
            .order_by(
                asc(NodeModel.created_at),
                asc(NodeModel.node_id),
            )
            .all()
        )
        return [(n.node_id, n.v_native) for n in nodes]

    def get_all_vectors_with_level(self, graph_id: str) -> List[tuple]:
        """Get all (node_id, v_native, level) tuples for semantic type classification.

        Used by engine_native._build_semantic_parents_data to classify inheritance
        edge semantic types based on node level comparison.

        Returns:
            List[tuple]: Each tuple is (node_id, v_native, level)
        """
        nodes = (
            self.session.query(
                NodeModel.node_id,
                NodeModel.v_native,
                NodeModel.level,
            )
            .filter(
                and_(
                    NodeModel.tenant_id == self.tenant_id,
                    NodeModel.graph_id == graph_id,
                )
            )
            .order_by(
                asc(NodeModel.created_at),
                asc(NodeModel.node_id),
            )
            .all()
        )
        return [
            (n.node_id, n.v_native, n.level or 0)
            for n in nodes
        ]


# Exports
__all__ = ["NodeRepo"]
