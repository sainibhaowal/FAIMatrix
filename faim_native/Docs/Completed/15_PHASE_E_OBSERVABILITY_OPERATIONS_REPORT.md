# 15 - Phase E Observability + Operations Report

Date: 2026-02-10

Status: Completed

Scope completed:

1. storage observability metrics endpoint
2. ingest phase latency capture and aggregation
3. failure taxonomy + dedup ratio tracking
4. backend health state reporting with probe latency
5. structured lifecycle logs with request/tenant/job/raw correlation
6. operations runbook and rollout controls

## 1) Modules Updated

- `faim_native/api/routers/storage.py`
- `faim_native/api/routers/ingest.py`
- `faim_native/orchestration/ingest_flow.py`
- `faim_native/orchestration/jobs/storage_retention.py`
- `faim_native/runtime/logging.py`
- `faim_native/runtime/feature_flags.py`
- `faim_native/runtime/config.py`

## 2) New API Surface

Added endpoint:

- `GET /api/v1/storage/ops/metrics`

Response includes:

- upload count/bytes for the selected window
- processed file count
- dedup hit count and dedup ratio
- failure reason taxonomy counts
- per-phase latency aggregate stats (`count`, `avg_ms`, `p95_ms`, `max_ms`)
- backend health states (`ok`, `status`, `latency_ms`, `error`)

## 3) Ingest Phase Latency Instrumentation

`run_ingest(...)` now records phase timings and emits durable event:

- event kind: `INGEST_PHASE_LATENCY`

Phase keys currently emitted:

- `extract`
- `packetize`
- `dedup_check`
- `validate`
- `encode`
- `write`
- `index` (when applicable)
- `dedup_record` (when applicable)

`IngestResult` now carries `phase_latency_ms` as additive output field.

## 4) Structured Lifecycle Logging

Storage/ingest/retention paths now emit correlated lifecycle logs with fields:

- `request_id`
- `tenant_id`
- `graph_id`
- `job_id`
- `raw_id`
- `op`
- `status`
- `failure_reason`
- `latency_ms`

`runtime/logging.JSONFormatter` was extended to include these fields when present.

## 5) Observability Feature Flags

Added rollout controls:

- `FAIM_STORAGE_OBSERVABILITY_ENABLED` (default: `true`)
- `FAIM_STORAGE_STRUCTURED_LIFECYCLE_LOGS` (default: `true`)

If observability endpoint is disabled, `/api/v1/storage/ops/metrics` returns `409` with explicit operator guidance.

## 6) Validation

Phase E targeted tests:

- `tests/unit/test_phase_e_observability.py`
- `tests/acceptance/test_AT_PE_storage_observability_surface.py`

Regression suite coverage rerun:

- Phase A/B/D storage tests
- storage API surface and auth/tenant isolation tests

## 7) Outcome

Phase E provides an operational observability baseline for storage: measurable upload throughput, latency and failure taxonomy, backend state health visibility, and correlated lifecycle logs suitable for incident triage and rollback decisions.
