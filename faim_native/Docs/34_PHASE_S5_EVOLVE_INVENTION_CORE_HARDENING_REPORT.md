# 34 - Phase S5 Evolve/Invention Core Hardening Report

Date: 2026-02-17
Owner: FAIM Native Runtime
Status: Completed

## Scope

Phase S5 objective:

1. Remove direct env reads from evolve-core invention decision path.
2. Make prune policy practical under real `touch_count` behavior.
3. Emit explicit `EVOLUTION_SKIPPED` reasons for observability.
4. Preserve deterministic ordering and strict runtime invariants.

## Implemented Changes

### 1) Config/orchestration-driven invention gating

Updated:

- `faim_native/core/dynamics/evolution_native.py`
- `faim_native/orchestration/evolve_flow.py`
- `faim_native/orchestration/jobs/worker.py`

Changes:

- removed direct env-based invention gate in evolve core
- added runtime settings resolution from orchestration/config with safe fallback defaults
- added `self_invent_requested` pass-through from worker evolve job payload to orchestration/core
- wired `max_actions` from runtime settings into evolve execution path

### 2) Practical prune default

Updated:

- `faim_native/core/operators/prune.py`

Change:

- `PrunePolicy.max_touch_count` default changed from `0` to `1`
- aligns default prune eligibility with real node lifecycle behavior (`touch_count` starts at 1)

### 3) Explicit skip observability

Updated:

- `faim_native/core/dynamics/evolution_native.py`
- `faim_native/orchestration/evolve_flow.py`

Changes:

- `DIAGNOSTICS_SNAPSHOT` emission is preserved for every evolve cycle
- explicit `EVOLUTION_SKIPPED` event emitted with deterministic reason payload when no mutate action occurs
- supported reasons:
  - `insufficient_nodes`
  - `no_actions_after_evaluation`
- orchestration response event list now returns:
  - `EVOLUTION_COMPLETE` on mutate cycle
  - `EVOLUTION_SKIPPED` on non-mutate cycle

## Tests Added/Updated

Added:

- `tests/unit/test_phase_s5_evolution_core_hardening.py`

Coverage:

- skip reason/event for insufficient node count
- skip reason/event for no-action evolve cycle
- orchestration passes config + invention request through to core evolve
- regression guard that evolve module has no direct self-invent env reads

Updated:

- `tests/unit/test_prune_policy.py`

Coverage:

- default prune policy assertion aligned to `max_touch_count == 1`

## Validation Executed

1. Compile checks:

```bash
python3 -m compileall \
  faim_native/core/dynamics/evolution_native.py \
  faim_native/core/operators/prune.py \
  faim_native/orchestration/evolve_flow.py \
  faim_native/orchestration/jobs/worker.py \
  tests/unit/test_prune_policy.py \
  tests/unit/test_phase_s5_evolution_core_hardening.py
```

Result: success.

2. Targeted unit checks:

```bash
PYTHONPATH=.:faim_native pytest -q \
  tests/unit/test_prune_policy.py \
  tests/unit/test_phase_s5_evolution_core_hardening.py
```

Result: `11 passed`.

3. Targeted regression checks (S3/S4 + diagnostics + invention runtime):

```bash
PYTHONPATH=.:faim_native pytest -q \
  tests/acceptance/test_AT_PJ_self_invention_runtime.py \
  tests/acceptance/test_AT_C5_diagnostics_events.py \
  tests/acceptance/test_AT_O4_evolve_diagnostics.py \
  tests/unit/test_phase_s3_self_evolve_scheduler.py \
  tests/unit/test_phase_s4_worker_autonomous_scheduler.py
```

Result: `24 passed`.

## Files Changed

- `faim_native/core/dynamics/evolution_native.py`
- `faim_native/core/operators/prune.py`
- `faim_native/orchestration/evolve_flow.py`
- `faim_native/orchestration/jobs/worker.py`
- `tests/unit/test_prune_policy.py`
- `tests/unit/test_phase_s5_evolution_core_hardening.py`
- `faim_native/Docs/04_STORAGE_MEMORY_MATH_AND_EVOLUTION.md`
- `faim_native/Docs/07_STORAGE_GAP_ANALYSIS_AND_EXECUTION_BACKLOG.md`
- `docs/Plan.md`
- `faim_native/Docs/34_PHASE_S5_EVOLVE_INVENTION_CORE_HARDENING_REPORT.md`
