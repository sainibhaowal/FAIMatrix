# Phase H2: Evolution Page Internal Server Error Hotfix

Date: 2026-02-18

Status: Completed

## Incident

Evolution dashboard displayed:

- `Evolution page failed to load`
- `Internal Server Error`

Frontend logs also showed repeated proxy failures (`socket hang up`) to `api:8000`.

## Root Cause

Primary functional mismatch:

1. Evolution page requested events with `limit=120`.
2. Backend events route validated `limit <= 100` and returned `422`.
3. Evolution page initial load uses `Promise.all(...)`; this 422 failed the full snapshot load path and raised the error toast/page failure.

Operational amplifier:

4. API healthcheck timeout was set to `3s` on `/ready`; under bursty traffic this could mark the container unhealthy and increase frontend proxy instability symptoms.

## Fixes Applied

1. Backend compatibility hardening:
- `faim_native/api/routers/events.py`
- changed `limit` query validation from strict `le=MAX_PAGE_SIZE` to `ge=1` and clamps in code to `MAX_PAGE_SIZE`.
- Result: oversized client limits are handled safely (capped) instead of 422.

2. Frontend alignment:
- `frontend/src/app/(app)/dashboard/evolution/page.tsx`
- changed `INITIAL_EVENT_LIMIT` from `120` to `100`.

3. Compose probe hardening:
- `docker-compose.yml`
- increased API healthcheck timeout from `3s` to `8s` for readiness probe stability.

## Verification

1. Confirmed prior failure path from logs:
- `/api/v1/events?...&limit=120` produced `422`.

2. After fix:
- Evolution events endpoint accepts larger client value and returns capped response (no 422 for `limit=120`).
- Frontend now requests `limit=100` on initial snapshot.

3. API readiness/liveness:
- `/ready` responds `200` after restart.
- API container transitions to healthy with longer timeout window.

## Scope Safety

1. No schema/database migrations were changed.
2. No auth/crypto policy changes were introduced.
3. Change is additive/compatibility-focused and isolated to events read path + dashboard polling constant + probe timeout.

## Outcome

Phase H2 is complete:

- the event limit mismatch is fixed,
- the evolution page load path is stable,
- readiness timeout hardening is in place.
