# 35 - Phase S6 End-to-End Validation Report

Date: 2026-02-17  
Owner: FAIM Native Runtime  
Status: Completed

## Scope

Phase S6 objective:

1. Unit validation for flags/validation, due-logic, prune behavior, invention gating/idempotence.
2. Acceptance validation for write -> auto evolve enqueue -> worker run -> invention/prune results -> events.
3. Regression validation for storage/memory/query/auth paths.

## What Was Executed

### 1) Compile gate

```bash
python3 -m compileall faim_native tests
```

Result: success.

### 2) Unit validation gate

```bash
PYTHONPATH=.:faim_native pytest -q \
  tests/unit/test_phase_s1_self_evolve_flags.py \
  tests/unit/test_phase_s2_self_evolution_state_repo.py \
  tests/unit/test_phase_s3_self_evolve_scheduler.py \
  tests/unit/test_phase_s4_worker_autonomous_scheduler.py \
  tests/unit/test_phase_s5_evolution_core_hardening.py \
  tests/unit/test_prune_policy.py \
  tests/unit/test_phase_j_self_invention_flags.py \
  tests/unit/test_phase_d_production_policy.py \
  tests/unit/test_phase_d_upload_abuse_guards.py \
  tests/unit/test_phase_k3_auth_enforcement.py \
  tests/unit/test_p2_encryption_at_rest.py
```

Result: `60 passed`.

### 3) Acceptance validation gate (self-evolve chain + diagnostics)

Added:

- `tests/acceptance/test_AT_S6_self_evolve_end_to_end.py`

Coverage:

- deterministic write chain produces graph state
- shared scheduler due-enqueue path produces evolve job
- worker executes job successfully
- evolve diagnostics/event evidence is persisted (`DIAGNOSTICS_SNAPSHOT`, `EVOLUTION_COMPLETE` or `EVOLUTION_SKIPPED`)
- evolve completion payload contains result fields for action cycles (`merges`, `prunes`, `inventions`)

Executed:

```bash
PYTHONPATH=.:faim_native pytest -q \
  tests/acceptance/test_AT_S6_self_evolve_end_to_end.py \
  tests/acceptance/test_AT_PJ_self_invention_runtime.py \
  tests/acceptance/test_AT_C5_diagnostics_events.py \
  tests/acceptance/test_AT_O4_evolve_diagnostics.py
```

Result: `13 passed`.

### 4) Regression gate (storage/memory/query/auth)

Executed:

```bash
PYTHONPATH=.:faim_native pytest -q \
  tests/acceptance/test_AT_P1_storage_api_surface.py \
  tests/acceptance/test_AT_PB_storage_phase_b_surface.py \
  tests/acceptance/test_AT_PD_storage_auth_tenant_isolation.py \
  tests/acceptance/test_AT_PE_storage_observability_surface.py \
  tests/acceptance/test_AT_PF_storage_lifecycle_non_regression.py \
  tests/acceptance/test_AT_PK3_authz_enforcement_surface.py \
  tests/acceptance/test_AT_PK4_api_keys_surface.py \
  tests/acceptance/test_AT_PK5_memory_api_surface.py \
  tests/acceptance/test_AT_PK5_memory_lifecycle.py \
  tests/acceptance/test_AT_Q1_query_determinism.py \
  tests/acceptance/test_AT_Q3_tenant_isolation.py \
  tests/acceptance/test_AT_Q7_query_flow.py
```

Result: `50 passed`.

### 5) Frontend targeted validation

Executed:

```bash
cd frontend
npm run typecheck
npm run lint
npx playwright test e2e/api-keys.spec.ts
```

Results:

- Typecheck: pass.
- Lint: fails in unrelated pre-existing dashboard/marketing files (not S6 scope).
- Playwright `e2e/api-keys.spec.ts`: pass (`2 passed`) after aligning test flow with current one-time reveal UX.

Note:

- Current Playwright config targets `frontend/e2e` only.
- `storage` e2e spec is not present in configured `testDir`.

## Test Stability Hardening Applied During S6

1. Dev/SQLite acceptance auth fixtures explicitly set compatibility mode:

- `FAIM_AUTH_DB_PRIMARY=false`
- `FAIM_AUTH_ENV_FALLBACK_ENABLED=true`

Updated files:

- `tests/acceptance/test_AT_PD_storage_auth_tenant_isolation.py`
- `tests/acceptance/test_AT_PE_storage_observability_surface.py`
- `tests/acceptance/test_AT_PF_storage_lifecycle_non_regression.py`
- `tests/acceptance/test_AT_PK5_memory_lifecycle.py`

2. SQLite lock flakiness removed for K5 lifecycle acceptance:

- isolated test DB per run using `tmp_path`
- explicit `client.close()` in `finally` block

Updated file:

- `tests/acceptance/test_AT_PK5_memory_lifecycle.py`

3. API keys Playwright spec aligned to current UI reveal behavior:

- click `Show key` before asserting plaintext visibility

Updated file:

- `frontend/e2e/api-keys.spec.ts`

## Files Added/Updated in S6

- `tests/acceptance/test_AT_S6_self_evolve_end_to_end.py` (new)
- `tests/acceptance/test_AT_PD_storage_auth_tenant_isolation.py`
- `tests/acceptance/test_AT_PE_storage_observability_surface.py`
- `tests/acceptance/test_AT_PF_storage_lifecycle_non_regression.py`
- `tests/acceptance/test_AT_PK5_memory_lifecycle.py`
- `frontend/e2e/api-keys.spec.ts`
- `faim_native/Docs/07_STORAGE_GAP_ANALYSIS_AND_EXECUTION_BACKLOG.md`
- `faim_native/Docs/README.md`
- `faim_native/Docs/35_PHASE_S6_END_TO_END_VALIDATION_REPORT.md`

## Outcome

Phase S6 objectives are met:

- unit validations passed,
- end-to-end self-evolve acceptance chain validated,
- storage/memory/query/auth regressions passed,
- targeted frontend checks completed with explicit scope notes.
