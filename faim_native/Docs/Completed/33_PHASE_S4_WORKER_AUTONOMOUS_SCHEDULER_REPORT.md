# 33 - Phase S4 Worker Autonomous Scheduler Report

Date: 2026-02-17
Owner: FAIM Native Runtime
Status: Completed

## Scope

Phase S4 objective:

1. Extend worker runtime with periodic due-graph scans.
2. Auto-enqueue evolve jobs when due and no active pending/running evolve job exists.
3. Preserve centralized enqueue source-of-truth from S3.

## Implemented Changes

### 1) Runtime knobs (config + feature flags)

Added new environment/config knob:

- `FAIM_SELF_EVOLVE_SCAN_INTERVAL_SECONDS` (default: `60`, minimum: `30`)

Updated:

- `faim_native/runtime/config.py`
- `faim_native/runtime/feature_flags.py`

Validation:

- startup guardrails now reject values below 30 seconds

### 2) Central scheduler enhancements

Updated:

- `faim_native/orchestration/self_evolve_scheduler.py`

Additions:

- source-aware trigger mode routing:
  - write-trigger sources (`storage_upload`, `ingest_json`, `ingest_upload`, `memory_write`) require `post_upload|hybrid`
  - periodic worker sources (`periodic_worker`) require `periodic|hybrid`
- `list_self_evolve_tenants(...)` to discover active tenants from graph-version state
- `scan_and_enqueue_due_self_evolve_jobs(...)`:
  - tenant-scoped due-graph scan via durable S2 state
  - capped by `FAIM_SELF_EVOLVE_MAX_ACTIONS`
  - uses centralized `enqueue_self_evolve_if_due(...)` for dedupe and enqueue

### 3) Worker autonomous periodic scheduling

Updated:

- `faim_native/orchestration/jobs/worker.py`

Additions:

- periodic autonomous scan tick in worker loop
- throttle by `self_evolve_scan_interval_seconds`
- tenant iteration + per-tenant scan invocation
- robust error isolation (scan failures do not crash worker loop)

## Tests Added/Updated

Added:

- `tests/unit/test_phase_s4_worker_autonomous_scheduler.py`

Coverage:

- periodic scan enqueues due graph
- periodic scan skips when trigger mode is not periodic/hybrid
- scan respects `FAIM_SELF_EVOLVE_MAX_ACTIONS`
- worker scan interval throttle behavior
- worker invokes per-tenant scheduler scan

Updated:

- `tests/unit/test_phase_s1_self_evolve_flags.py`

Coverage:

- parse/config for `FAIM_SELF_EVOLVE_SCAN_INTERVAL_SECONDS`
- bounds validation (`>= 30`)

## Validation Executed

1. Compile:

```bash
python3 -m compileall \
  faim_native/orchestration/self_evolve_scheduler.py \
  faim_native/orchestration/jobs/worker.py \
  faim_native/runtime/feature_flags.py \
  faim_native/runtime/config.py \
  tests/unit/test_phase_s4_worker_autonomous_scheduler.py \
  tests/unit/test_phase_s1_self_evolve_flags.py
```

2. S-series unit validation:

```bash
PYTHONPATH=.:faim_native pytest -q \
  tests/unit/test_phase_s4_worker_autonomous_scheduler.py \
  tests/unit/test_phase_s3_self_evolve_scheduler.py \
  tests/unit/test_phase_s2_self_evolution_state_repo.py \
  tests/unit/test_phase_s1_self_evolve_flags.py
```

Result: `27 passed`.

3. Route-surface regression checks:

```bash
PYTHONPATH=.:faim_native pytest -q \
  tests/acceptance/test_AT_P1_storage_api_surface.py \
  tests/unit/test_phase_k5_memory_router_contract.py
```

Result: all passed.

## Files Changed

- `faim_native/runtime/config.py`
- `faim_native/runtime/feature_flags.py`
- `faim_native/orchestration/self_evolve_scheduler.py`
- `faim_native/orchestration/jobs/worker.py`
- `tests/unit/test_phase_s1_self_evolve_flags.py`
- `tests/unit/test_phase_s4_worker_autonomous_scheduler.py`
- `faim_native/Docs/07_STORAGE_REMAINING_GAPS_AND_FUTURE_WORK_REPORT.md`
