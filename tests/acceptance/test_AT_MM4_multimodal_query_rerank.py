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
from faim_native.orchestration.multimodal_backfill import run_multimodal_backfill
from faim_native.orchestration.query_flow import run_query
from faim_native.store.pg.models_faim import Base
from faim_native.store.pg.repos.edge_repo import EdgeRepo
from faim_native.store.pg.repos.event_repo import EventRepo
from faim_native.store.pg.repos.graph_version_repo import GraphVersionRepo
from faim_native.store.pg.repos.node_repo import NodeRepo


class _RawRef:
    def __init__(self, raw_id: str):
        self.id = raw_id


class _RawRepo:
    def get_by_id(self, session, raw_id):
        return _RawRef(raw_id)


class _RawStore:
    def __init__(self, payloads):
        self.payloads = payloads

    def load(self, raw_ref, verify=True):
        return self.payloads[str(raw_ref.id)]


class _StorageFileRow:
    def __init__(self, raw_id, filename, mime_type="application/pdf"):
        self.raw_id = raw_id
        self.filename = filename
        self.mime_type = mime_type


class _StorageFileRepo:
    def __init__(self, rows):
        self.rows = rows

    def list_files(
        self, session, graph_id, status, query, limit, offset, include_delete_requested
    ):
        items = self.rows[offset : offset + limit]
        return items, len(self.rows)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_multimodal_query_adds_modality_signal():
    session = _session()
    try:
        tenant_id = "tenant_mm_q"
        graph_id = "graph_mm_q"
        blocks = [
            EvidenceBlock.create(
                raw_id="raw-1",
                anchor=BlockAnchor(doc_type="pdf", page=1),
                content="invoice amount total due",
                block_type="ocr",
            )
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

        def _extract(file_bytes, filename, raw_id):
            return blocks

        run_multimodal_backfill(
            session=session,
            tenant_id=tenant_id,
            graph_id=graph_id,
            raw_repo=_RawRepo(),
            storage_file_repo=_StorageFileRepo(
                [_StorageFileRow("raw-1", "invoice.pdf")]
            ),
            raw_store=_RawStore({"raw-1": b"fake-pdf"}),
            node_repo=NodeRepo(session=session, tenant_id=tenant_id),
            gv_repo=GraphVersionRepo(session=session, tenant_id=tenant_id),
            event_repo=EventRepo(session=session, tenant_id=tenant_id),
            extract_fn=_extract,
        )

        with patch.dict(os.environ, {"FAIM_REPR_V2_ENABLED": "true"}):
            result = run_query(
                session=session,
                tenant_id=tenant_id,
                graph_id=graph_id,
                query_text="invoice total due",
                k=1,
                profile=FAIMProfile.STRICT,
                return_explain=False,
                index=None,
                cache=None,
            )
        assert result.results
        assert result.results[0]["score_components"].get("modality", 0.0) > 0.0
    finally:
        session.close()
