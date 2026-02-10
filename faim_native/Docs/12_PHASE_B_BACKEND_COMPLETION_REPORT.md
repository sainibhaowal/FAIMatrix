# 12 - Phase B Backend Completion Report

Date: 2026-02-10

Scope completed:

1. provenance inspect API surface
2. upload job cancellation model + safe stop checkpoints
3. storage lifecycle audit event coverage
4. retention cleanup worker path (dry-run + irreversible guardrails)

## 1) Provenance Inspect API

Added:

- `GET /api/v1/storage/files/{raw_id}/provenance`

Implemented in:

- `faim_native/api/routers/storage.py`

Response now provides:

- storage file metadata
- raw ref metadata (`raw_id`, `sha256`, `uri`, `mime_type`, `size_bytes`)
- dedup linkage summary (`packet_hash`, dedup record info)
- linked node summaries by `raw_id`
- linked recent events containing raw provenance references

## 2) Upload Job Cancellation

Added:

- `POST /api/v1/storage/uploads/{job_id}/cancel`

Implemented in:

- `faim_native/orchestration/jobs/job_store.py`
- `faim_native/api/routers/storage.py`

Behavior:

- cancellation request stored in job payload (`cancel_requested`, reason, timestamps)
- claim path will not execute cancel-requested jobs
- storage upload loop checks cancellation at safe boundaries:
  - before next file starts
  - after raw persistence and before ingest execution
- cancelled files are marked with `ingest_status="cancelled"` where applicable

## 3) Storage Lifecycle Audit Events

Implemented events:

- `STORAGE_RAW_STORED`
- `STORAGE_DEDUP_HIT`
- `STORAGE_EXTRACT_FAILED`
- `STORAGE_ENCRYPT_FAILED`
- `STORAGE_DELETE_REQUESTED`
- `STORAGE_DELETE_EXECUTED`

Wired in:

- `faim_native/api/routers/storage.py`
- `faim_native/api/routers/ingest.py`
- `faim_native/orchestration/jobs/storage_retention.py`

## 4) Retention Worker Path

Added retention execution module:

- `faim_native/orchestration/jobs/storage_retention.py`

Added API routes:

- `POST /api/v1/storage/retention/execute` (inline execution)
- `POST /api/v1/storage/retention/jobs` (durable job enqueue)

Worker support:

- `faim_native/orchestration/jobs/worker.py` now handles `kind="storage_retention"`

Guardrails:

- dry-run is the default behavior
- physical deletion requires `irreversible=true`
- physical deletion requires `FAIM_STORAGE_HARD_DELETE_ENABLED=true`
- active reference protection: raw blobs are not physically deleted if still referenced by active storage rows

## 5) Storage/Raw Repo Hardening for Retention

Updated:

- `faim_native/store/pg/repos/storage_file_repo.py`
  - `mark_cancelled(...)`
  - `mark_delete_executed(...)`
  - `list_delete_requested(...)`
  - `count_active_references(...)`
- `faim_native/store/pg/repos/raw_repo.py`
  - `delete_by_id(...)`
- `faim_native/store/raw/raw_store.py`
  - `delete(...)`, `delete_by_sha(...)`
- `faim_native/store/raw/encrypted_payload_store.py`
  - passthrough delete methods

## 6) Tests Added

- `tests/unit/test_phase_b_job_cancellation.py`
- `tests/unit/test_phase_b_storage_retention.py`
- `tests/acceptance/test_AT_PB_storage_phase_b_surface.py`

Also revalidated:

- `tests/unit/test_storage_file_repo.py`
- `tests/unit/test_phase_a_storage_contract.py`
- `tests/acceptance/test_AT_P1_storage_api_surface.py`
- `tests/unit/test_phase_a_feature_flags.py`
- `tests/unit/test_p2_encryption_at_rest.py`

## 7) Validation Notes

- compile checks passed for all changed backend modules
- targeted Phase B/P1/P2/Phase A test suites passed
- one legacy acceptance suite (`test_AT_S10_job_durability.py`) still fails under SQLite migration path due pre-existing Stage-11 SQL dialect incompatibility in migration `0003`, not due Phase B changes
