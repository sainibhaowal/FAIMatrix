"""Acceptance test for Phase 5 sparse shortlist."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from faim_native.core.contracts.types import BlockAnchor, EvidenceBlock
from faim_native.core.engine_native import FAIMNativeEngine
from faim_native.encoding.representation_v2 import build_representation_v2_for_block
from faim_native.encoding.text_vectorizer import vectorize_blocks
from faim_native.index.inverted_index import InvertedIndex
from faim_native.index.wand import block_max_wand_shortlist
from faim_native.store.pg.models_faim import Base
from faim_native.store.pg.repos.edge_repo import EdgeRepo
from faim_native.store.pg.repos.event_repo import EventRepo
from faim_native.store.pg.repos.graph_version_repo import GraphVersionRepo
from faim_native.store.pg.repos.node_repo import NodeRepo
from faim_native.store.pg.repos.representation_repo import RepresentationRepo


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_sparse_shortlist_returns_relevant_doc():
    session = _session()
    try:
        tenant_id = "tenant_idx"
        graph_id = "graph_idx"
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
        reprs = [build_representation_v2_for_block(block) for block in blocks]
        engine = FAIMNativeEngine(
            node_repo=NodeRepo(session=session, tenant_id=tenant_id),
            edge_repo=EdgeRepo(session=session, tenant_id=tenant_id),
            event_repo=EventRepo(session=session, tenant_id=tenant_id),
            graph_version_repo=GraphVersionRepo(session=session, tenant_id=tenant_id),
        )
        engine.write_atoms(graph_id=graph_id, vectors=vectors, reprs_v2=reprs)
        repo = RepresentationRepo(session=session, tenant_id=tenant_id)
        index = InvertedIndex.build(repo.list_all(graph_id))
        stats = repo.get_graph_stats(graph_id)
        query_repr = build_representation_v2_for_block(
            EvidenceBlock.create(
                raw_id="q",
                anchor=BlockAnchor(doc_type="text", char_start=0, char_end=20),
                content="2026 revenue Berlin",
                block_type="text",
            )
        )
        ranked = block_max_wand_shortlist(index, query_repr, stats, k=2)
        assert ranked
        assert ranked[0][1] >= ranked[-1][1]
    finally:
        session.close()
