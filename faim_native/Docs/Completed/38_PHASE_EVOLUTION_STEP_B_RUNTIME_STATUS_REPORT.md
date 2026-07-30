# 38 - Phase EV-B Evolution Dashboard Step B Runtime Status Report

Date: 2026-02-18  
Owner: FAIM Native Runtime  
Status: Completed

## Scope

Step B objective:

1. Add a production-safe read-only evolve status contract.
2. Reuse shared due-decision logic between enqueue path and status path.
3. Integrate Evolution dashboard UI with new runtime/scheduler status surface.
4. Keep changes additive, tenant-scoped, and non-destructive.

## Implemented Changes

Backend:

- `faim_native/orchestration/self_evolve_scheduler.py`
  - added `SelfEvolveDueEvaluation`
  - added `evaluate_self_evolve_due(...)` as read-only due evaluator
  - refactored `enqueue_self_evolve_if_due(...)` to use the shared evaluator
  - preserved existing enqueue outcomes/reasons (`due_enqueued`, `active_evolve_job_exists`, skip reasons)
- `faim_native/api/routers/evolve.py`
  - added `GET /api/v1/evolve/status`
  - response includes:
    - runtime self flags and jobs enabled state
    - durable scheduler state summary
    - due status + reason + thresholds/delta
    - active evolve job and last enqueued evolve job summaries
    - last event summary (`last event`, `last snapshot hash`, `last skip reason`)
- `faim_native/api/middleware/ratelimit.py`
  - added explicit evolve route mapping:
    - `GET /api/v1/evolve/*` -> `query_read`
    - `POST /api/v1/evolve` -> `ingest_write`

Frontend:

- `frontend/src/app/(app)/dashboard/evolution/page.tsx`
  - integrated `/api/v1/evolve/status` into initial refresh and polling flow
  - added Step B scheduler/runtime state card with:
    - trigger mode, jobs enabled, self-evolve/self-invent flags
    - due-now badge + due reason
    - version delta and last evolved timestamp
    - active job and last enqueued job status
    - last skip reason visibility

## Test Coverage Added/Updated

- `tests/unit/test_phase_s3_self_evolve_scheduler.py`
  - validates read-only due evaluation (no scheduler-state mutation in status mode)
  - validates due evaluator active-job reason path
- `tests/acceptance/test_AT_EV_B_evolve_status_surface.py`
  - validates evolve status route surface
  - validates evolve status rate-limit classification
  - validates tenant isolation for status/job visibility

## Validation Executed

```bash
python3 -m compileall \
  faim_native/api/routers/evolve.py \
  faim_native/orchestration/self_evolve_scheduler.py \
  tests/unit/test_phase_s3_self_evolve_scheduler.py \
  tests/acceptance/test_AT_EV_B_evolve_status_surface.py

PYTHONPATH=.:faim_native pytest -q \
  tests/unit/test_phase_s3_self_evolve_scheduler.py \
  tests/acceptance/test_AT_EV_B_evolve_status_surface.py

PYTHONPATH=.:faim_native pytest -q \
  tests/acceptance/test_AT_O4_evolve_diagnostics.py \
  tests/unit/test_phase_s4_worker_autonomous_scheduler.py \
  tests/acceptance/test_AT_S6_self_evolve_end_to_end.py

cd frontend
npm run typecheck
npx next lint --file 'src/app/(app)/dashboard/evolution/page.tsx'
```

Results:

- compile: pass
- new/updated Step B backend tests: pass
- targeted self-evolve non-regression tests: pass
- frontend typecheck: pass
- evolution page lint: pass

## Outcome

Phase EV-B is complete:

- evolution runtime/scheduler observability now has a dedicated additive API contract,
- due evaluation logic is centralized to avoid drift between enqueue and status behavior,
- dashboard now exposes self-runtime health and scheduling state without write-side effects.
