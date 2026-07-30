"""Phase K5 unit tests: memory write idempotency helpers and repo."""

from __future__ import annotations

from uuid import uuid4

from api.services.memory_service import build_write_request_hash, parse_idempotency_key
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from store.pg.models_faim import MemoryWriteRequestModel
from store.pg.repos.memory_write_idempotency_repo import MemoryWriteIdempotencyRepo


def _mk_session():
    engine = create_engine("sqlite:///:memory:")
    MemoryWriteRequestModel.__table__.create(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return Session()


def test_k5_request_hash_is_deterministic():
    payload = b"hello memory"

    first = build_write_request_hash(
        graph_id="g1",
        filename="memory.txt",
        content_type="text/plain",
        payload_bytes=payload,
        profile="strict",
        persist_mode="relaxed",
    )
    second = build_write_request_hash(
        graph_id="g1",
        filename="memory.txt",
        content_type="text/plain",
        payload_bytes=payload,
        profile="strict",
        persist_mode="relaxed",
    )
    changed = build_write_request_hash(
        graph_id="g1",
        filename="memory.txt",
        content_type="text/plain",
        payload_bytes=b"hello memory changed",
        profile="strict",
        persist_mode="relaxed",
    )

    assert first == second
    assert first != changed


def test_k5_parse_idempotency_key_priority_and_validation():
    assert parse_idempotency_key(header_value="abc", body_value=None) == "abc"
    assert parse_idempotency_key(header_value=None, body_value="abc") == "abc"
    assert parse_idempotency_key(header_value="abc", body_value="abc") == "abc"
    assert parse_idempotency_key(header_value=None, body_value=None) is None

    try:
        parse_idempotency_key(header_value="a", body_value="b")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "mismatch" in str(exc).lower()


def test_k5_idempotency_repo_begin_classification_and_replay():
    session = _mk_session()
    repo = MemoryWriteIdempotencyRepo(session, tenant_id="tenant_k5")

    begin = repo.begin(
        session,
        graph_id="graph_k5",
        idempotency_key="idem-1",
        request_hash="h1",
    )
    assert begin.state == "new"
    assert begin.record.status == "in_progress"
    session.commit()

    in_progress = repo.begin(
        session,
        graph_id="graph_k5",
        idempotency_key="idem-1",
        request_hash="h1",
    )
    assert in_progress.state == "in_progress"

    repo.mark_completed(
        session,
        record=begin.record,
        response_json={"status": "ok", "packet_hash": "p1"},
        packet_hash="p1",
        raw_id=uuid4(),
        node_count=3,
        vector_count=4,
    )
    session.commit()

    replay = repo.begin(
        session,
        graph_id="graph_k5",
        idempotency_key="idem-1",
        request_hash="h1",
    )
    assert replay.state == "replay"
    assert replay.record.response_json["status"] == "ok"

    conflict = repo.begin(
        session,
        graph_id="graph_k5",
        idempotency_key="idem-1",
        request_hash="different",
    )
    assert conflict.state == "conflict_payload"


def test_k5_idempotency_repo_marks_failed_state():
    session = _mk_session()
    repo = MemoryWriteIdempotencyRepo(session, tenant_id="tenant_k5")

    begin = repo.begin(
        session,
        graph_id="graph_k5",
        idempotency_key="idem-2",
        request_hash="h2",
    )
    assert begin.state == "new"

    repo.mark_failed(
        session,
        record=begin.record,
        error_message="intentional failure",
    )
    session.commit()

    failed = repo.begin(
        session,
        graph_id="graph_k5",
        idempotency_key="idem-2",
        request_hash="h2",
    )
    assert failed.state == "failed"
    assert "intentional" in str(failed.record.error_message)
