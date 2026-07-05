# 53 Full Repo Endpoint Validation Report

Date: 2026-02-20

Status: Completed (historical baseline; superseded by 54)

## Scope Executed

This validation run aimed to be exhaustive at repo level by executing:

1. Full backend test suite (`pytest -q`) across unit + acceptance + security tests.
2. Frontend typecheck + full lint + Playwright e2e.
3. Live runtime health checks on deployed Docker stack.
4. Endpoint inventory extraction from live OpenAPI and heuristic test-coverage gap scan.

## Environment

- Docker services: `api`, `worker`, `frontend`, `postgres`, `redis`, `qdrant` all healthy.
- API base: `http://localhost:8000`
- Frontend base: `http://localhost:8010`

## Automated Results

### Backend compile gate

- Command: `python3 -m compileall faim_native tests`
- Result: PASS

### Full backend pytest gate

- Command: `PYTHONPATH=.:faim_native pytest -q`
- Result: **714 passed, 6 failed, 1 skipped**

Failed tests:
1. `tests/acceptance/test_AT_PI_storage_supported_types_surface.py::test_supported_types_endpoint_returns_expected_contract`
2. `tests/acceptance/test_AT_S10_job_durability.py::TestJobDurability::test_job_claim_order_deterministic`
3. `tests/acceptance/test_AT_S10_job_durability.py::TestJobDurability::test_job_durability_resume_after_stale`
4. `tests/acceptance/test_AT_S10_job_durability.py::TestJobDurability::test_job_single_writer_lock_evolve`
5. `tests/acceptance/test_AT_S10_migration_readiness.py::TestMigrationIdempotent::test_migration_apply_idempotent`
6. `tests/acceptance/test_AT_S10_migration_readiness.py::TestMigrationIdempotent::test_ready_fails_if_migrations_missing`

### Frontend gates

1. `npm run typecheck` -> PASS
2. `npm run lint` -> FAIL (pre-existing lint errors in non-storage/evolution pages)
3. `npm run test:e2e` -> PASS (4/4)

## Endpoint Inventory and Coverage Gap Scan

Source: live OpenAPI (`/openapi.json`)

- Total routes discovered: **48**
- Covered by direct test-string heuristic: **33**
- Uncovered by heuristic: **15**

Heuristic-uncovered endpoints:
1. `DELETE /api/v1/auth/me`
2. `GET /api/v1/auth/me`
3. `GET /api/v1/events/latest`
4. `GET /api/v1/events/stream`
5. `POST /api/v1/ingest/upload`
6. `GET /api/v1/metrics/scorecard`
7. `GET /api/v1/node/{node_id}/explain`
8. `GET /api/v1/storage/backends/health`
9. `POST /api/v1/storage/files/{raw_id}/ingest`
10. `POST /api/v1/storage/retention/jobs`
11. `GET /api/v1/storage/summary`

Note: the old `/api/v1/admin/*` routes were removed from the live app and are no longer part of the runtime API inventory.

Note: heuristic gap means no direct literal path hit found in tests; some may still be covered indirectly.

## Real-World Runtime Observations

- Health endpoints (`/health`, `/ready`, `/version`) are OK in live runtime.
- Recent `api` + `worker` logs show no active blocker errors in latest validation window.
- Storage/evolution/profile-persist critical runtime paths were verified in prior hotfix smoke and are operational.

## Root-Cause Notes for Current Failures

### 1) Supported-types acceptance test (401)

- `test_AT_PI_storage_supported_types_surface` expects 200 but gets 401.
- This is auth-path test fixture/runtime mismatch (tenant-key setup or auth mode expectations), not a crash.

### 2) S10 job durability tests

- These tests rely on broad `claim_next` behavior assumptions.
- Worker/runtime now intentionally uses filtered executable job kinds.
- Test expectations need alignment with executable-kind claim policy.

### 3) S10 migration readiness tests on SQLite

- Failure occurs while applying migration SQL that includes Postgres-specific DDL (`UUID`, `gen_random_uuid()`, `TIMESTAMPTZ`, etc.).
- Current migration polyfill is insufficient for this stage on SQLite.
- Production Postgres path remains valid; this is a portability gap in test harness/migrate script.

## Production Readiness Verdict

Status: **Historical pre-fix baseline. Superseded by 54 once the remaining blockers were fixed.**

Why not fully green:
1. Full backend suite still has 6 failing acceptance tests.
2. Full frontend lint gate still fails on unrelated pages.
3. Endpoint heuristic shows 15 routes without direct explicit test references.

## Required to Declare Full Exhaustive Green

1. Fix and re-green the 6 failing acceptance tests.
2. Fix frontend lint errors and re-green full `npm run lint`.
3. Add explicit acceptance coverage for the heuristic-uncovered endpoints (or formally de-scope/deprecate some endpoints).
4. Re-run complete gate and record all-green evidence.

## Outcome

This report is complete as a historical validation baseline:

- it captured the original repo-wide blockers,
- it identified the precise remaining gap classes,
- its findings were resolved and superseded by `54_FULL_REPO_PRODUCTION_READINESS_REVALIDATION_REPORT.md`.
