"""Acceptance test for Representation V2 persistence and query fusion."""

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
from faim_native.store.pg.models_faim import (
    Base,
    GraphRepresentationStatsModel,
    NodeRepresentationV2Model,
)
from faim_native.store.pg.repos.edge_repo import EdgeRepo
from faim_native.store.pg.repos.event_repo import EventRepo
from faim_native.store.pg.repos.graph_version_repo import GraphVersionRepo
from faim_native.store.pg.repos.node_repo import NodeRepo


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_representation_v2_persists_and_affects_query_scores():
    session = _session()
    try:
        tenant_id = "test_tenant"
        graph_id = "graph-rv2"
        blocks = [
            EvidenceBlock.create(
                raw_id="raw-1",
                anchor=BlockAnchor(doc_type="text", char_start=0, char_end=64),
                content="Release 2026 revenue reached 15 percent in Berlin.",
                block_type="text",
            ),
            EvidenceBlock.create(
                raw_id="raw-2",
                anchor=BlockAnchor(doc_type="text", char_start=0, char_end=52),
                content="Warehouse inventory was adjusted yesterday.",
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

        assert (
            session.query(NodeRepresentationV2Model)
            .filter_by(tenant_id=tenant_id, graph_id=graph_id)
            .count()
            == 2
        )
        stored_repr = (
            session.query(NodeRepresentationV2Model)
            .filter_by(tenant_id=tenant_id, graph_id=graph_id)
            .first()
        )
        assert stored_repr is not None
        assert stored_repr.normalized_text
        assert (
            session.query(GraphRepresentationStatsModel)
            .filter_by(tenant_id=tenant_id, graph_id=graph_id)
            .count()
            == 6
        )

        with patch.dict(os.environ, {"FAIM_REPR_V2_ENABLED": "true"}):
            result = run_query(
                session=session,
                tenant_id=tenant_id,
                graph_id=graph_id,
                query_text="2026 revenue 15 percent",
                k=2,
                profile=FAIMProfile.STRICT,
                return_explain=False,
                index=None,
                cache=None,
            )

        assert result.results
        assert any(
            item["score_components"].get("lex", 0.0) > 0.0 for item in result.results
        )
    finally:
        session.close()
