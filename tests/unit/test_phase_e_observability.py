"""Phase E unit tests: observability flags + structured logging correlation."""

from __future__ import annotations

import json
import logging


def test_feature_flags_parse_phase_e_observability_controls(monkeypatch):
    from runtime.feature_flags import get_feature_flags

    monkeypatch.setenv("FAIM_STORAGE_OBSERVABILITY_ENABLED", "false")
    monkeypatch.setenv("FAIM_STORAGE_STRUCTURED_LIFECYCLE_LOGS", "false")

    flags = get_feature_flags()
    assert flags.storage_observability_enabled is False
    assert flags.storage_structured_lifecycle_logs is False


def test_runtime_config_parses_phase_e_observability_controls(monkeypatch):
    from runtime.config import load_config, reset_config

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("TENANT_KEYS_JSON", '{"tenant_a": ["key_a"]}')
    monkeypatch.setenv("FAIM_STORAGE_OBSERVABILITY_ENABLED", "true")
    monkeypatch.setenv("FAIM_STORAGE_STRUCTURED_LIFECYCLE_LOGS", "false")

    reset_config()
    cfg = load_config()
    assert cfg.storage_observability_enabled is True
    assert cfg.storage_structured_lifecycle_logs is False


def test_json_formatter_includes_storage_correlation_fields():
    from runtime.logging import JSONFormatter

    formatter = JSONFormatter()

    record = logging.LogRecord(
        name="test.storage",
        level=logging.INFO,
        pathname=__file__,
        lineno=42,
        msg="storage lifecycle event",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-1"
    record.tenant_id = "tenant-1"
    record.graph_id = "graph-1"
    record.job_id = "job-1"
    record.raw_id = "raw-1"
    record.op = "upload_batch"
    record.status = "completed"
    record.failure_reason = "none"
    record.latency_ms = 21

    payload = json.loads(formatter.format(record))
    assert payload["request_id"] == "req-1"
    assert payload["tenant_id"] == "tenant-1"
    assert payload["graph_id"] == "graph-1"
    assert payload["job_id"] == "job-1"
    assert payload["raw_id"] == "raw-1"
    assert payload["op"] == "upload_batch"
    assert payload["status"] == "completed"
    assert payload["failure_reason"] == "none"
    assert payload["latency_ms"] == 21
