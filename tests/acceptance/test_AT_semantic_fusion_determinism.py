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


def test_semantic_fusion_determinism_is_stable_across_repeated_runs():
    session = _session()
    try:
        tenant_id = "tenant_fusion_determinism"
        graph_id = "graph-fusion-determinism"
        blocks = [
            EvidenceBlock.create(
                raw_id="raw-a",
                anchor=BlockAnchor(doc_type="text", char_start=0, char_end=80),
                content="AI revenue improved before 2026 and supported multilingual reporting.",
                block_type="text",
            ),
            EvidenceBlock.create(
                raw_id="raw-b",
                anchor=BlockAnchor(doc_type="text", char_start=0, char_end=80),
                content="Inventory reports were archived without revenue context.",
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
            first = run_query(
                session=session,
                tenant_id=tenant_id,
                graph_id=graph_id,
                query_text="artificial intelligence revenue before 2026 translation",
                k=2,
                profile=FAIMProfile.STRICT,
                return_explain=True,
                index=None,
                cache=None,
            )
            second = run_query(
                session=session,
                tenant_id=tenant_id,
                graph_id=graph_id,
                query_text="artificial intelligence revenue before 2026 translation",
                k=2,
                profile=FAIMProfile.STRICT,
                return_explain=True,
                index=None,
                cache=None,
            )

        assert [item["node_id"] for item in first.results] == [
            item["node_id"] for item in second.results
        ]
        first_fusion = first.results[0]["explain"]["fusion_summary"]
        second_fusion = second.results[0]["explain"]["fusion_summary"]
        assert first_fusion["active_layers"] == second_fusion["active_layers"]
        assert first_fusion["strongest_layers"] == second_fusion["strongest_layers"]
        assert first_fusion["strongest_signals"] == second_fusion["strongest_signals"]
        assert (
            first.results[0]["explain"]["query_fusion_summary"]
            == second.results[0]["explain"]["query_fusion_summary"]
        )
        first_ledger = first.results[0]["explain"]["reason_source_ledger"]
        second_ledger = second.results[0]["explain"]["reason_source_ledger"]
        assert first_ledger["protocol"] == "pulse-v2"
        assert first_ledger["trace_id"] == second_ledger["trace_id"]
        assert first_ledger["source_summary"] == second_ledger["source_summary"]
        assert first.results[0]["explain"]["pulse_event_stream"]
        assert [
            event["event_id"]
            for event in first.results[0]["explain"]["pulse_event_stream"]
        ] == [
            event["event_id"]
            for event in second.results[0]["explain"]["pulse_event_stream"]
        ]
        assert "late_interaction" in first.results[0]["explain"]["fusion_summary"]["active_layers"]
    finally:
        session.close()
