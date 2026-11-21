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
from threading import RLock
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
    from faim.Faim_Native.store.pg.repos.representation_repo import RepresentationRepo
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.antisym import merge_vectors, opposition_score, should_merge
    from core.operators.inheritance import compute_inheritance_plan
    from core.operators.semantic_typing import (
        SEMANTIC_WEIGHTS,
        build_semantic_meta,
        classify_semantic_type,
        should_create_semantic_edge,
    )
    from encoding.vector_schema import FAIMVector
    from store.pg.repos.edge_repo import EdgeRepo
    from store.pg.repos.event_repo import EventRepo
    from store.pg.repos.graph_version_repo import GraphVersionRepo
    from store.pg.repos.node_repo import NodeRepo
    from store.pg.repos.representation_repo import RepresentationRepo


_WRITE_SNAPSHOT_CACHE: Dict[
    Tuple[str, str],
    Tuple[int, List[Tuple[UUID, List[float], int, str]], Any],
] = {}
_WRITE_SNAPSHOT_LOCK = RLock()


def _build_norm_matrix(records: List[Tuple[UUID, List[float], int, str]]):
    import numpy as np

    if not records:
        return None
    mat = np.asarray([r[1] for r in records], dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return mat / norms


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
        reprs_v2: Optional[List[Any]] = None,
        embedding_vectors: Optional[List[Optional[List[float]]]] = None,
        valid_from: Optional[Any] = None,
        valid_to: Optional[Any] = None,
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
        repr_repo = RepresentationRepo(
            session=self.node_repo.session,
            tenant_id=self.node_repo.tenant_id,
        )

        # Snapshot the existing graph once.  The previous implementation
        # queried all vectors and then the first 100 nodes for every atom,
        # making ingest progressively slower as the graph grew.  The snapshot
        # preserves the repository's deterministic created_at/node_id order;
        # newly inserted nodes are appended as the current write advances.
        tenant_key = str(getattr(self.node_repo, "tenant_id", "") or "")
        cache_key = (tenant_key, graph_id)
        get_ver_fn = getattr(self.graph_version_repo, "get_version", None)
        cur_ver: Optional[int] = None
        if callable(get_ver_fn):
            try:
                cur_ver = int(get_ver_fn(self.node_repo.session, graph_id))
            except Exception:
                cur_ver = None

        candidate_records = None
        cached_matrix = None
        if cur_ver is not None:
            with _WRITE_SNAPSHOT_LOCK:
                cached = _WRITE_SNAPSHOT_CACHE.get(cache_key)
                if cached is not None and cached[0] == cur_ver:
                    candidate_records = list(cached[1])
                    cached_matrix = cached[2]
        if candidate_records is None:
            candidate_records = self.node_repo.get_all_vectors_with_level_and_hash(graph_id)
            try:
                cached_matrix = _build_norm_matrix(candidate_records)
            except Exception:
                cached_matrix = None
        candidate_ids = {record[0] for record in candidate_records}

        # Import cognitive typing for neural constellation classification
        try:
            from faim.Faim_Native.core.cognitive.cognitive_typing import (
                classify_for_constellation,
            )
        except ImportError:
            from core.cognitive.cognitive_typing import (
                classify_for_constellation,
            )

        for idx, vector in enumerate(vectors):
            # 1. Classify cognitive type for neural constellation view
            # Extract text from anchor_dict for classification
            text_content = ""
            if vector.anchor_dict:
                text_content = vector.anchor_dict.get("text", "")
                if not text_content and "canonical" in vector.anchor_dict:
                    text_content = vector.anchor_dict.get("canonical", "")

            classification = classify_for_constellation(
                text=text_content,
                raw_id=raw_id or "unknown",
                context={"source_type": "document"},
            )

            # 2. Upsert atom node with cognitive classification and semantic embedding
            emb_vec = (
                embedding_vectors[idx]
                if embedding_vectors and idx < len(embedding_vectors)
                else None
            )
            node_id = self.node_repo.upsert_atom_node(
                graph_id,
                vector,
                cognitive_type=classification.cognitive_type.value,
                galaxy_id=classification.galaxy_id,
                v_embedding=emb_vec,
                valid_from=valid_from,
                valid_to=valid_to,
            )
            result.node_ids.append(node_id)
            result.nodes_written += 1

            if reprs_v2 and idx < len(reprs_v2) and reprs_v2[idx] is not None:
                repr_repo.upsert_node_representation(
                    graph_id=graph_id,
                    node_id=node_id,
                    representation=reprs_v2[idx],
                )

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
            candidates_with_level = [
                (candidate_id, candidate_vector, candidate_level)
                for candidate_id, candidate_vector, candidate_level, _ in candidate_records
                if candidate_id != node_id
            ]

            if candidates_with_level:
                # Extract (UUID, vector) for compute_inheritance_plan
                candidates_for_plan = [(nid, v) for nid, v, _ in candidates_with_level]

                plan = self._compute_inheritance_plan_fast(
                    child_vector=list(vector.v_native),
                    candidates=candidates_for_plan,
                    k=self.parent_top_k,
                    precomputed_norm_matrix=cached_matrix,
                    skip_id=node_id,
                    record_ids=[r[0] for r in candidate_records],
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
                merge_candidates = self._get_merge_candidates_from_snapshot(
                    candidate_records=candidate_records,
                    target_id=node_id,
                    target_vector=list(vector.v_native),
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

            if node_id not in candidate_ids:
                candidate_records.append(
                    (
                        node_id,
                        list(vector.v_native),
                        int(vector.level or 0),
                        vector.vector_hash,
                    )
                )
                candidate_ids.add(node_id)
                if cached_matrix is not None:
                    try:
                        import numpy as np

                        row = np.asarray(vector.v_native, dtype=np.float32)
                        rn = float(np.linalg.norm(row))
                        if rn > 0.0:
                            row = row / rn
                        cached_matrix = np.vstack([cached_matrix, row.reshape(1, -1)])
                    except Exception:
                        cached_matrix = None

        # 5. Bump graph version
        new_version = self.graph_version_repo.bump(
            self.node_repo.session,
            graph_id=graph_id,
            reason=f"write_atoms: {result.nodes_written} nodes",
        )
        result.graph_version = new_version
        if isinstance(new_version, int):
            with _WRITE_SNAPSHOT_LOCK:
                if len(_WRITE_SNAPSHOT_CACHE) >= 32 and cache_key not in _WRITE_SNAPSHOT_CACHE:
                    _WRITE_SNAPSHOT_CACHE.pop(next(iter(_WRITE_SNAPSHOT_CACHE)))
                _WRITE_SNAPSHOT_CACHE[cache_key] = (
                    int(new_version),
                    list(candidate_records),
                    cached_matrix,
                )

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

        # 6. Track Coactivation synchronously
        if len(result.node_ids) >= 2:
            self.node_repo.track_coactivation(graph_id, result.node_ids)

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

    @staticmethod
    def _compute_inheritance_plan_fast(
        *,
        child_vector: List[float],
        candidates: List[Tuple[UUID, List[float]]],
        k: int,
        precomputed_norm_matrix: Any = None,
        skip_id: Optional[UUID] = None,
        record_ids: Optional[List[UUID]] = None,
    ):
        """Select exact parents with a vectorized similarity pass.

        Parent selection is mathematically the same cosine ranking as
        ``compute_inheritance_plan``.  NumPy performs the dense dot products
        in native code, avoiding a Python loop over every existing node for
        every newly ingested atom.  The canonical operator remains the
        fallback for environments without NumPy and for the final fraction /
        residual calculation on the bounded top-k set.
        """
        if not candidates:
            return compute_inheritance_plan(
                child_vector=child_vector,
                candidates=candidates,
                k=k,
            )
        try:
            import numpy as np

            child = np.asarray(child_vector, dtype=np.float32)
            child_norm = float(np.linalg.norm(child))
            if child_norm == 0.0:
                return compute_inheritance_plan(
                    child_vector=child_vector,
                    candidates=candidates,
                    k=k,
                )
            child_unit = child / child_norm
            if (
                precomputed_norm_matrix is not None
                and record_ids is not None
                and precomputed_norm_matrix.shape[0] == len(record_ids)
            ):
                similarities = precomputed_norm_matrix @ child_unit
                if skip_id is not None:
                    mask_idx = [i for i, nid in enumerate(record_ids) if nid == skip_id]
                    if mask_idx:
                        similarities = similarities.copy()
                        for i in mask_idx:
                            similarities[i] = -1.0
                if len(record_ids) > k:
                    top_idx = np.argpartition(-similarities, k)[: max(k * 2, k + 8)]
                    ranked = sorted(
                        (int(i) for i in top_idx),
                        key=lambda index: (
                            -float(similarities[index]),
                            str(record_ids[index]),
                        ),
                    )
                else:
                    ranked = sorted(
                        range(len(record_ids)),
                        key=lambda index: (
                            -float(similarities[index]),
                            str(record_ids[index]),
                        ),
                    )
                cand_vec_map = {nid: vec for nid, vec in candidates}
                selected = [
                    (record_ids[index], cand_vec_map[record_ids[index]])
                    for index in ranked[:k]
                    if float(similarities[index]) > 0.0
                    and record_ids[index] in cand_vec_map
                ]
                return compute_inheritance_plan(
                    child_vector=child_vector,
                    candidates=selected,
                    k=k,
                )

            node_ids = [node_id for node_id, _vector in candidates]
            matrix = np.asarray(
                [vector for _node_id, vector in candidates], dtype=np.float32
            )
            norms = np.linalg.norm(matrix, axis=1)
            similarities = np.divide(
                matrix @ child_unit,
                norms,
                out=np.zeros(len(candidates), dtype=np.float32),
                where=norms != 0,
            )
            if len(node_ids) > k:
                top_idx = np.argpartition(-similarities, k)[: max(k * 2, k + 8)]
                ranked = sorted(
                    (int(i) for i in top_idx),
                    key=lambda index: (-float(similarities[index]), str(node_ids[index])),
                )
            else:
                ranked = sorted(
                    range(len(node_ids)),
                    key=lambda index: (-float(similarities[index]), str(node_ids[index])),
                )
            selected = [
                (node_ids[index], candidates[index][1])
                for index in ranked[:k]
                if float(similarities[index]) > 0.0
            ]
            return compute_inheritance_plan(
                child_vector=child_vector,
                candidates=selected,
                k=k,
            )
        except (ImportError, ValueError, TypeError):
            return compute_inheritance_plan(
                child_vector=child_vector,
                candidates=candidates,
                k=k,
            )

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

    def _get_merge_candidates_from_snapshot(
        self,
        *,
        candidate_records: List[Tuple[UUID, List[float], int, str]],
        target_id: UUID,
        target_vector: List[float],
        exclude_ids: set,
    ) -> List[Tuple[UUID, str, float]]:
        """Return merge candidates from the ordered ingest snapshot.

        ``_get_merge_candidates`` remains available for callers outside the
        batched write path.  This variant has the same first-100 deterministic
        candidate window without issuing a database query per atom.
        """
        candidates = []
        for node_id, node_vector, _level, vector_hash in candidate_records[:100]:
            if node_id == target_id or node_id in exclude_ids:
                continue
            score = opposition_score(target_vector, node_vector)
            if score >= self.antisym_threshold:
                candidates.append((node_id, vector_hash, score))
        candidates.sort(key=lambda item: (-item[2], item[1]))
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
        for parent_id, cosine_sim in zip(plan.parents, plan.similarities, strict=False):
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
