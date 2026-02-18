# Phase H1: Production API Timeout + Lock Hotfix Report

Date: 2026-02-18

## Summary

This hotfix addressed production API hangs/timeouts and memory patch lock contention in the API-key path.

## Root Cause

1. Request-scoped FAIM DB sessions created by `get_faim_context` were not explicitly closed.
2. Query/memory search paths mutate usage state (`touch_count`, query events) but were not committing consistently.
3. Patch/write contention could block too long without bounded lock timeout behavior.
4. `store.pg.session.get_session()` created a new `SessionFactory`/engine path per call pattern in auth/readiness usage, which can degrade responsiveness under repeated authenticated traffic.

## Implemented Fixes

1. Request session lifecycle cleanup:
- `faim_native/api/deps.py`
- `get_faim_context` now yields and always rollbacks (best-effort) + closes session in `finally`.

2. Commit/rollback correctness for mutating query routes:
- `faim_native/api/routers/memory.py`
- `faim_native/api/routers/query.py`
- added explicit `session.commit()` on success and `rollback()` on failure for search/query flows.

3. Lock contention hardening for memory patch:
- `faim_native/api/routers/memory.py`
- added per-request lock timeout configuration:
  - PostgreSQL: `SET LOCAL lock_timeout = '3s'`
  - SQLite: `PRAGMA busy_timeout = 3000`
- added lock-conflict classification and 409 retryable response for patch lock conflicts.

4. Session factory/engine churn fix:
- `faim_native/store/pg/session.py`
- added cached `SessionFactory` reuse keyed by DB URL to avoid per-call factory churn.

5. Auth/readiness session alignment:
- `faim_native/api/middleware/auth.py`
- `faim_native/api/routers/health.py`
- switched to runtime session lifecycle helpers (`runtime.context` session + close).

6. Compose runtime stabilization:
- `docker-compose.yml`
- API command uses `uvicorn` process mode for stable runtime in current production profile.

## Verification

1. Live container health:
- `GET /ready` => `200`
- `GET /health` => `200`
- `docker compose ps` shows `api`, `worker`, `postgres`, `redis`, `qdrant`, `frontend` all up/healthy.

2. Live Postgres/API-key E2E:
- Created temporary tenant key in DB.
- Executed:
  - `POST /api/v1/memory/write`
  - `POST /api/v1/memory/search`
  - `GET /api/v1/memory/{node_id}`
  - `GET /api/v1/memory/{node_id}/provenance`
  - `PATCH /api/v1/memory/{node_id}`
- all returned `200` in one run after fixes.

3. Test suites:
- `tests/acceptance/test_AT_H1_memory_patch_after_search.py`
- `tests/acceptance/test_AT_PK5_memory_lifecycle.py`
- `tests/acceptance/test_AT_PK5_memory_api_surface.py`
- `tests/acceptance/test_AT_PK4_api_keys_surface.py`
- `tests/acceptance/test_AT_Q7_query_flow.py`
- `tests/acceptance/test_AT_Q6_events_emitted.py`
- `tests/acceptance/test_AT_Q1_query_determinism.py`
- `tests/security/test_api_key_hashing.py`
- `tests/security/test_jwt_middleware.py`
- Result: passing in this hotfix run.

## Notes

1. Existing unrelated local files/artifacts were intentionally not modified by this hotfix commit scope.
2. This report covers production timeout/lock stabilization only; broader feature behavior is unchanged.
