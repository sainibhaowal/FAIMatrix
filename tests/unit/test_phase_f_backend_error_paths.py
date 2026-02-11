"""Phase F unit tests: backend error taxonomy and crypto/error guard paths."""

from __future__ import annotations

import pytest
from fastapi import HTTPException


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Upload file too large", "upload_oversize"),
        ("MIME type does not match file extension", "mime_extension_mismatch"),
        ("Filename cannot contain path separators", "path_traversal_filename"),
        ("raw_id must be a valid UUID", "raw_id_contract_error"),
        ("raw blob not available", "raw_unavailable"),
        ("extract parser failed", "extract_error"),
        ("vector encoder failed", "encode_error"),
        ("qdrant index unavailable", "index_error"),
        ("decrypt failed for tenant key", "encryption_error"),
        ("", "unknown"),
    ],
)
def test_storage_failure_reason_taxonomy_is_stable(message: str, expected: str):
    from api.routers.storage import _normalize_failure_reason

    assert _normalize_failure_reason(message) == expected


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Upload file too large", "upload_oversize"),
        ("MIME type does not match file extension", "mime_extension_mismatch"),
        ("path separators not allowed", "path_traversal_filename"),
        ("raw_id must be UUID", "raw_id_contract_error"),
        ("extract pipeline failed", "extract_error"),
        ("encrypt failed for payload", "encryption_error"),
        ("unexpected runtime fault", "ingest_error"),
        ("", "unknown"),
    ],
)
def test_ingest_failure_reason_taxonomy_is_stable(message: str, expected: str):
    from api.routers.ingest import _normalize_failure_reason

    assert _normalize_failure_reason(message) == expected


def test_storage_encryption_enabled_detects_cipher_mode(monkeypatch):
    from api.routers.storage import _storage_encryption_enabled

    monkeypatch.setenv("FAIM_PAYLOAD_CIPHER", "envelope")
    monkeypatch.delenv("FAIM_ENCRYPTION_AT_REST", raising=False)
    assert _storage_encryption_enabled() is True

    monkeypatch.setenv("FAIM_PAYLOAD_CIPHER", "plain")
    monkeypatch.setenv("FAIM_ENCRYPTION_AT_REST", "true")
    assert _storage_encryption_enabled() is True

    monkeypatch.setenv("FAIM_PAYLOAD_CIPHER", "plain")
    monkeypatch.setenv("FAIM_ENCRYPTION_AT_REST", "false")
    assert _storage_encryption_enabled() is False


def test_ingest_encryption_enabled_detects_cipher_mode(monkeypatch):
    from api.routers.ingest import _encryption_enabled

    monkeypatch.setenv("FAIM_PAYLOAD_CIPHER", "fernet")
    monkeypatch.delenv("FAIM_ENCRYPTION_AT_REST", raising=False)
    assert _encryption_enabled() is True

    monkeypatch.setenv("FAIM_PAYLOAD_CIPHER", "plain")
    monkeypatch.setenv("FAIM_ENCRYPTION_AT_REST", "true")
    assert _encryption_enabled() is True

    monkeypatch.setenv("FAIM_PAYLOAD_CIPHER", "plain")
    monkeypatch.setenv("FAIM_ENCRYPTION_AT_REST", "0")
    assert _encryption_enabled() is False


def test_storage_parse_uuid_rejects_invalid_contract():
    from api.routers.storage import _parse_uuid

    with pytest.raises(HTTPException) as exc:
        _parse_uuid("not-a-uuid", "raw_id")
    assert exc.value.status_code == 400
    assert "valid UUID" in str(exc.value.detail)


def test_ingest_parse_uuid_rejects_invalid_contract():
    from api.routers.ingest import _parse_uuid

    with pytest.raises(HTTPException) as exc:
        _parse_uuid("not-a-uuid")
    assert exc.value.status_code == 400
    assert "valid UUID" in str(exc.value.detail)


def test_job_store_append_event_assigns_monotonic_seq(session_factory):
    from orchestration.jobs.job_store import JobStore

    with session_factory.session() as session:
        job_id = JobStore.enqueue(
            session=session,
            tenant_id="tenant_phase_f_seq",
            graph_id="graph_phase_f_seq",
            kind="storage_upload",
            payload={"requested_files": 1},
        )
        JobStore.append_event(session, job_id, "step_start", {"message": "start"})
        JobStore.append_event(session, job_id, "step_progress", {"message": "progress"})

        events = JobStore.get_job_events(session, job_id)
        assert len(events) == 2
        assert int(events[0].seq) >= 1
        assert int(events[1].seq) == int(events[0].seq) + 1
