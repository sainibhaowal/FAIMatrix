# 17B - Phase F Validation and Non-Regression Report

Date: 2026-02-11

Scope completed:

1. backend unit validation for new error and crypto guard paths
2. API/acceptance validation for full storage lifecycle controls
3. frontend validation for queue lifecycle and provenance interactions
4. compile/lint/regression gate execution with evidence

## 1) Modules Updated

- backend:
  - `faim_native/orchestration/jobs/job_store.py`
- frontend:
  - `frontend/src/app/(app)/dashboard/storage/page.tsx`
  - `frontend/src/middleware.ts`
  - `frontend/playwright.config.ts`
- tests:
  - `tests/unit/test_phase_f_backend_error_paths.py`
  - `tests/acceptance/test_AT_PF_storage_lifecycle_non_regression.py`
  - `frontend/tests/e2e/storage-phase-f.spec.ts`

## 2) Validation Coverage Added

### Backend Unit Coverage

`tests/unit/test_phase_f_backend_error_paths.py` validates:

- storage failure taxonomy mapping stability
- ingest failure taxonomy mapping stability
- encryption mode detection guard logic (`storage` and `ingest`)
- UUID contract parse rejection behavior
- monotonic `job_events.seq` assignment behavior in local/SQLite path

### API/Acceptance Coverage

`tests/acceptance/test_AT_PF_storage_lifecycle_non_regression.py` validates:

- upload batch endpoint, status endpoint, events endpoint
- storage catalog list/detail
- provenance inspect endpoint
- delete request endpoint and retention dry-run execution endpoint
- retry endpoint idempotency guard semantics
- cancellation request endpoint state visibility

### Frontend Coverage

`frontend/tests/e2e/storage-phase-f.spec.ts` validates:

- queue transitions for failed -> retry -> ingested
- queue transitions for in-flight -> cancel -> cancelled
- provenance inspect panel data rendering

## 3) Defects Found and Fixed During Phase F

### A) SQLite Job Event Sequence Portability

Issue:

- `job_events.seq` inserts failed in SQLite with `NOT NULL` on `JobStore.append_event(...)`.

Fix:

- `faim_native/orchestration/jobs/job_store.py`
  - assign `seq` explicitly for SQLite using `max(seq)+1` fallback logic.

Result:

- upload/cancel acceptance flows execute correctly in local test runtime.

### B) Storage UI Retry Polling Race

Issue:

- retry action could be overwritten by stale polling tied to previous `job_id`, causing status regression back to failed.

Fix:

- `frontend/src/app/(app)/dashboard/storage/page.tsx`
  - clear `jobId` when retry starts and when retry result is applied.
  - add stable `data-testid` hooks for queue/provenance test targeting.

Result:

- retry transition is stable in e2e flow and no stale-job overwrite occurs.

### C) Playwright Auth Access to Protected Dashboard Routes

Issue:

- middleware auth redirect blocked storage e2e entry path.

Fix:

- `frontend/src/middleware.ts`
  - add test-only bypass path controlled by `PLAYWRIGHT_BYPASS_AUTH=true`.
- `frontend/playwright.config.ts`
  - run web server with `PLAYWRIGHT_BYPASS_AUTH=true`
  - isolate test server on `http://localhost:8011`

Result:

- storage e2e runs reliably without changing production auth defaults.

## 4) Validation Commands and Results

Backend compile:

- `python3 -m compileall -q ...` (touched storage/orchestration/runtime modules)
- result: passed

Backend targeted Phase F:

- `PYTHONPATH=faim_native pytest -q tests/unit/test_phase_f_backend_error_paths.py tests/acceptance/test_AT_PF_storage_lifecycle_non_regression.py`
- result: `26 passed`

Backend regression pack (A/B/D/E/F + P2 + storage acceptance):

- `PYTHONPATH=faim_native pytest -q tests/unit/test_phase_a_storage_contract.py tests/unit/test_phase_a_feature_flags.py tests/unit/test_phase_b_job_cancellation.py tests/unit/test_phase_b_storage_retention.py tests/unit/test_phase_d_production_policy.py tests/unit/test_phase_d_upload_abuse_guards.py tests/unit/test_phase_e_observability.py tests/unit/test_phase_f_backend_error_paths.py tests/unit/test_p2_encryption_at_rest.py tests/acceptance/test_AT_P1_storage_api_surface.py tests/acceptance/test_AT_PB_storage_phase_b_surface.py tests/acceptance/test_AT_PD_storage_auth_tenant_isolation.py tests/acceptance/test_AT_PE_storage_observability_surface.py tests/acceptance/test_AT_PF_storage_lifecycle_non_regression.py`
- result: `62 passed`

Frontend lint:

- `cd frontend && npm run -s lint -- --file src/app/(app)/dashboard/storage/page.tsx --file src/middleware.ts`
- result: passed

Frontend e2e:

- `cd frontend && CI=1 npx playwright test tests/e2e/storage-phase-f.spec.ts --project=chromium --workers=1`
- result: `2 passed`

## 5) Outcome

Phase F establishes production-grade validation and non-regression evidence for storage Phase A-E behavior, with new automated coverage across backend logic, API lifecycle controls, and frontend queue/provenance interactions.
