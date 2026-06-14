"""Node Repository for FIG graph storage.

FAIM-native node operations with deterministic ordering.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from sqlalchemy import and_, asc, select, text
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
        *,
        cognitive_type: Optional[str] = None,
        galaxy_id: Optional[str] = None,
    ) -> UUID:
        """Upsert an atom node from FAIMVector.

        If node with same vector_hash exists, update it.
        Otherwise create new node.

        Args:
            graph_id: Graph identifier.
            vector: FAIMVector to store.
            cognitive_type: Cognitive classification (fact, event, procedure, etc.)
            galaxy_id: Source document/galaxy grouping ID.

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
            # Update cognitive fields if newly provided
            if cognitive_type and not existing.cognitive_type:
                existing.cognitive_type = cognitive_type
            if galaxy_id and not existing.galaxy_id:
                existing.galaxy_id = galaxy_id
            self.session.flush()
            return existing.node_id

        # Create new node with cognitive classification
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
            cognitive_type=cognitive_type,
            galaxy_id=galaxy_id,
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
        cognitive_type: Optional[str] = None,
        galaxy_id: Optional[str] = None,
    ) -> UUID:
        """Create a macro node (level > 0).

        Args:
            graph_id: Graph identifier.
            v_native: Vector values.
            vector_hash: Computed hash.
            opp_signature: Opposition signature.
            level: Hierarchy level (default 1).
            residual: Residual value.
            cognitive_type: Cognitive classification (fact, event, procedure, etc.)
            galaxy_id: Source document/galaxy grouping ID.

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
            cognitive_type=cognitive_type,
            galaxy_id=galaxy_id,
            created_at=now,
            updated_at=now,
        )
        self.session.add(node)
        self.session.flush()
        return node.node_id

    def upsert_special_node(
        self,
        graph_id: str,
        *,
        kind: str,
        vector_hash: str,
        v_native: List[float],
        opp_signature: Dict[str, float],
        residual: float = 0.0,
        level: int = 1,
        cognitive_type: Optional[str] = None,
        galaxy_id: Optional[str] = None,
    ) -> UUID:
        """Upsert a non-atom deterministic node such as a concept node."""
        existing = self.get_by_vector_hash(graph_id, vector_hash)
        now = datetime.now(timezone.utc)
        if existing:
            existing.kind = kind
            existing.v_native = v_native
            existing.opp_signature = opp_signature
            existing.residual = int(residual * 1e9)
            existing.level = level
            # Update cognitive fields if newly provided
            if cognitive_type and not existing.cognitive_type:
                existing.cognitive_type = cognitive_type
            if galaxy_id and not existing.galaxy_id:
                existing.galaxy_id = galaxy_id
            existing.updated_at = now
            self.session.flush()
            return existing.node_id
        node = NodeModel(
            node_id=uuid7(),
            tenant_id=self.tenant_id,
            graph_id=graph_id,
            kind=kind,
            vector_hash=vector_hash,
            raw_id=None,
            block_id=None,
            anchor_json=None,
            v_native=v_native,
            opp_signature=opp_signature,
            residual=int(residual * 1e9),
            level=level,
            touch_count=0,
            last_access=now,
            cognitive_type=cognitive_type,
            galaxy_id=galaxy_id,
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

    def get_by_id(
        self, graph_id: str, node_id: Union[UUID, str]
    ) -> Optional[NodeModel]:
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

    def list_by_ids(
        self,
        graph_id: str,
        node_ids: List[UUID],
    ) -> List[NodeModel]:
        """List nodes by explicit IDs with deterministic ordering."""
        if not node_ids:
            return []
        return (
            self.session.query(NodeModel)
            .filter(
                and_(
                    NodeModel.tenant_id == self.tenant_id,
                    NodeModel.graph_id == graph_id,
                    NodeModel.node_id.in_(list(node_ids)),
                )
            )
            .order_by(
                asc(NodeModel.created_at),
                asc(NodeModel.node_id),
            )
            .all()
        )

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

    def list_by_raw_id(
        self,
        graph_id: str,
        raw_id: str,
        *,
        kind: Optional[str] = None,
    ) -> List[NodeModel]:
        """List nodes for one raw file with deterministic ordering."""
        query = self.session.query(NodeModel).filter(
            and_(
                NodeModel.tenant_id == self.tenant_id,
                NodeModel.graph_id == graph_id,
                NodeModel.raw_id == str(raw_id),
            )
        )
        if kind is not None:
            query = query.filter(NodeModel.kind == kind)
        return query.order_by(
            asc(NodeModel.created_at),
            asc(NodeModel.node_id),
        ).all()

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
        return [(n.node_id, n.v_native, n.level or 0) for n in nodes]

    def find_redundant_pairs(self, graph_id: str, threshold: float, limit: int = 1000) -> List[tuple]:
        """Find highly similar node pairs using pgvector HNSW index.
        
        Uses a LATERAL join to force O(log N) index scans per node instead of O(N^2) Cartesian products.
        
        Returns:
            List of (node_id_a, node_id_b, similarity) ordered by most similar first.
        """
        stmt = text("""
            SELECT a.node_id, b.node_id, 1 - (a.v_vector <=> b.v_vector) as sim
            FROM nodes a
            CROSS JOIN LATERAL (
                SELECT b.node_id, b.v_vector
                FROM nodes b
                WHERE b.tenant_id = a.tenant_id 
                  AND b.graph_id = a.graph_id 
                  AND b.node_id != a.node_id
                ORDER BY a.v_vector <=> b.v_vector
                LIMIT 5
            ) b
            WHERE a.tenant_id = :tenant_id 
              AND a.graph_id = :graph_id
              AND 1 - (a.v_vector <=> b.v_vector) >= :threshold
            ORDER BY sim DESC
            LIMIT :limit
        """)
        
        results = self.session.execute(
            stmt, 
            {"tenant_id": self.tenant_id, "graph_id": graph_id, "threshold": threshold, "limit": limit}
        ).fetchall()
        
        return [(UUID(str(r[0])), UUID(str(r[1])), float(r[2])) for r in results]

    def get_max_similarities(self, graph_id: str, threshold: float) -> Dict[UUID, float]:
        """Find maximum similarity to any other node using pgvector.
        
        Uses a LATERAL join to perform O(log N) nearest-neighbor lookups.
        
        Returns:
            Dict mapping node_id to its highest similarity (only if >= threshold).
        """
        stmt = text("""
            SELECT a.node_id, 1 - (a.v_vector <=> b.v_vector) as max_sim
            FROM nodes a
            CROSS JOIN LATERAL (
                SELECT b.v_vector
                FROM nodes b
                WHERE b.tenant_id = a.tenant_id 
                  AND b.graph_id = a.graph_id 
                  AND b.node_id != a.node_id
                ORDER BY a.v_vector <=> b.v_vector
                LIMIT 1
            ) b
            WHERE a.tenant_id = :tenant_id 
              AND a.graph_id = :graph_id
              AND 1 - (a.v_vector <=> b.v_vector) >= :threshold
        """)
        
        results = self.session.execute(
            stmt, 
            {"tenant_id": self.tenant_id, "graph_id": graph_id, "threshold": threshold}
        ).fetchall()
        
        return {UUID(str(r[0])): float(r[1]) for r in results}

    def _compute_macro_hash(self, member_ids: List[str]) -> str:
        sorted_ids = sorted(member_ids)
        json_str = json.dumps(sorted_ids, separators=(",", ":"))
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def track_coactivation(self, graph_id: str, node_ids: List[UUID]) -> None:
        """Track a synchronous coactivation of nodes for invention.
        
        This executes an UPSERT on the coactivations table directly in the DB.
        """
        if len(node_ids) < 2:
            return
            
        str_ids = [str(n) for n in node_ids]
        signature = self._compute_macro_hash(str_ids)
        members_json = json.dumps(sorted(str_ids))
        
        # Cross-dialect UPSERT using SQLAlchemy text
        # For Postgres we use ON CONFLICT, for SQLite we use ON CONFLICT
        # since SQLite 3.24+ supports Postgres-style UPSERT!
        stmt = text("""
            INSERT INTO coactivations (tenant_id, graph_id, signature, members, coactivation_count, invented)
            VALUES (:tenant_id, :graph_id, :signature, :members, 1, FALSE)
            ON CONFLICT (tenant_id, graph_id, signature) DO UPDATE SET 
                coactivation_count = coactivations.coactivation_count + 1,
                updated_at = CURRENT_TIMESTAMP
        """)
        
        self.session.execute(
            stmt,
            {
                "tenant_id": self.tenant_id,
                "graph_id": graph_id,
                "signature": signature,
                "members": members_json
            }
        )
        self.session.flush()

    def get_pending_inventions(self, graph_id: str, min_count: int, limit: int = 100) -> List[dict]:
        """Fetch highly coactivated node sets that are pending invention."""
        stmt = text("""
            SELECT signature, members, coactivation_count
            FROM coactivations
            WHERE tenant_id = :tenant_id 
              AND graph_id = :graph_id 
              AND invented = FALSE 
              AND coactivation_count >= :min_count
            ORDER BY coactivation_count DESC, updated_at ASC
            LIMIT :limit
        """)
        
        results = self.session.execute(
            stmt,
            {"tenant_id": self.tenant_id, "graph_id": graph_id, "min_count": min_count, "limit": limit}
        ).fetchall()
        
        parsed = []
        for r in results:
            parsed.append({
                "signature": r[0],
                "members": json.loads(r[1]) if isinstance(r[1], str) else r[1],
                "count": r[2]
            })
        return parsed

    def mark_invented(self, graph_id: str, signature: str) -> None:
        """Mark a coactivation set as successfully invented."""
        stmt = text("""
            UPDATE coactivations
            SET invented = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE tenant_id = :tenant_id 
              AND graph_id = :graph_id 
              AND signature = :signature
        """)
        self.session.execute(
            stmt,
            {"tenant_id": self.tenant_id, "graph_id": graph_id, "signature": signature}
        )
        self.session.flush()


# Exports
__all__ = ["NodeRepo"]
