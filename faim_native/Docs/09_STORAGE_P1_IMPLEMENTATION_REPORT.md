# 09 - Storage P1 Implementation Report

Date: 2026-02-10
Owner: FAIM Native Runtime
Status: Completed
Scope: `07_STORAGE_REMAINING_GAPS_AND_FUTURE_WORK_REPORT.md` P1 only

## Summary

P1 full storage feature delivery is implemented.

Delivered outcomes:

- shared runtime raw store wiring for immutable raw persistence
- storage catalog persistence model (`storage_files`) with repository
- dedicated storage backend API surface (`/api/v1/storage/*`)
- production-style Storage UI page with multi-file lifecycle operations
- ingest endpoints now update storage catalog metadata as part of ingest flow

## Files Changed

## Backend

- `faim_native/runtime/context.py`
- `faim_native/api/deps.py`
- `faim_native/api/routers/storage.py` (new)
- `faim_native/api/routers/ingest.py`
- `faim_native/api/routers/health.py`
- `faim_native/api/routers/__init__.py`
- `faim_native/api/app.py`
- `faim_native/api/validators/input_limits.py`
- `faim_native/store/pg/models_faim.py`
- `faim_native/store/pg/repos/storage_file_repo.py` (new)
- `faim_native/store/pg/repos/__init__.py`
- `faim_native/store/__init__.py`
- `faim_native/store/pg/migrations/0005_storage_files.sql` (new)
- `faim_native/store/pg/schema.sql`

## Frontend

- `frontend/src/app/(app)/dashboard/storage/page.tsx`

## Tests

- `tests/acceptance/test_AT_P1_storage_api_surface.py` (new)
- `tests/unit/test_storage_file_repo.py` (new)

## Documentation

- `faim_native/Docs/README.md`
- `faim_native/Docs/01_STORAGE_IMPLEMENTATION_AUDIT_AND_STATUS_REPORT.md`
- `faim_native/Docs/07_STORAGE_REMAINING_GAPS_AND_FUTURE_WORK_REPORT.md`

## Technical Details

## A) Raw Truth Wiring

Implemented runtime-level raw store wiring in `runtime/context.py`:

- new shared raw store instance via `raw_store` in repository context
- environment path support via `FAIM_RAW_STORE_PATH`
- `FAIMContext` now carries `raw_store` and `storage_file_repo`

Effect:

- APIs use a common raw persistence path instead of per-route ad hoc instantiation.

## B) Storage Persistence Model

Added `storage_files` model/table for UI and API lifecycle state:

- table stores `raw_id`, filename, mime, size, sha, ingest status, packet hash, counts, error, timestamps, delete-request flags
- migration file `0005_storage_files.sql` added
- repository `StorageFileRepo` added with methods for:
  - upsert upload metadata
  - ingest start/result transitions
  - list/filter/paginate
  - summary aggregation
  - logical delete-request marking

## C) Storage API Surface

Implemented `api/routers/storage.py` with routes:

- `POST /api/v1/storage/uploads`
- `GET /api/v1/storage/uploads/{job_id}`
- `GET /api/v1/storage/uploads/{job_id}/events`
- `GET /api/v1/storage/files`
- `GET /api/v1/storage/files/{raw_id}`
- `DELETE /api/v1/storage/files/{raw_id}`
- `POST /api/v1/storage/files/{raw_id}/ingest`
- `POST /api/v1/storage/files/{raw_id}/retry`
- `GET /api/v1/storage/summary`
- `GET /api/v1/storage/backends/health`

Security/contract controls kept:

- tenant-scoped context on all endpoints
- upload validators enforced (size/type/extension/filename)
- UUID validation for `raw_id` and `job_id`
- delete action is logical request only (non-destructive)

## D) Ingest Integration with Storage Catalog

`api/routers/ingest.py` now updates storage catalog lifecycle rows:

- when raw upload persists, catalog row is upserted and marked ingesting
- when ingest finishes, catalog status is updated to ingested/dedup_hit/failed

This keeps legacy ingest endpoints and new storage UI in sync.

## E) Frontend Storage UI

Replaced placeholder page with operational UI at `frontend/src/app/(app)/dashboard/storage/page.tsx`:

- multi-file selection and upload
- profile/persist-mode controls
- batch result panel with progress
- searchable/filterable catalog table
- actions per file:
  - re-ingest
  - retry failed
  - delete request
- summary cards and backend health indicators

API integration uses existing frontend rewrite path (`/api/v1/*`) and NextAuth bearer token headers.

## Validation

## Compile

- `python3 -m compileall` on changed backend modules: passed.

## Backend tests

- P1 new tests:
  - `tests/acceptance/test_AT_P1_storage_api_surface.py`
  - `tests/unit/test_storage_file_repo.py`
- P0 regression tests rerun and passing:
  - `tests/acceptance/test_AT_A3_ingest_emits_events.py`
  - `tests/acceptance/test_AT_A6_node_inspector_no_leak.py`
  - `tests/acceptance/test_AT_A4_sse_resume_after_seq.py`
  - `tests/acceptance/test_AT_S9_ingest_idempotency.py`
  - `tests/acceptance/test_AT_R1_raw_truth.py`
  - `tests/unit/test_stage_7_1_hardening.py`
  - `tests/unit/test_snapshot_repo.py`

## Frontend lint

- `npx eslint src/app/(app)/dashboard/storage/page.tsx --max-warnings=0`: passed.
- Full frontend lint currently fails due unrelated pre-existing issues in other pages.

## Residual Risks / Next Scope

Remaining P2 items:

- encryption-at-rest activation in live ingest path (`EncryptedRawStore`/envelope integration)
- deeper query cache and qdrant contract hardening
- operational retention pipeline beyond delete-request state
