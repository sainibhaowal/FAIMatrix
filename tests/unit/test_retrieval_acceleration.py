"""Tests for opt-in chunking and the semantic ANN acceleration path."""

from __future__ import annotations

import sys
import types
from uuid import UUID


def test_chunking_preserves_source_offsets_and_skips_structured_blocks():
    from core.contracts.types import BlockAnchor, EvidenceBlock
    from perception.chunking import chunk_evidence_blocks

    text = "one two three four five six seven eight nine ten " * 20
    source = EvidenceBlock.create(
        raw_id="raw-1",
        anchor=BlockAnchor(doc_type="text", char_start=100, char_end=100 + len(text)),
        content=text,
    )
    table = EvidenceBlock.create(
        raw_id="raw-1",
        anchor=BlockAnchor(doc_type="text"),
        content=text,
        block_type="table",
    )

    chunks = chunk_evidence_blocks([source, table], max_chars=256, overlap=32)

    assert len(chunks) > 2
    assert all(chunk.metadata and chunk.metadata["chunked"] for chunk in chunks[:-1])
    assert chunks[-1].block_type == "table"
    assert chunks[0].anchor.char_start == 100
    assert chunks[0].anchor.char_end is not None
    assert chunks[0].anchor.char_end > chunks[0].anchor.char_start


def test_semantic_qdrant_uses_one_batch_upsert(monkeypatch):
    import index.semantic_qdrant_index as semantic

    class Model:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    qdrant_models = types.ModuleType("qdrant_client.models")
    qdrant_models.Distance = Model
    qdrant_models.VectorParams = Model
    qdrant_models.PointStruct = Model
    qdrant_package = types.ModuleType("qdrant_client")
    qdrant_package.models = qdrant_models
    monkeypatch.setitem(sys.modules, "qdrant_client", qdrant_package)
    monkeypatch.setitem(sys.modules, "qdrant_client.models", qdrant_models)

    class FakeCollections:
        collections = []

    class FakeClient:
        def __init__(self):
            self.upserts = []

        def get_collections(self):
            return FakeCollections()

        def create_collection(self, **kwargs):
            return None

        def upsert(self, **kwargs):
            self.upserts.append(kwargs)

    fake = FakeClient()
    monkeypatch.setattr(semantic, "_client", lambda: fake)

    index = semantic.SemanticQdrantIndex(
        UUID("12345678-1234-5678-1234-567812345678"), 3
    )
    count = index.upsert_batch(
        "graph-1",
        [
            ("00000000-0000-0000-0000-000000000001", [1.0, 0.0, 0.0]),
            ("00000000-0000-0000-0000-000000000002", [0.0, 1.0, 0.0]),
        ],
    )

    assert count == 2
    assert len(fake.upserts) == 1
    assert len(fake.upserts[0]["points"]) == 2


def test_retry_or_fail_requeues_only_transient_failures(session_factory, monkeypatch):
    from orchestration.jobs.job_store import JobStore

    class OperationalError(Exception):
        pass

    monkeypatch.setenv("FAIM_JOB_MAX_RETRIES", "1")
    with session_factory.session() as session:
        job_id = JobStore.enqueue(
            session,
            tenant_id="tenant-retry",
            graph_id="graph-retry",
            kind="storage_upload",
            payload={},
        )
        assert JobStore.retry_or_fail(
            session, job_id, OperationalError("invalid transaction")
        )
        job = JobStore.get_job(session, job_id)
        assert job is not None
        assert job.status == "pending"
        assert job.payload_json["worker_retry_count"] == 1
        assert not JobStore.retry_or_fail(
            session, job_id, OperationalError("invalid transaction")
        )
        assert not JobStore.retry_or_fail(session, job_id, ValueError("bad document"))


def test_benchmark_worker_isolated_from_autonomous_jobs(monkeypatch):
    import orchestration.jobs.worker as worker_module

    monkeypatch.setenv("FAIM_BENCHMARK_MODE", "true")
    worker = worker_module.Worker(
        poll_interval=1.0, self_evolve_scan_interval_seconds=3600.0
    )

    assert "storage_upload" in worker.executable_job_kinds
    assert "ingest_secondary_index" in worker.executable_job_kinds
    assert "evolve" not in worker.executable_job_kinds
    assert "domain_autonomy" not in worker.executable_job_kinds


def test_large_graph_phase5_can_skip_sql_dense_materialization(monkeypatch):
    import orchestration.perf.index_rebuild as rebuild

    class FakeRepo:
        def __init__(self, **kwargs):
            pass

        def load_representation_rows(self, graph_id):
            return []

        def load_vector_points(self, graph_id):
            raise AssertionError("large-graph Phase 5 must use persistent ANN")

    monkeypatch.setattr(rebuild, "IndexRepo", FakeRepo)
    artifacts = rebuild.build_graph_index_artifacts(
        session=object(),
        tenant_id="tenant",
        graph_id="graph",
        include_dense=False,
    )

    assert artifacts.ann_root is None
