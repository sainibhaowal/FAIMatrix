# 30 - Phase S1 Self-by-Default Guardrails Report

Date: 2026-02-17

## Scope

Implement Phase S1 only:

1. Define additive self-evolve runtime contract.
2. Add startup guardrails/validation for safe combinations.
3. Keep default behavior unchanged (no automatic evolve activation by default).

## Implemented

1. Runtime config contract fields added in `runtime/config.py`:
- `FAIM_SELF_EVOLVE_ENABLED`
- `FAIM_SELF_EVOLVE_TRIGGER_MODE`
- `FAIM_SELF_EVOLVE_MIN_INTERVAL_SECONDS`
- `FAIM_SELF_EVOLVE_MIN_VERSION_DELTA`
- `FAIM_SELF_EVOLVE_MAX_ACTIONS`

2. Feature flag surface expanded in `runtime/feature_flags.py` with same fields.

3. Guardrail validation added:
- Allowed trigger modes: `manual`, `post_upload`, `periodic`, `hybrid`
- If `FAIM_SELF_EVOLVE_ENABLED=true` with mode `post_upload|periodic|hybrid`, then `FAIM_ENABLE_JOBS=true` is required
- Bounds:
  - `FAIM_SELF_EVOLVE_MIN_INTERVAL_SECONDS >= 30`
  - `FAIM_SELF_EVOLVE_MIN_VERSION_DELTA >= 1`
  - `FAIM_SELF_EVOLVE_MAX_ACTIONS >= 1`

4. Environment template updated with S1 self-evolve variables and safe defaults.

5. Unit coverage added/extended:
- `tests/unit/test_phase_s1_self_evolve_flags.py` (new)
- `tests/unit/test_phase_a_feature_flags.py` (extended default checks)

## Non-Goals (kept unchanged in S1)

1. No autonomous scheduler implementation yet.
2. No write-path trigger wiring changes yet.
3. No storage/memory/evolve behavior switch by default.

## Files Updated

- `faim_native/runtime/config.py`
- `faim_native/runtime/feature_flags.py`
- `tests/unit/test_phase_s1_self_evolve_flags.py`
- `tests/unit/test_phase_a_feature_flags.py`
- `env.template`
- `faim_native/Docs/README.md`
- `faim_native/Docs/07_STORAGE_REMAINING_GAPS_AND_FUTURE_WORK_REPORT.md`
- `faim_native/Docs/30_PHASE_S1_SELF_BY_DEFAULT_GUARDRAILS_REPORT.md`

## Validation

Executed command set:

```bash
python3 -m compileall faim_native tests
PYTHONPATH=.:faim_native pytest -q \
  tests/unit/test_phase_s1_self_evolve_flags.py \
  tests/unit/test_phase_a_feature_flags.py \
  tests/unit/test_phase_j_self_invention_flags.py
```

Result:

- compile succeeded
- `16 passed` (targeted unit suites)
- no regressions observed in S1 scope

## Outcome

Phase S1 is complete as contract + guardrails groundwork, with backward-compatible defaults and no runtime behavior regression by design.
