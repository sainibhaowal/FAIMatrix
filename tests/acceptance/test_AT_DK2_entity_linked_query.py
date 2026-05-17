from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from faim_native.core.contracts.types import BlockAnchor, EvidenceBlock
from faim_native.core.engine_native import FAIMNativeEngine
from faim_native.encoding.representation_v2 import build_representation_v2_for_block
from faim_native.encoding.text_vectorizer import vectorize_blocks
from faim_native.orchestration.domain_knowledge_import import (
    run_domain_knowledge_import,
)
from faim_native.orchestration.ingest_flow import FAIMProfile
from faim_native.orchestration.query_flow import run_query
from faim_native.store.pg.models_faim import Base
from faim_native.store.pg.repos.edge_repo import EdgeRepo
from faim_native.store.pg.repos.event_repo import EventRepo
from faim_native.store.pg.repos.graph_version_repo import GraphVersionRepo
from faim_native.store.pg.repos.node_repo import NodeRepo


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_query_uses_domain_knowledge_scores():
    session = _session()
    try:
        tenant_id = "tenant_dkq"
        graph_id = "graph_dkq"
        block = EvidenceBlock.create(
            raw_id="raw-1",
            anchor=BlockAnchor(doc_type="text", char_start=0, char_end=64),
            content="Acme revenue reached 10M in 2026.",
            block_type="text",
        )
        vectors = vectorize_blocks([block])
        reprs = [build_representation_v2_for_block(block)]
        engine = FAIMNativeEngine(
            node_repo=NodeRepo(session=session, tenant_id=tenant_id),
            edge_repo=EdgeRepo(session=session, tenant_id=tenant_id),
            event_repo=EventRepo(session=session, tenant_id=tenant_id),
            graph_version_repo=GraphVersionRepo(session=session, tenant_id=tenant_id),
        )
        engine.write_atoms(graph_id=graph_id, vectors=vectors, reprs_v2=reprs)
        run_domain_knowledge_import(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            kb_rows=[
                {
                    "entity": "Acme",
                    "relation": "revenue",
                    "value": "10M",
                    "time": "2026",
                    "source_id": "kb-1",
                }
            ],
            domain_pack="finance",
            node_repo=NodeRepo(session=session, tenant_id=tenant_id),
            edge_repo=EdgeRepo(session=session, tenant_id=tenant_id),
            gv_repo=GraphVersionRepo(session=session, tenant_id=tenant_id),
            event_repo=EventRepo(session=session, tenant_id=tenant_id),
        )
        result = run_query(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            query_text="Acme revenue 2026",
            k=5,
            profile=FAIMProfile.STRICT,
            return_explain=True,
        )
        assert result.results
        assert result.results[0]["score_components"].get("domain", 0.0) >= 0.0
    finally:
        session.close()
