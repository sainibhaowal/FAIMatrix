"""FAIM-Native Engine.

Core write operations with inheritance, antisym, and event emission.

NO ML MODELS. NO RANDOMNESS.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

# Flexible imports
try:
    from faim.Faim_Native.core.antisym import find_merge_candidates  # noqa: F401, I001
    from faim.Faim_Native.core.antisym import (
        merge_vectors,
        opposition_score,
        should_merge,
    )
    from faim.Faim_Native.core.contracts.types import uuid7  # noqa: F401
    from faim.Faim_Native.core.operators.inheritance import (  # noqa: F401
        InheritancePlan,
        compute_inheritance_plan,
    )
    from faim.Faim_Native.core.operators.semantic_typing import (
        classify_semantic_type,
        build_semantic_meta,
        should_create_semantic_edge,
        SEMANTIC_WEIGHTS,
    )
    from faim.Faim_Native.encoding.vector_schema import FAIMVector
    from faim.Faim_Native.store.pg.models_faim import EdgeModel, NodeModel  # noqa: F401
    from faim.Faim_Native.store.pg.repos.edge_repo import EdgeRepo
    from faim.Faim_Native.store.pg.repos.event_repo import EventRepo
    from faim.Faim_Native.store.pg.repos.graph_version_repo import GraphVersionRepo
    from faim.Faim_Native.store.pg.repos.node_repo import NodeRepo
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.antisym import merge_vectors, opposition_score, should_merge
    from core.operators.inheritance import compute_inheritance_plan
    from core.operators.semantic_typing import (
        classify_semantic_type,
        build_semantic_meta,
        should_create_semantic_edge,
        SEMANTIC_WEIGHTS,
    )
    from encoding.vector_schema import FAIMVector
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.graph_version_repo import GraphVersionRepo
    from store.pg.repos.node_repo import NodeRepo


@dataclass
class WriteResult:
    """Result of a write operation.

    Attributes:
        nodes_written: Number of nodes upserted.
        edges_written: Number of inheritance edges created.
        merges: Number of merge operations.
        events_emitted: Number of events emitted.
        graph_version: New graph version after write.
        node_ids: List of node IDs written.
    """

    nodes_written: int = 0
    edges_written: int = 0
    merges: int = 0
    events_emitted: int = 0
    graph_version: int = 0
    node_ids: List[UUID] = field(default_factory=list)


class FAIMNativeEngine:
    """FAIM-native engine for graph operations.

    Implements deterministic write_atoms with inheritance and antisym.
    """

    def __init__(
        self,
        node_repo: NodeRepo,
        edge_repo: EdgeRepo,
        event_repo: EventRepo,
        graph_version_repo: GraphVersionRepo,
        *,
        parent_top_k: int = 8,
        antisym_threshold: float = 0.95,
    ):
        """Initialize engine.

        Args:
            node_repo: Node repository.
            edge_repo: Edge repository.
            event_repo: Event repository.
            graph_version_repo: Graph version repository.
            parent_top_k: Max parents for inheritance.
            antisym_threshold: Threshold for merge.
        """
        self.node_repo = node_repo
        self.edge_repo = edge_repo
        self.event_repo = event_repo
        self.graph_version_repo = graph_version_repo
        self.parent_top_k = parent_top_k
        self.antisym_threshold = antisym_threshold

    def write_atoms(
        self,
        graph_id: str,
        vectors: List[FAIMVector],
        raw_id: Optional[str] = None,
        packet_hash: Optional[str] = None,
    ) -> WriteResult:
        """Write atom vectors to graph.

        For each vector:
        1. Upsert atom node
        2. Select parents and set inheritance edges
        3. Antisym scan for merge candidates
        4. Emit events
        5. Bump graph version

        Args:
            graph_id: Graph identifier.
            vectors: List of FAIMVectors to write.

        Returns:
            WriteResult summary.
        """
        result = WriteResult()
        merged_ids = set()

        for vector in vectors:
            # 1. Upsert atom node
            node_id = self.node_repo.upsert_atom_node(graph_id, vector)
            result.node_ids.append(node_id)
            result.nodes_written += 1

            # Emit NODE_UPSERT event
            self._emit_event(
                graph_id=graph_id,
                kind="NODE_UPSERT",
                payload={
                    "node_id": str(node_id),
                    "vector_hash": vector.vector_hash,
                    "block_id": vector.block_id,
                },
            )
            result.events_emitted += 1

            # 2. Compute inheritance
            candidates_with_level = self._get_parent_candidates(graph_id, node_id)

            if candidates_with_level:
                # Extract (UUID, vector) for compute_inheritance_plan
                candidates_for_plan = [(nid, v) for nid, v, _ in candidates_with_level]

                plan = compute_inheritance_plan(
                    child_vector=list(vector.v_native),
                    candidates=candidates_for_plan,
                    k=self.parent_top_k,
                )

                if plan.parents:
                    # Build semantic metadata and edges for inheritance parents
                    parents_meta, semantic_edges = self._build_semantic_parents_data(
                        child_vector=list(vector.v_native),
                        child_level=vector.level,  # Atoms are level 0
                        plan=plan,
                        candidates=candidates_with_level,
                    )

                    # Set inheritance edges with semantic metadata (Layer A)
                    parents_with_fractions = list(
                        zip(plan.parents, plan.fractions, strict=False)
                    )
                    edge_ids = self.edge_repo.set_inheritance_parents(
                        graph_id=graph_id,
                        child_id=node_id,
                        parents=parents_with_fractions,
                        parents_meta=parents_meta,
                    )
                    result.edges_written += len(edge_ids)

                    # Create semantic edges (Layer B) for typed relationships
                    for parent_id, semantic_type, semantic_weight in semantic_edges:
                        self.edge_repo.add_semantic_edge(
                            graph_id=graph_id,
                            src_node_id=parent_id,
                            dst_node_id=node_id,
                            semantic_type=semantic_type,
                            semantic_weight=semantic_weight,
                            meta=None,
                        )

                    # Emit INHERITANCE_SET event
                    self._emit_event(
                        graph_id=graph_id,
                        kind="INHERITANCE_SET",
                        payload={
                            "child_id": str(node_id),
                            "parents": [str(p) for p in plan.parents],
                            "fractions": list(plan.fractions),
                            "residual": plan.residual,
                        },
                    )
                    result.events_emitted += 1

            # 3. Antisym scan
            if node_id not in merged_ids:
                merge_candidates = self._get_merge_candidates(
                    graph_id=graph_id,
                    target_id=node_id,
                    target_vector=list(vector.v_native),
                    target_hash=vector.vector_hash,
                    exclude_ids=merged_ids,
                )

                for cand_id, cand_hash, score in merge_candidates:
                    if should_merge(score, self.antisym_threshold):
                        merge_result = merge_vectors(
                            a_id=node_id,
                            b_id=cand_id,
                            a_hash=vector.vector_hash,
                            b_hash=cand_hash,
                            score=score,
                        )

                        # Mark loser as merged
                        merged_ids.add(merge_result.loser_id)

                        # Add opposition edge
                        self.edge_repo.add_opposition_edge(
                            graph_id=graph_id,
                            a_id=merge_result.winner_id,
                            b_id=merge_result.loser_id,
                            weight=score,
                            meta=merge_result.meta,
                        )

                        # Emit MERGE event
                        self._emit_event(
                            graph_id=graph_id,
                            kind="MERGE",
                            payload={
                                "winner_id": str(merge_result.winner_id),
                                "loser_id": str(merge_result.loser_id),
                                "score": score,
                            },
                        )
                        result.events_emitted += 1
                        result.merges += 1

                        # Only one merge per target
                        break

        # 5. Bump graph version
        new_version = self.graph_version_repo.bump(
            self.node_repo.session,
            graph_id=graph_id,
            reason=f"write_atoms: {result.nodes_written} nodes",
        )
        result.graph_version = new_version

        # Emit GRAPH_VERSION_BUMP event
        self._emit_event(
            graph_id=graph_id,
            kind="GRAPH_VERSION_BUMP",
            payload={
                "version": new_version,
                "nodes_written": result.nodes_written,
                "edges_written": result.edges_written,
                "merges": result.merges,
            },
        )
        result.events_emitted += 1

        return result

    def _get_parent_candidates(
        self,
        graph_id: str,
        exclude_id: UUID,
    ) -> List[Tuple[UUID, List[float], int]]:
        """Get candidate parents for inheritance with node levels.

        Returns all existing nodes except the target as (node_id, vector, level).
        Level is used for semantic type classification (hypernym/hyponym decision).
        """
        all_vectors = self.node_repo.get_all_vectors_with_level(graph_id)
        return [(nid, v, lvl) for nid, v, lvl in all_vectors if nid != exclude_id]

    def _get_merge_candidates(
        self,
        graph_id: str,
        target_id: UUID,
        target_vector: List[float],
        target_hash: str,
        exclude_ids: set,
    ) -> List[Tuple[UUID, str, float]]:
        """Get merge candidates for antisym.

        Returns nodes similar to target.
        """
        nodes = self.node_repo.list_nodes(graph_id, limit=100)
        candidates = []

        for node in nodes:
            if node.node_id == target_id:
                continue
            if node.node_id in exclude_ids:
                continue

            score = opposition_score(target_vector, node.v_native)
            if score >= self.antisym_threshold:
                candidates.append((node.node_id, node.vector_hash, score))

        # Sort by score desc, hash asc
        candidates.sort(key=lambda x: (-x[2], x[1]))

        return candidates[:5]

    def _build_semantic_parents_data(
        self,
        child_vector: List[float],
        child_level: int,
        plan: InheritancePlan,
        candidates: List[Tuple[UUID, List[float], int]],
    ) -> Tuple[List[Optional[Dict]], List[Tuple[UUID, str, float]]]:
        """Build semantic metadata and edges for inheritance parents.

        For each parent in the plan, classify semantic type using cosine similarity
        and node level hierarchy, then build Layer A meta and Layer B edge rows.

        Args:
            child_vector: Child node's native vector.
            child_level: Child node's level in hierarchy (typically 0 for atoms).
            plan: InheritancePlan with selected parents and fractions.
            candidates: List of (parent_id, parent_vector, parent_level) tuples.

        Returns:
            Tuple of:
            - parents_meta: List[Optional[Dict]] parallel to plan.parents,
              each dict = {"semantic_type": str, "semantic_weight": float}
            - semantic_edges: List[Tuple[parent_id, semantic_type, semantic_weight]]
              for types where should_create_semantic_edge() is True.
        """
        # Build lookup: parent_id -> (vector, level)
        candidate_map = {nid: (vec, lvl) for nid, vec, lvl in candidates}

        parents_meta = []
        semantic_edges = []

        # Classify each parent using cosine similarity and level
        for parent_id, cosine_sim in zip(plan.parents, plan.similarities):
            if parent_id not in candidate_map:
                # Parent not in candidates (shouldn't happen, but be safe)
                parents_meta.append(None)
                continue

            parent_vector, parent_level = candidate_map[parent_id]

            # Classify semantic type deterministically
            semantic_type = classify_semantic_type(
                cosine_sim=cosine_sim,
                child_level=child_level,
                parent_level=parent_level,
            )

            # Layer A: Build meta dict for this parent
            meta = build_semantic_meta(semantic_type)
            parents_meta.append(meta)

            # Layer B: If this type warrants a semantic edge row, add it
            if should_create_semantic_edge(semantic_type):
                semantic_weight = SEMANTIC_WEIGHTS.get(semantic_type, 1.0)
                semantic_edges.append((parent_id, semantic_type, semantic_weight))

        return parents_meta, semantic_edges

    def _emit_event(
        self,
        graph_id: str,
        kind: str,
        payload: Dict[str, Any],
    ) -> None:
        """Emit an event to the journal."""
        if self.event_repo:
            self.event_repo.emit(
                session=self.node_repo.session,
                graph_id=graph_id,
                kind=kind,
                payload=payload,
            )

    def compute_graph_hash(self, graph_id: str) -> str:
        """Compute deterministic hash of graph state.

        Hash includes:
        - Sorted list of (node_id, vector_hash, level, residual)
        - Sorted list of (edge_id, src, dst, kind, weight)
        """
        # Get nodes sorted
        nodes = self.node_repo.list_nodes(graph_id, limit=10000)
        node_data = []
        for n in nodes:
            node_data.append(
                (
                    str(n.node_id),
                    n.vector_hash,
                    n.level,
                    n.residual / 1e9 if n.residual else 0.0,
                )
            )
        node_data.sort()

        # Get edges sorted
        edges = self.edge_repo.list_all_edges(graph_id, limit=10000)
        edge_data = []
        for e in edges:
            edge_data.append(
                (
                    str(e.edge_id),
                    str(e.src_node_id),
                    str(e.dst_node_id),
                    e.kind,
                    e.weight / 1e9 if e.weight else 0.0,
                )
            )
        edge_data.sort()

        # Build canonical JSON
        canonical = {
            "nodes": node_data,
            "edges": edge_data,
        }
        json_str = json.dumps(canonical, sort_keys=True, separators=(",", ":"))

        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def get_graph_stats(self, graph_id: str) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "node_count": self.node_repo.count_nodes(graph_id),
            "atom_count": self.node_repo.count_atoms(graph_id),
            "macro_count": self.node_repo.count_macros(graph_id),
            "edge_count": self.edge_repo.count_edges(graph_id),
            "inheritance_edges": self.edge_repo.count_inheritance_edges(graph_id),
            "graph_version": self.graph_version_repo.get(graph_id),
        }


# Exports
__all__ = ["FAIMNativeEngine", "WriteResult"]
