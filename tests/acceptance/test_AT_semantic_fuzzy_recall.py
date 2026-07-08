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


def test_semantic_fuzzy_recall_prefers_alias_and_phrase_aligned_evidence():
    session = _session()
    try:
        tenant_id = "tenant_semantic_fuzzy"
        graph_id = "graph-semantic-fuzzy"
        blocks = [
            EvidenceBlock.create(
                raw_id="raw-strong",
                anchor=BlockAnchor(doc_type="text", char_start=0, char_end=96),
                content="AI revenue improved 15% before the 2026 acquisition in München.",
                block_type="text",
            ),
            EvidenceBlock.create(
                raw_id="raw-weak",
                anchor=BlockAnchor(doc_type="text", char_start=0, char_end=72),
                content="Warehouse inventory changed slightly during last winter.",
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
                query_text="artificial intelligence earnings growth before 2026 in Munchen",
                k=2,
                profile=FAIMProfile.STRICT,
                return_explain=True,
                index=None,
                cache=None,
            )

        assert result.results
        top = result.results[0]
        assert top["evidence"]["raw_id"] == "raw-strong"
        assert top["score_components"].get("phasec", 0.0) > 0.0
        assert top["score_components"].get("phasec_alias_bridge", 0.0) > 0.0
        assert top["score_components"].get("phasec_translit_bridge", 0.0) > 0.0
        assert "late_interaction" in top["explain"]["fusion_summary"]["active_layers"]
        assert top["explain"]["phaseC_late_interaction"]["matched_units"]["alias"]
    finally:
        session.close()
