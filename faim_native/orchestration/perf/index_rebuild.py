"""Phase 5 in-memory acceleration builders.

These helpers materialize deterministic sparse and dense acceleration structures
from the current graph truth. They are rebuilt on demand and are never a second
source of truth.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

try:
    from faim.Faim_Native.index.deterministic_ann import VPTreeNode, build_vptree
    from faim.Faim_Native.index.inverted_index import InvertedIndex
    from faim.Faim_Native.store.pg.models_faim import NodeModel
    from faim.Faim_Native.store.pg.repos.index_repo import IndexRepo
except (ImportError, RuntimeError):
    from index.deterministic_ann import VPTreeNode, build_vptree
    from index.inverted_index import InvertedIndex
    from store.pg.models_faim import NodeModel
    from store.pg.repos.index_repo import IndexRepo


@dataclass(frozen=True)
class CachedNodeMeta:
    node_id: UUID
    raw_id: Optional[str]
    block_id: Optional[str]
    anchor_json: Optional[Dict[str, Any]]
    level: int
    touch_count: int
    vector_hash: str
    v_native: Tuple[float, ...]
    opp_signature: Dict[str, Any]
    created_at: Optional[datetime]
    valid_from: Optional[datetime]
    valid_to: Optional[datetime]
    last_access: Optional[datetime]
    residual: int
    v_embedding: Any = None


@dataclass(frozen=True)
class GraphIndexArtifacts:
    sparse_index: InvertedIndex
    ann_root: Optional[VPTreeNode]
    node_meta: Optional[Dict[UUID, CachedNodeMeta]] = None


_INDEX_ARTIFACT_CACHE: (
    "OrderedDict[Tuple[str, str, int, bool], GraphIndexArtifacts]"
) = OrderedDict()
_INDEX_ARTIFACT_CACHE_LOCK = RLock()
_INDEX_ARTIFACT_CACHE_MAX_SIZE = 16


def build_graph_index_artifacts(
    session: Session,
    tenant_id: str,
    graph_id: str,
    *,
    include_dense: bool = True,
) -> GraphIndexArtifacts:
    repo = IndexRepo(session=session, tenant_id=tenant_id)
    sparse_rows = repo.load_representation_rows(graph_id)
    sparse_index = InvertedIndex.build(sparse_rows)
    # Large production graphs use the persistent Qdrant ANN index for dense
    # recall.  Keep the legacy in-process VP-tree available for small graphs
    # and compatibility callers, but do not materialize every SQL vector in a
    # long-lived request transaction when the caller has a persistent ANN.
    ann_root = None
    if include_dense:
        vector_points = repo.load_vector_points(graph_id)
        ann_root = build_vptree(vector_points)

    node_rows = (
        session.query(
            NodeModel.node_id,
            NodeModel.raw_id,
            NodeModel.block_id,
            NodeModel.anchor_json,
            NodeModel.level,
            NodeModel.touch_count,
            NodeModel.vector_hash,
            NodeModel.v_native,
            NodeModel.opp_signature,
            NodeModel.created_at,
            NodeModel.valid_from,
            NodeModel.valid_to,
            NodeModel.last_access,
            NodeModel.residual,
        )
        .filter(NodeModel.tenant_id == tenant_id, NodeModel.graph_id == graph_id)
        .all()
    )
    node_meta = {
        r.node_id: CachedNodeMeta(
            node_id=r.node_id,
            raw_id=r.raw_id,
            block_id=r.block_id,
            anchor_json=r.anchor_json,
            level=int(r.level or 0),
            touch_count=int(r.touch_count or 0),
            vector_hash=str(r.vector_hash or ""),
            v_native=tuple(r.v_native) if r.v_native is not None else (),
            opp_signature=r.opp_signature if isinstance(r.opp_signature, dict) else {},
            created_at=r.created_at,
            valid_from=r.valid_from,
            valid_to=r.valid_to,
            last_access=r.last_access,
            residual=int(r.residual or 0),
        )
        for r in node_rows
    }
    return GraphIndexArtifacts(
        sparse_index=sparse_index, ann_root=ann_root, node_meta=node_meta
    )


def get_graph_index_artifacts(
    session: Session,
    tenant_id: str,
    graph_id: str,
    graph_version: int,
    *,
    include_dense: bool = True,
) -> GraphIndexArtifacts:
    """Return graph-index artifacts with graph-versioned in-process caching."""
    cache_key = (tenant_id, graph_id, int(graph_version), bool(include_dense))
    with _INDEX_ARTIFACT_CACHE_LOCK:
        cached = _INDEX_ARTIFACT_CACHE.get(cache_key)
        if cached is not None:
            _INDEX_ARTIFACT_CACHE.move_to_end(cache_key)
            return cached

    artifacts = build_graph_index_artifacts(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
        include_dense=include_dense,
    )

    with _INDEX_ARTIFACT_CACHE_LOCK:
        _INDEX_ARTIFACT_CACHE[cache_key] = artifacts
        _INDEX_ARTIFACT_CACHE.move_to_end(cache_key)
        while len(_INDEX_ARTIFACT_CACHE) > _INDEX_ARTIFACT_CACHE_MAX_SIZE:
            _INDEX_ARTIFACT_CACHE.popitem(last=False)
    return artifacts


__all__ = [
    "GraphIndexArtifacts",
    "build_graph_index_artifacts",
    "get_graph_index_artifacts",
]
