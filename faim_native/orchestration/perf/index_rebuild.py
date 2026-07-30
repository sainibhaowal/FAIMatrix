"""Phase 5 in-memory acceleration builders.

These helpers materialize deterministic sparse and dense acceleration structures
from the current graph truth. They are rebuilt on demand and are never a second
source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import OrderedDict
from threading import RLock
from typing import Optional, Tuple

from sqlalchemy.orm import Session

try:
    from faim.Faim_Native.index.deterministic_ann import VPTreeNode, build_vptree
    from faim.Faim_Native.index.inverted_index import InvertedIndex
    from faim.Faim_Native.store.pg.repos.index_repo import IndexRepo
except (ImportError, RuntimeError):
    from index.deterministic_ann import VPTreeNode, build_vptree
    from index.inverted_index import InvertedIndex
    from store.pg.repos.index_repo import IndexRepo


@dataclass(frozen=True)
class GraphIndexArtifacts:
    sparse_index: InvertedIndex
    ann_root: Optional[VPTreeNode]


_INDEX_ARTIFACT_CACHE: "OrderedDict[Tuple[str, str, int], GraphIndexArtifacts]" = (
    OrderedDict()
)
_INDEX_ARTIFACT_CACHE_LOCK = RLock()
_INDEX_ARTIFACT_CACHE_MAX_SIZE = 16


def build_graph_index_artifacts(
    session: Session,
    tenant_id: str,
    graph_id: str,
) -> GraphIndexArtifacts:
    repo = IndexRepo(session=session, tenant_id=tenant_id)
    sparse_rows = repo.load_representation_rows(graph_id)
    sparse_index = InvertedIndex.build(sparse_rows)
    vector_points = repo.load_vector_points(graph_id)
    ann_root = build_vptree(vector_points)
    return GraphIndexArtifacts(sparse_index=sparse_index, ann_root=ann_root)


def get_graph_index_artifacts(
    session: Session,
    tenant_id: str,
    graph_id: str,
    graph_version: int,
) -> GraphIndexArtifacts:
    """Return graph-index artifacts with graph-versioned in-process caching."""
    cache_key = (tenant_id, graph_id, int(graph_version))
    with _INDEX_ARTIFACT_CACHE_LOCK:
        cached = _INDEX_ARTIFACT_CACHE.get(cache_key)
        if cached is not None:
            _INDEX_ARTIFACT_CACHE.move_to_end(cache_key)
            return cached

    artifacts = build_graph_index_artifacts(
        session=session,
        tenant_id=tenant_id,
        graph_id=graph_id,
    )

    with _INDEX_ARTIFACT_CACHE_LOCK:
        _INDEX_ARTIFACT_CACHE[cache_key] = artifacts
        _INDEX_ARTIFACT_CACHE.move_to_end(cache_key)
        while len(_INDEX_ARTIFACT_CACHE) > _INDEX_ARTIFACT_CACHE_MAX_SIZE:
            _INDEX_ARTIFACT_CACHE.popitem(last=False)
    return artifacts


__all__ = ["GraphIndexArtifacts", "build_graph_index_artifacts", "get_graph_index_artifacts"]
