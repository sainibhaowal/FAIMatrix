from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from faim_native.orchestration.domain_knowledge_import import (
    run_domain_knowledge_import,
)
from faim_native.store.pg.models_faim import Base, EdgeModel, NodeModel
from faim_native.store.pg.repos.edge_repo import EdgeRepo
from faim_native.store.pg.repos.event_repo import EventRepo
from faim_native.store.pg.repos.graph_version_repo import GraphVersionRepo
from faim_native.store.pg.repos.node_repo import NodeRepo


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_domain_knowledge_import_materializes_nodes_edges_and_lexicon():
    session = _session()
    try:
        tenant_id = "tenant_dk"
        graph_id = "graph_dk"
        result = run_domain_knowledge_import(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            kb_rows=[
                {
                    "entity": "Acme",
                    "relation": "revenue",
                    "value": "10M",
                    "time": "2026",
                    "aliases": ["ACME Corp"],
                    "source_id": "kb-1",
                }
            ],
            domain_pack="finance",
            node_repo=NodeRepo(session=session, tenant_id=tenant_id),
            edge_repo=EdgeRepo(session=session, tenant_id=tenant_id),
            gv_repo=GraphVersionRepo(session=session, tenant_id=tenant_id),
            event_repo=EventRepo(session=session, tenant_id=tenant_id),
        )
        assert result.lexicon_written >= 1
        kinds = {
            row.kind
            for row in session.query(NodeModel).filter_by(graph_id=graph_id).all()
        }
        assert {"entity", "relation", "fact", "value", "time"} <= kinds
        edge_kinds = {
            row.kind
            for row in session.query(EdgeModel).filter_by(graph_id=graph_id).all()
        }
        assert "entity_relation" in edge_kinds
        assert "fact_value" in edge_kinds
    finally:
        session.close()
