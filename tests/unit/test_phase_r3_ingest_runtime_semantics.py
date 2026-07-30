"""Phase R3 unit checks: ingest runtime semantics realization."""

from __future__ import annotations

import inspect


def test_r3_ingest_result_has_mode_and_durability_fields():
    from orchestration.ingest_flow import IngestResult

    result = IngestResult(
        status="completed",
        packet_hash="abc",
        graph_version=1,
        nodes_written=1,
        merges=0,
        block_count=1,
        vector_count=1,
        diagnostics_hash=None,
        events_emitted=["INGEST_START"],
        latency_ms=1,
    )

    payload = result.to_dict()
    assert payload["requested_profile"] == "strict"
    assert payload["requested_persist_mode"] == "relaxed"
    assert payload["effective_profile"] == "strict"
    assert payload["effective_persist_mode"] == "relaxed"
    assert payload["durability_path"] == "core_sync_secondary_async"
    assert payload["index_write_mode"] == "skipped"
    assert payload["secondary_task_status"] == "not_required"
    assert payload["secondary_task_job_id"] is None


def test_r3_ingest_flow_contains_async_secondary_index_path():
    import orchestration.ingest_flow as ingest_flow
    from orchestration.ingest_flow import run_ingest

    source = inspect.getsource(run_ingest)
    module_source = inspect.getsource(ingest_flow)
    assert "INDEX_UPSERT_QUEUED" in source
    assert "ingest_secondary_index" in module_source
    assert "sync_fallback_no_jobs" in source
    assert "profile_persist_compat_mode" in source
