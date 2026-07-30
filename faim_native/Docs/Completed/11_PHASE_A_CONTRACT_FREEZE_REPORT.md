# 11 - Phase A Contract Freeze and Safety Guardrails Report

Date: 2026-02-10

Status: Completed

Scope completed:

1. storage API contract freeze
2. compatibility validation checks
3. rollout feature-flag guardrails

## 1) Storage Contract Freeze

Added contract definition module:

- `faim_native/api/contracts/storage_contract.py`

What it enforces:

- required `/api/v1/storage/*` method + path matrix
- required response fields for storage response models
- explicit contract version marker: `2026-02-10.phaseA`

Startup integration:

- `faim_native/api/app.py` validates storage contract on startup.
- behavior controlled by `FAIM_STORAGE_CONTRACT_STRICT` (default: `true`).

## 2) Rollout Feature Flags and Guardrails

Added feature-flag runtime module:

- `faim_native/runtime/feature_flags.py`

Flags defined:

- `FAIM_ENCRYPTION_FAIL_CLOSED`
- `FAIM_STORAGE_HARD_DELETE_ENABLED`
- `FAIM_STORAGE_LIVE_JOB_STREAM_ENABLED`
- `FAIM_STORAGE_CONTRACT_STRICT`

Guardrail validation rules:

- hard delete requires `FAIM_ENABLE_JOBS=true`
- production + encryption-at-rest requires fail-closed
- live stream mode emits rollout warning for explicit verification

Startup integration:

- `faim_native/api/app.py` validates feature flags at startup and fails fast on errors.

## 3) Runtime Config Alignment

Updated:

- `faim_native/runtime/config.py`

Changes:

- parses Phase A flags into `FAIMConfig`
- validates unsafe combinations using the same guardrail logic class of checks

## 4) Tests Added

- `tests/unit/test_phase_a_storage_contract.py`
  - route/method matrix freeze checks
  - required response fields checks
- `tests/unit/test_phase_a_feature_flags.py`
  - defaults and parsing
  - invalid flag combo guardrails
  - runtime config integration checks

## 5) Operational Notes

- Phase A is additive and non-destructive.
- No storage endpoint paths changed.
- No response fields were removed or renamed.
- Existing clients remain compatible under default flag configuration.
