"""Phase 5 in-memory acceleration builders.

These helpers materialize deterministic sparse and dense acceleration structures
from the current graph truth. They are rebuilt on demand and are never a second
source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

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


__all__ = ["GraphIndexArtifacts", "build_graph_index_artifacts"]
