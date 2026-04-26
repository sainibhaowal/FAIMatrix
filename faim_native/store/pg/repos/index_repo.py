"""Index-facing repo helpers for Phase 5 scale pipeline."""

from __future__ import annotations

from typing import List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

try:
    from faim.Faim_Native.index.deterministic_ann import VectorPoint
    from faim.Faim_Native.store.pg.repos.node_repo import NodeRepo
    from faim.Faim_Native.store.pg.repos.representation_repo import RepresentationRepo
except (ImportError, RuntimeError):
    from index.deterministic_ann import VectorPoint

    from store.pg.repos.node_repo import NodeRepo
    from store.pg.repos.representation_repo import RepresentationRepo


class IndexRepo:
    """Loader helpers for graph-scoped phase-5 acceleration structures."""

    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    def load_representation_rows(self, graph_id: str):
        return RepresentationRepo(
            session=self.session, tenant_id=self.tenant_id
        ).list_all(graph_id)

    def load_vector_points(self, graph_id: str) -> List[VectorPoint]:
        node_repo = NodeRepo(session=self.session, tenant_id=self.tenant_id)
        rows: List[Tuple[UUID, object]] = node_repo.get_all_vectors(graph_id)
        return [
            VectorPoint(
                node_id=node_id,
                vector=tuple(float(x) for x in (values or [])),
            )
            for node_id, values in rows
        ]


__all__ = ["IndexRepo"]
