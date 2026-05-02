from __future__ import annotations

import os
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from faim_native.core.contracts.types import BlockAnchor, EvidenceBlock
from faim_native.core.engine_native import FAIMNativeEngine
from faim_native.encoding.representation_v2 import build_representation_v2_for_block
from faim_native.encoding.text_vectorizer import vectorize_blocks
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


def test_query_returns_phase9_answer_block():
    session = _session()
    try:
        tenant_id = "tenant_as1"
        graph_id = "graph_as1"
        blocks = [
            EvidenceBlock.create(
                raw_id="raw-berlin",
                anchor=BlockAnchor(doc_type="text", char_start=0, char_end=64),
                content="Atlas lives in Berlin in 2026.",
                block_type="text",
            )
        ]
        vectors = vectorize_blocks(blocks)
        reprs_v2 = [build_representation_v2_for_block(block) for block in blocks]
        engine = FAIMNativeEngine(
            node_repo=NodeRepo(session=session, tenant_id=tenant_id),
            edge_repo=EdgeRepo(session=session, tenant_id=tenant_id),
            event_repo=EventRepo(session=session, tenant_id=tenant_id),
            graph_version_repo=GraphVersionRepo(session=session, tenant_id=tenant_id),
        )
        engine.write_atoms(graph_id=graph_id, vectors=vectors, reprs_v2=reprs_v2)

        with patch.dict(os.environ, {"FAIM_REPR_V2_ENABLED": "true"}):
            result = run_query(
                session=session,
                tenant_id=tenant_id,
                graph_id=graph_id,
                query_text="Where does Atlas live in 2026?",
                k=3,
                profile=FAIMProfile.STRICT,
                return_explain=True,
                index=None,
                cache=None,
        )
        assert result.answer is not None
        assert "berlin" in result.answer["direct_answer"].lower()
        assert "2026" in result.answer["direct_answer"].lower()
        assert result.answer["citations"][0]["raw_id"] == "raw-berlin"
    finally:
        session.close()
