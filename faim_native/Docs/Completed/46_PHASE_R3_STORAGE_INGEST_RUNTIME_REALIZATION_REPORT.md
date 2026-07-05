# 46 - Phase R3 Storage/Ingest Runtime Realization Report

Date: 2026-02-20  
Owner: FAIM Native Runtime  
Status: Completed

## Objective

Implement Phase R3 runtime behavior for `profile` + `persist_mode` in ingest/storage/memory paths so `persist_mode` materially changes execution behavior and observability.

## Scope Delivered

1. Applied centralized resolver output in ingest runtime.
2. Implemented material `persist_mode` behavior for secondary index work:
- `strict` (compat mode off): synchronous index durability path before response.
- `relaxed` (compat mode off): queue secondary index work asynchronously when jobs are enabled.
3. Preserved safe compatibility behavior behind `FAIM_PROFILE_PERSIST_COMPAT_MODE=true`.
4. Emitted effective mode and durability path metadata through events and API responses.
5. Added worker execution support for async secondary index jobs.

## Implementation Details

### 1) Ingest runtime durability realization

Updated `faim_native/orchestration/ingest_flow.py`:

1. Added result-contract metadata fields on `IngestResult`:
- `requested_profile`
- `requested_persist_mode`
- `effective_profile`
- `effective_persist_mode`
- `durability_path`
- `index_write_mode`
- `secondary_task_status`
- `secondary_task_job_id`

2. Added helper paths:
- `_jobs_enabled()`
- `_project_id_from_graph_or_default(...)`
- `_upsert_index_sync(...)`
- `_enqueue_async_index_upsert_job(...)`

3. Added mode-aware secondary behavior:
- compat mode `true`: legacy synchronous/non-fatal index behavior retained.
- compat mode `false` + `persist_mode=strict`: synchronous secondary upsert.
- compat mode `false` + `persist_mode=relaxed`:
  - if jobs enabled and session available: queue `ingest_secondary_index` durable job.
  - else: fallback to synchronous upsert with explicit fallback metadata.

4. Added/extended ingest events:
- `INDEX_UPSERTED`
- `INDEX_UPSERT_QUEUED`
- `INDEX_UPSERT_SKIPPED`

All include requested/effective mode + durability metadata.

### 2) Worker async secondary job execution

Updated `faim_native/orchestration/jobs/worker.py`:

1. Added new job kind handling in polling loop:
- `ingest_secondary_index`

2. Implemented `_run_ingest_secondary_index_job(...)`:
- loads queued node IDs
- upserts vectors into index via `FAIMIndex`
- emits worker/job progress
- emits journal event `INDEX_UPSERTED_ASYNC`

### 3) API response surface alignment (additive only)

Updated:
- `faim_native/api/routers/ingest.py`
- `faim_native/api/routers/storage.py`
- `faim_native/api/routers/memory.py`

Responses now expose requested/effective mode + durability metadata and secondary task status/job ID.

## Files Changed

1. `faim_native/orchestration/ingest_flow.py`
2. `faim_native/orchestration/jobs/worker.py`
3. `faim_native/api/routers/ingest.py`
4. `faim_native/api/routers/storage.py`
5. `faim_native/api/routers/memory.py`
6. `tests/unit/test_phase_r3_ingest_runtime_semantics.py` (new)
7. `tests/acceptance/test_AT_R3_profile_persist_ingest_runtime.py` (new)
8. `tests/unit/test_orchestration_index.py` (updated for refactor-safe assertions)

## Validation Executed

1. Compile checks:
- `python3 -m py_compile faim_native/orchestration/ingest_flow.py`
- `python3 -m py_compile faim_native/orchestration/jobs/worker.py`
- `python3 -m py_compile faim_native/api/routers/ingest.py`
- `python3 -m py_compile faim_native/api/routers/storage.py`
- `python3 -m py_compile faim_native/api/routers/memory.py`
- `python3 -m compileall faim_native tests`

2. R3 targeted + regression tests:
- `PYTHONPATH=.:faim_native pytest -q tests/unit/test_phase_r3_ingest_runtime_semantics.py tests/acceptance/test_AT_R3_profile_persist_ingest_runtime.py tests/unit/test_orchestration_index.py tests/acceptance/test_AT_R2_profile_persist_policy_runtime.py`
- `PYTHONPATH=.:faim_native pytest -q tests/acceptance/test_AT_P1_storage_api_surface.py tests/acceptance/test_AT_PF_storage_lifecycle_non_regression.py tests/acceptance/test_AT_PK5_memory_api_surface.py tests/acceptance/test_AT_PK5_memory_lifecycle.py tests/unit/test_phase_k5_memory_router_contract.py`

Results:
- All listed tests passed.

## Security and Compatibility Notes

1. No schema migrations required (additive runtime change).
2. Tenant isolation and auth paths unchanged.
3. Compatibility guard preserved:
- `FAIM_PROFILE_PERSIST_COMPAT_MODE=true` keeps prior runtime behavior.
4. No plaintext key/secret logging introduced.

## Phase R3 Acceptance

Phase R3 is complete for storage/ingest runtime realization:

1. `persist_mode` now materially affects ingest durability behavior.
2. Resolver-driven effective policy is applied at runtime.
3. Async secondary path is durable and worker-executed.
4. Requested/effective/durability metadata is visible in events and responses.
