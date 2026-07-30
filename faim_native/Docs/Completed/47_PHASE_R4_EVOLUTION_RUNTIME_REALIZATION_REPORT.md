# 47 - Phase R4 Evolution Runtime Realization Report

Date: 2026-02-20  
Owner: FAIM Native Runtime  
Status: Completed

## Objective

Implement real `profile` + `persist_mode` runtime semantics in evolution path (not metadata-only), while keeping strict deterministic safety and additive API compatibility.

## Scope Delivered

1. Applied central resolver output as real evolve runtime behavior.
2. Implemented profile-specific evolve behavior differences for:
- action budget,
- merge threshold,
- prune policy,
- invention gating/aggressiveness.
3. Implemented material evolve `persist_mode` completion semantics:
- `strict`: state-update durability is required in completion path,
- `relaxed`: core evolve commit first, state durability is best-effort non-fatal.
4. Added additive evolve API response metadata for requested/effective mode and completion semantics.
5. Added R4 unit + acceptance coverage.

## Implementation Details

### 1) Central resolver expansion

Updated `faim_native/orchestration/profile_persist_policy.py`:

Added evolve policy knobs to resolved contract:

1. `evolve_action_budget_scale`
2. `evolve_merge_threshold`
3. `evolve_prune_min_age_days`
4. `evolve_prune_max_touch_count`
5. `evolve_prune_similarity_threshold`
6. `evolve_invention_mode`
7. `evolve_invention_requested_default`
8. `evolve_invention_max_macros_cap`

Compatibility safety retained:

1. `FAIM_PROFILE_PERSIST_COMPAT_MODE=true` keeps prior runtime envelope.
2. `compat_mode=false` enables differentiated R4 evolve semantics.

### 2) Evolve runtime realization

Updated `faim_native/orchestration/evolve_flow.py`:

1. `EvolveResult` now includes additive mode/completion metadata:
- requested/effective profile + persist mode
- durability path
- evolve aggressiveness
- completion mode
- state update status/error

2. Resolver knobs are now applied to core evolve call:
- profile-scaled `max_actions`
- profile-specific `merge_threshold`
- profile-specific `PrunePolicy`
- invention defaults/overrides derived from policy

3. Implemented persist completion semantics:
- `strict`: required synchronous `self_evolution_state.mark_evolved` + commit.
- `relaxed`: commit core evolve first; run state update best-effort and non-fatal.

4. Added `EVOLUTION_PERSISTENCE_APPLIED` event with completion metadata.

### 3) Core evolve override support

Updated `faim_native/core/dynamics/evolution_native.py`:

1. `evolve_once(...)` now accepts `invention_overrides`.
2. Runtime-safe validation/clamping is applied for override values.
3. Core remains deterministic in ordering and action traversal.

### 4) Scheduler/worker metadata alignment

Updated:

1. `faim_native/orchestration/self_evolve_scheduler.py`
- enqueue payload now includes evolve policy metadata fields.
- periodic scheduler profile default now honors runtime `profile_default`.

2. `faim_native/orchestration/jobs/worker.py`
- evolve job progress events now carry requested/effective mode + completion metadata.

### 5) API surface alignment (additive)

Updated `faim_native/api/routers/evolve.py`:

1. Added optional request field:
- `self_invent_requested`

2. Added additive response fields:
- requested/effective profile/persist mode
- durability path
- evolve aggressiveness
- completion mode
- state update status/error

### 6) Runtime DB-session robustness (order-safe test/runtime behavior)

Updated `faim_native/runtime/context.py` and `faim_native/store/pg/session.py`:

1. DB URL resolution is now call-time safe for dynamic env changes.
2. Runtime context engine/session factory now reinitialize when `DATABASE_URL` changes.

This avoids stale DB/session reuse across runtime reload/test-order scenarios.

## Files Changed

1. `faim_native/orchestration/profile_persist_policy.py`
2. `faim_native/orchestration/evolve_flow.py`
3. `faim_native/core/dynamics/evolution_native.py`
4. `faim_native/orchestration/self_evolve_scheduler.py`
5. `faim_native/orchestration/jobs/worker.py`
6. `faim_native/api/routers/evolve.py`
7. `faim_native/runtime/context.py`
8. `faim_native/store/pg/session.py`
9. `tests/unit/test_phase_r4_evolve_runtime_semantics.py` (new)
10. `tests/acceptance/test_AT_R4_profile_persist_evolve_runtime.py` (new)
11. `tests/acceptance/test_AT_EV_B_evolve_status_surface.py` (stability hardening for DB/session reset)

## Validation Executed

1. Compile gate:
- `python3 -m compileall faim_native tests`

2. R4 targeted:
- `PYTHONPATH=.:faim_native pytest -q tests/unit/test_phase_r4_evolve_runtime_semantics.py tests/acceptance/test_AT_R4_profile_persist_evolve_runtime.py`

3. R2/S5/S6/EV status regressions:
- `PYTHONPATH=.:faim_native pytest -q tests/unit/test_phase_r2_profile_persist_policy.py tests/acceptance/test_AT_R2_profile_persist_policy_runtime.py tests/unit/test_phase_s5_evolution_core_hardening.py tests/acceptance/test_AT_EV_B_evolve_status_surface.py tests/acceptance/test_AT_S6_self_evolve_end_to_end.py tests/unit/test_phase_r4_evolve_runtime_semantics.py tests/acceptance/test_AT_R4_profile_persist_evolve_runtime.py`

Result:

1. All listed tests passed (`34 passed`).

## Security/Compatibility Notes

1. API changes are additive only.
2. No destructive schema/database migration in R4.
3. Tenant isolation/auth behavior unchanged.
4. Encryption/secret handling unchanged.
5. Compatibility guard retained via `FAIM_PROFILE_PERSIST_COMPAT_MODE`.

## Phase R4 Acceptance

Phase R4 is complete:

1. Evolve runtime now uses resolver output as real behavior.
2. Profile differences are materially implemented.
3. Persist-mode completion semantics are materially implemented.
4. Strict deterministic invariants remain intact.
5. API/observability surfaces expose requested/effective/completion semantics.
