"""Acceptance tests for Phase 4 reranker v2 proposition and evidence matching."""

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


def test_phase4_query_prefers_matching_proposition_and_exposes_explain():
    session = _session()
    try:
        tenant_id = "test_tenant"
        graph_id = "graph-rr1"
        blocks = [
            EvidenceBlock.create(
                raw_id="raw-berlin",
                anchor=BlockAnchor(doc_type="text", char_start=0, char_end=64),
                content="Atlas lives in Berlin in 2026.",
                block_type="text",
            ),
            EvidenceBlock.create(
                raw_id="raw-inventory",
                anchor=BlockAnchor(doc_type="text", char_start=0, char_end=64),
                content="Warehouse inventory changed yesterday.",
                block_type="text",
            ),
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
                k=2,
                profile=FAIMProfile.STRICT,
                return_explain=True,
                index=None,
                cache=None,
            )

        assert result.results
        first = result.results[0]
        assert first["evidence"]["raw_id"] == "raw-berlin"
        assert first["score_components"].get("phase4", 0.0) > 0.0
        assert "phase4_reranker" in first["explain"]
        assert first["score_components"].get("phasec", 0.0) > 0.0
        assert "phaseC_late_interaction" in first["explain"]
    finally:
        session.close()
