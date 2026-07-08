from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_cortex_writeback_executor_is_idempotent(monkeypatch):
    from faim_native.core.cortex.writeback_executor import (
        execute_cortex_writeback_candidate,
    )
    from faim_native.store.pg.models_faim import (
        Base,
        CortexWritebackCandidateModel,
        MemoryWriteRequestModel,
    )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    candidate_row = CortexWritebackCandidateModel(
        turn_id="turn-1",
        session_id="session-1",
        tenant_id="tenant-1",
        graph_id="graph-1",
        kind="summary",
        status="auto_approved",
        reason="persist a durable summary",
        payload_json={"kind": "summary", "reason": "persist a durable summary"},
        confidence=0.95,
        created_at=datetime.now(timezone.utc),
    )
    session.add(candidate_row)
    session.commit()

    fake_result = SimpleNamespace(
        status="ok",
        packet_hash="packet-hash",
        graph_version=9,
        nodes_written=3,
        merges=1,
        block_count=2,
        vector_count=4,
        events_emitted=["event-1"],
        latency_ms=12,
        phase_latency_ms={"ingest": 5},
        error=None,
        requested_profile="strict",
        requested_persist_mode="strict",
        effective_profile="strict",
        effective_persist_mode="strict",
        durability_path="strict",
        index_write_mode="sync",
        secondary_task_status=None,
        secondary_task_job_id=None,
    )

    def fake_make_context(**kwargs):
        return SimpleNamespace(**kwargs)

    def fake_run_memory_write(**kwargs):
        return "raw-1", fake_result

    monkeypatch.setattr(
        "core.cortex.writeback_executor._make_context", fake_make_context
    )
    monkeypatch.setattr("api.routers.memory._run_memory_write", fake_run_memory_write)

    first = execute_cortex_writeback_candidate(
        session=session,
        tenant_id="tenant-1",
        graph_id="graph-1",
        turn_id="turn-1",
        candidate_row=candidate_row,
        candidate_payload={
            "kind": "summary",
            "reason": "persist a durable summary",
            "text": "persist a durable summary",
            "confidence": 0.95,
        },
        request_id="turn-1",
    )
    assert first.execution_status == "executed"
    assert first.replayed is False
    assert first.response_json["raw_id"] == "raw-1"
    first_key = first.execution_key
    first_request_hash = first.execution_request_hash

    second = execute_cortex_writeback_candidate(
        session=session,
        tenant_id="tenant-1",
        graph_id="graph-1",
        turn_id="turn-1",
        candidate_row=candidate_row,
        candidate_payload={
            "kind": "summary",
            "reason": "persist a durable summary",
            "text": "persist a durable summary",
            "confidence": 0.95,
        },
        request_id="turn-1",
    )
    assert second.execution_status == "replayed"
    assert second.replayed is True
    assert second.execution_key == first_key
    assert second.execution_request_hash == first_request_hash

    request_rows = session.query(MemoryWriteRequestModel).all()
    assert len(request_rows) == 1
    assert request_rows[0].status == "completed"
    assert candidate_row.execution_status == "replayed"
    assert candidate_row.execution_receipt_json["raw_id"] == "raw-1"

