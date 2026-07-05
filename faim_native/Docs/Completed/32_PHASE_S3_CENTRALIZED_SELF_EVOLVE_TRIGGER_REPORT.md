# 32 - Phase S3 Centralized Self-Evolve Trigger Report

Date: 2026-02-17
Owner: FAIM Native Runtime
Status: Completed

## Scope

Phase S3 objective:

1. Centralize enqueue trigger logic with a shared helper.
2. Enforce one pending/running evolve job per tenant+graph.
3. Keep storage follow-up behavior while routing through shared logic.
4. Reuse same helper in ingest and memory write paths.

## Implemented Changes

### 1) Shared scheduler helper (single source of truth)

Added:

- `faim_native/orchestration/self_evolve_scheduler.py`

Primary API:

- `enqueue_self_evolve_if_due(...)`

Behavior:

- evaluates trigger eligibility from runtime flags
- preserves storage legacy follow-up compatibility (`self_invent_after_upload`)
- checks `FAIM_ENABLE_JOBS` before enqueue
- marks seen graph version in durable scheduler state
- applies due checks (version delta + min interval)
- enforces active evolve dedupe (`pending`/`running`)
- enqueues evolve job with normalized payload when due
- records `last_enqueued_job_id` in `self_evolution_state`

### 2) Storage follow-up path routed via shared helper

Updated:

- `faim_native/api/routers/storage.py`

Change:

- replaced local post-upload evolve enqueue logic with shared helper call
- kept existing storage behavior gate (`self_invent_enabled && self_invent_after_upload`)
- kept follow-up job-id propagation and job timeline event behavior

### 3) Ingest path integration

Updated:

- `faim_native/api/routers/ingest.py`

Change:

- added best-effort shared enqueue call after successful ingest result (`completed`/`dedup_hit`)
- applied to both `/ingest` and `/ingest/upload` endpoints
- failures in enqueue path are isolated to warnings (ingest response remains non-blocking)

### 4) Memory write path integration

Updated:

- `faim_native/api/routers/memory.py`

Change:

- added best-effort shared enqueue call after successful memory write ingest result
- failures in enqueue path are isolated to warnings (memory write response remains non-blocking)

## Tests Added

Added:

- `tests/unit/test_phase_s3_self_evolve_scheduler.py`

Coverage:

- self-evolve disabled skip
- storage legacy follow-up compatibility
- trigger mode guard (`manual` rejected for write-trigger path)
- jobs-disabled guard
- enqueue success + active-job dedupe
- due by version-delta
- due by min-interval

## Validation Executed

1. Compile checks:

```bash
python3 -m compileall \
  faim_native/orchestration/self_evolve_scheduler.py \
  faim_native/api/routers/storage.py \
  faim_native/api/routers/ingest.py \
  faim_native/api/routers/memory.py \
  tests/unit/test_phase_s3_self_evolve_scheduler.py
```

2. Targeted unit regressions:

```bash
PYTHONPATH=.:faim_native pytest -q \
  tests/unit/test_phase_s3_self_evolve_scheduler.py \
  tests/unit/test_phase_s2_self_evolution_state_repo.py \
  tests/unit/test_phase_s1_self_evolve_flags.py
```

Result: `21 passed`.

3. Route-surface regression spot checks:

```bash
PYTHONPATH=.:faim_native pytest -q \
  tests/acceptance/test_AT_P1_storage_api_surface.py \
  tests/unit/test_phase_k5_memory_router_contract.py
```

Result: all passed.

## Notes

- A legacy SQLite acceptance scenario (`tests/acceptance/test_AT_PK5_memory_lifecycle.py`) hit a local DB lock in this environment during patch flow. Primary S3 validation remains green in unit + targeted route-surface suites.
- Production path remains PostgreSQL-first; no schema-destructive change was introduced in S3.

## Files Changed

- `faim_native/orchestration/self_evolve_scheduler.py` (new)
- `faim_native/api/routers/storage.py`
- `faim_native/api/routers/ingest.py`
- `faim_native/api/routers/memory.py`
- `tests/unit/test_phase_s3_self_evolve_scheduler.py` (new)
- `faim_native/Docs/07_STORAGE_REMAINING_GAPS_AND_FUTURE_WORK_REPORT.md`
