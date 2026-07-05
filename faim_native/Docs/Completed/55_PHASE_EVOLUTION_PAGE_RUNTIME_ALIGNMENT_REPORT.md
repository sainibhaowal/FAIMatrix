# 55 - Phase Evolution Page Runtime Alignment Report

Date: 2026-02-20

Status: Completed

## Scope

Fix minor but user-visible Evolution page/runtime alignment issues without changing core graph truth, security, or storage contracts.

## Verified Root Causes

1. Metrics cards (`Fractal D`, `Entropy H`, `Pressure λ`, `Metric Details`) were empty (`-`) because:
   - `DIAGNOSTICS_SNAPSHOT` emits flat payload fields (`D_hat`, `H_hat`, `lambda_hat`, `redundancy_R`, `novelty_N`, `energy_E`).
   - `/api/v1/metrics/scorecard` previously read nested `payload.metrics.*` keys only.

2. `Apply graph` was confusing for single-graph user sessions:
   - action changes graph context only; it does not run evolve.
   - for unchanged graph id it behaved like a no-op.

3. Timeline card appeared half-empty due to grid stretch behavior, not missing data.

4. Scheduler state `Active job` often showed `-` because no pending/running job existed (idle state), but copy lacked clarity.

## Implementation

### Backend

Updated:
- `faim_native/api/routers/metrics.py`

Changes:
1. Added compatibility extraction for both nested and flat diagnostics payload shapes.
2. Added graph hash fallback (`graph_hash` -> `diagnostics_hash` -> empty).
3. Kept endpoint additive/backward-compatible.

### Frontend

Updated:
- `frontend/src/app/(app)/dashboard/evolution/page.tsx`

Changes:
1. Added operator-only graph switching via `NEXT_PUBLIC_FAIM_ENABLE_GRAPH_SWITCH=true`.
2. Default behavior now surfaces session-bound graph context for user mode.
3. Added explicit toast when graph is already applied.
4. Prevented timeline panel stretch visual artifact (`items-start` / `self-start`).
5. Improved refresh behavior to avoid hard-empty timeline while loading.
6. Added human-readable scheduler due-reason text and clearer idle wording.
7. Added source coverage panel using storage APIs:
   - `/api/v1/storage/summary`
   - `/api/v1/storage/files`

### Docs

Updated:
- `faim_native/Docs/04_STORAGE_MEMORY_MATH_AND_EVOLUTION_REPORT.md`
- `faim_native/Docs/README.md`

Added:
- `faim_native/Docs/55_PHASE_EVOLUTION_PAGE_RUNTIME_ALIGNMENT_REPORT.md`

## Runtime Verification (Active Graph)

Graph: `U:621be0f1` (tenant `user:621be0f1-bee7-5feb-964a-a8e2a0243bd9`)

1. Storage ingestion evidence:
   - 4 PDFs present in `storage_files`
   - all `ingested`
   - node/vector counts match persisted nodes
2. Graph footprint:
   - 98 nodes / 856 edges
3. Metrics scorecard now resolves:
   - `dimension_D=0.802645`
   - `entropy_H=0.167669`
   - `pressure_lambda=0.076833`
   - `redundancy=0.85567`
   - `novelty=0.0`
   - `energy=1.186225`

## Test and Verification Gates

1. `python3 -m compileall faim_native tests` -> PASS
2. `PYTHONPATH=.:faim_native pytest -q tests/unit/test_phase_r5_api_response_clarity.py tests/unit/test_phase_r4_evolve_runtime_semantics.py tests/acceptance/test_AT_R4_profile_persist_evolve_runtime.py tests/acceptance/test_AT_R5_api_response_clarity.py` -> PASS (`17 passed`)
3. `cd frontend && npm run typecheck` -> PASS
4. `cd frontend && npm run lint -- --file 'src/app/(app)/dashboard/evolution/page.tsx' --file 'src/app/(app)/dashboard/storage/page.tsx'` -> PASS
5. `cd frontend && npm run test:e2e` -> PASS (`4 passed`)
6. `PYTHONPATH=.:faim_native pytest -q tests/unit tests/acceptance tests/security` -> PASS (`723 passed, 1 skipped`)

## Safety Notes

1. No destructive DB changes.
2. No auth/crypto/encryption behavior changes.
3. No tenant-isolation logic changes.
4. API behavior changed additively for metrics compatibility only.

## Outcome

Phase 55 is complete:

- the evolution page now matches runtime behavior more accurately,
- the metrics and status surfaces are aligned with live payload shapes,
- user-visible alignment issues were resolved without changing core graph truth.
