# 29 - Phase K7 Validation and Non-Regression Report

## Date

2026-02-14

## Objective

Validate K2-K6 API key/authz/memory work end-to-end with production-mature
non-regression coverage:

- unit coverage for scope/expiry/revoke/rotation/middleware context
- API/acceptance coverage for tenant isolation and key lifecycle
- memory lifecycle validation including search path
- frontend API keys page behavior checks (actions + error states)
- compile/type/lint/e2e execution evidence

## Implemented in K7

## 1) Unit and Middleware Validation Hardening

Updated and extended:

- `tests/unit/test_phase_k3_auth_enforcement.py`
- `tests/unit/test_phase_k4_api_keys_router.py`

Coverage includes:

- scope-allowed and scope-denied paths
- middleware context propagation (`tenant_id`, `auth_method`, `auth_key_id`,
  `auth_scopes`)
- env fallback behavior controls for revoked denial path
- key rotation correctness assertions (lineage/scope/revoke behavior)
- method-aware rate-limit category assertions

## 2) API/Acceptance Lifecycle Validation

Updated and extended:

- `tests/acceptance/test_AT_PK3_authz_enforcement_surface.py`
- `tests/acceptance/test_AT_PK4_api_keys_surface.py`
- `tests/acceptance/test_AT_PK5_memory_lifecycle.py`

Coverage includes:

- tenant isolation for API key operations
- key lifecycle E2E (create -> rotate -> revoke -> denied)
- scope allowed/denied behavior matrix
- memory write idempotency replay + search path assertion

## 3) Runtime Query Stability Fix Discovered by K7

K7 validation surfaced a runtime issue in memory search path for SQLite-style
naive timestamps:

- error: `can't subtract offset-naive and offset-aware datetimes`

Fix applied:

- `faim_native/core/query/query_engine.py`
  - `recency_boost()` now normalizes naive/aware datetimes to UTC before age
    arithmetic.

Additional coverage:

- `tests/acceptance/test_AT_Q1_query_determinism.py`
  - added naive timestamp recency test.

## 4) Frontend Validation Surface

Implemented API keys page/frontend validation support:

- `frontend/e2e/api-keys.spec.ts`
  - create/rotate/revoke flow
  - create-failure error state
  - auth session mocks for protected dashboard route
- `frontend/playwright.config.ts`
  - `testDir` aligned to `frontend/e2e`
  - Chromium default for deterministic local runs
  - optional WebKit via `PLAYWRIGHT_INCLUDE_WEBKIT=true`
- `frontend/package.json`
  - added `typecheck` and `test:e2e` scripts
- `frontend/src/app/(app)/dashboard/api-keys/page.tsx`
  - aligned toast API usage to `useToast().toast.*` contract

## Validation Evidence

Executed:

- `python3 -m compileall faim_native`
- `PYTHONPATH=faim_native pytest -q tests/unit/test_phase_k2_auth_model_upgrade.py tests/unit/test_phase_k3_auth_enforcement.py tests/unit/test_phase_k4_api_keys_router.py tests/unit/test_phase_k5_memory_router_contract.py tests/unit/test_phase_f_backend_error_paths.py tests/acceptance/test_AT_PK3_authz_enforcement_surface.py tests/acceptance/test_AT_PK4_api_keys_surface.py tests/acceptance/test_AT_PK5_memory_lifecycle.py tests/acceptance/test_AT_Q1_query_determinism.py`
- `npm run typecheck` (from `frontend/`)
- `npx next lint --file "src/app/(app)/dashboard/api-keys/page.tsx" --file "e2e/api-keys.spec.ts"` (from `frontend/`)
- `npm run test:e2e` (from `frontend/`)

Results:

- backend targeted suite: 75 passed
- compile step: passed
- frontend typecheck: passed
- targeted frontend lint: passed
- frontend Playwright suite: 2 passed

## Notes

- Full-repo `next lint` still includes pre-existing unrelated violations in
  non-K7 pages. K7 validation used targeted lint on changed scope to avoid
  conflating unrelated legacy issues.
- K7 changes are additive and backward-compatible with existing K2-K6 contracts.
