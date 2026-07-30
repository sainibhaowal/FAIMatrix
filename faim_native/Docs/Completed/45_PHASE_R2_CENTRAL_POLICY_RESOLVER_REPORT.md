# 45 - Phase R2 Central Policy Resolver Report

Date: 2026-02-20  
Owner: FAIM Native Runtime  
Status: Completed

## Objective

Implement one central resolver for `profile` + `persist_mode` so ingest/evolve behavior is resolved from a single backend source of truth, with a compatibility guard that preserves current workloads by default.

## Scope Delivered

1. Added central policy module:
- `faim_native/orchestration/profile_persist_policy.py`
2. Added compatibility flag parsing:
- `faim_native/runtime/config.py`
- `faim_native/runtime/feature_flags.py`
3. Wired resolver into runtime paths:
- `faim_native/orchestration/ingest_flow.py`
- `faim_native/orchestration/evolve_flow.py`
- `faim_native/orchestration/jobs/worker.py`
- `faim_native/orchestration/self_evolve_scheduler.py`
4. Added env/operator surfaces:
- `env.template`
- `docker-compose.yml`
- `deploy/env.production.example`
5. Added/updated tests:
- `tests/unit/test_phase_r2_profile_persist_policy.py`
- `tests/acceptance/test_AT_R2_profile_persist_policy_runtime.py`
- `tests/unit/test_orchestration_index.py`

## Central Resolver Contract

`resolve_profile_persist_policy(...)` now resolves:

1. `requested_profile`, `requested_persist_mode`
2. `effective_profile`, `effective_persist_mode`
3. `durability_path`
4. `index_enabled` (ingest operation)
5. `evolve_aggressiveness` (evolve operation)
6. `compatibility_mode`
7. coercion state/reason for invalid inputs

Supported operations:

1. `ingest`
2. `evolve`

## Compatibility / Safety

New flag:

1. `FAIM_PROFILE_PERSIST_COMPAT_MODE` (default `true`)

Behavior:

1. `true`: keeps legacy runtime behavior while using centralized policy resolution.
2. `false`: enables centralized policy semantics without legacy-compat assumptions.

Safety properties retained:

1. No schema migrations in R2.
2. No auth/tenant isolation changes.
3. No encryption or key handling changes.
4. Additive event payload fields only.

## Runtime Wiring Details

### Ingest

`INGEST_START` event now includes both requested/effective mode values and policy metadata.  
Index upsert decision now uses resolved policy (`policy.index_enabled`) rather than inline ad-hoc branching.

### Evolve

`EVOLUTION_START` event now includes requested/effective mode values, durability path, compatibility mode, and evolve aggressiveness.

### Worker / Scheduler

Worker evolve execution now passes both resolved `profile` and `persist_mode` to `run_evolve` (previously persist mode was dropped).  
Scheduler enqueue payload now records requested/effective fields and policy metadata for observability.

## Validation Executed

1. `python3 -m compileall faim_native/orchestration/profile_persist_policy.py faim_native/orchestration/ingest_flow.py faim_native/orchestration/evolve_flow.py faim_native/orchestration/jobs/worker.py faim_native/orchestration/self_evolve_scheduler.py faim_native/runtime/config.py faim_native/runtime/feature_flags.py`
2. `PYTHONPATH=.:faim_native pytest -q tests/unit/test_phase_r2_profile_persist_policy.py`
3. `PYTHONPATH=.:faim_native pytest -q tests/acceptance/test_AT_R2_profile_persist_policy_runtime.py`
4. `PYTHONPATH=.:faim_native pytest -q tests/unit/test_orchestration_index.py tests/unit/test_phase_s1_self_evolve_flags.py`
5. `PYTHONPATH=.:faim_native pytest -q tests/unit/test_phase_s3_self_evolve_scheduler.py tests/unit/test_phase_s4_worker_autonomous_scheduler.py tests/unit/test_phase_s5_evolution_core_hardening.py`
6. `PYTHONPATH=.:faim_native pytest -q tests/acceptance/test_AT_EV_B_evolve_status_surface.py tests/acceptance/test_AT_PF_storage_lifecycle_non_regression.py`

All commands above passed.

## Follow-up (R3+)

1. Expand differentiated algorithm branches per profile/persist combination beyond current centralized baseline.
2. Add API response-level requested/effective mode fields where contract rollout is desired for external clients.
