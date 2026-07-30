# 22 - Phase J Self-Inventing Runtime Integration Report

Date: 2026-02-11

Status: Completed

## Scope

Wire self-inventing logic from `core/dynamics/invention_native.py` into live runtime safely and deterministically.

## Implemented

1. Runtime/config feature knobs (safe defaults)
- `FAIM_SELF_INVENT_ENABLED`
- `FAIM_SELF_INVENT_ON_EVOLVE`
- `FAIM_SELF_INVENT_AFTER_UPLOAD`
- `FAIM_SELF_INVENT_MAX_MACROS_PER_CYCLE`
- `FAIM_SELF_INVENT_EVENT_WINDOW`
- `FAIM_SELF_INVENT_MIN_COACTIVATION_COUNT`
- `FAIM_SELF_INVENT_LAMBDA_THRESHOLD`
- `FAIM_SELF_INVENT_MIN_REDUNDANCY_REDUCTION`

Files:
- `faim_native/runtime/feature_flags.py`
- `faim_native/runtime/config.py`

2. Durable invention runtime state
- Added `self_invention_state` persistence model/table for incremental event cursor + bounded coactivation counters.

Files:
- `faim_native/store/pg/models_faim.py`
- `faim_native/store/pg/schema.sql`
- `faim_native/store/pg/migrations/0007_self_invention_state.sql`
- `faim_native/store/pg/repos/self_invention_state_repo.py`
- `faim_native/store/pg/repos/__init__.py`

3. Invention operator contract alignment + runtime cycle
- Fixed event emission contract in invention path to use `EventRepo.emit(session, ...)`.
- Added bounded incremental invention cycle helper (`run_invention_cycle`).

File:
- `faim_native/core/dynamics/invention_native.py`

4. Live evolve wiring
- `evolve_once` now executes optional self-invent pass (flag-gated).
- Evolve result now tracks `inventions`.
- Evolve completion payload includes invention count.

Files:
- `faim_native/core/dynamics/evolution_native.py`
- `faim_native/orchestration/evolve_flow.py`
- `faim_native/api/routers/evolve.py`

5. Optional storage-triggered invention path
- Upload completion may enqueue follow-up `evolve` job when self-invent-after-upload is enabled.
- Queue dedupe prevents duplicate pending/running evolve jobs per tenant+graph.

File:
- `faim_native/api/routers/storage.py`

## Validation

Compile:
- `python3 -m compileall faim_native tests`

Targeted tests:
- `PYTHONPATH=.:faim_native pytest -q tests/unit/test_phase_j_self_invention_flags.py tests/acceptance/test_AT_PJ_self_invention_runtime.py tests/acceptance/test_AT_O4_evolve_diagnostics.py tests/acceptance/test_AT_C5_diagnostics_events.py`
- `PYTHONPATH=.:faim_native pytest -q tests/unit/test_phase_a_feature_flags.py tests/acceptance/test_AT_P1_storage_api_surface.py tests/acceptance/test_AT_PB_storage_phase_b_surface.py tests/acceptance/test_AT_PD_storage_auth_tenant_isolation.py`

Result:
- 28 tests passed.

## Notes

- Self-inventing is off by default and requires explicit enablement.
- Runtime path is additive and backward-compatible for existing storage/evolve API contracts.
