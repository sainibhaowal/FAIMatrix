# 25 - Phase K3 Auth Middleware + Authz Enforcement Report

Date: 2026-02-13

Status: Completed

## Scope

Implement Phase K3 safely and additively:

1. move tenant API key auth decision to DB-backed verification as primary
2. keep env-key fallback only behind explicit compatibility flag
3. add scope enforcement dependency (`require_scopes`)
4. propagate auth context in request state (`auth_method`, `auth_key_id`, `auth_scopes`)
5. align rate-limit classification with `/api/v1/*` and apply tenant + identity aware buckets

## Implemented

## Runtime Flags and Production Guards

Added K3 flags:

- `FAIM_AUTH_DB_PRIMARY` (default: `true`)
- `FAIM_AUTH_ENV_FALLBACK_ENABLED` (default: `false`)
- `FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED` (default: `false`)

Production policy enforcement:

- production requires `FAIM_AUTH_DB_PRIMARY=true`
- production requires `FAIM_AUTH_ENV_FALLBACK_ENABLED=false`

Files:

- `faim_native/runtime/feature_flags.py`
- `faim_native/runtime/config.py`
- `env.template`

## Auth Middleware

`faim_native/api/middleware/auth.py` now provides:

- `AuthDecision` envelope for auth result metadata
- `authenticate_tenant_key(tenant_id, api_key)` with DB-primary ordering
- explicit optional env-key fallback path (flag-gated)
- middleware request context propagation:
  - `request.state.tenant_id`
  - `request.state.auth_method`
  - `request.state.auth_key_id`
  - `request.state.auth_scopes`

Backward compatibility:

- `validate_tenant_key(...)` retained as bool wrapper

## Scope Enforcement Dependency

Added `require_scopes(required_scopes)` in `faim_native/api/deps.py`.

Behavior:

- checks active only when `FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED=true`
- JWT compatibility path remains allowed for current session auth model
- missing required scopes returns `403`

## Rate Limiting Alignment

Updated `faim_native/api/middleware/ratelimit.py`:

- added `/api/v1/*` category mapping:
  - `/api/v1/storage`
  - `/api/v1/ingest`
  - `/api/v1/query`
  - `/api/v1/events`
  - `/api/v1/memory/*`
- kept legacy `/v1/*` paths for compatibility
- bucket keys now include tenant + identity + category
- identity path supports:
  - JWT (`jwt:<user_id>`)
  - API key (`key:<key_id>`)
  - tenant fallback (`tenant:<tenant_id>`)

## Tests

Added:

- `tests/unit/test_phase_k3_auth_enforcement.py`
- `tests/acceptance/test_AT_PK3_authz_enforcement_surface.py`

Updated:

- `tests/acceptance/test_AT_S9_rate_limiting.py`

## Validation

Executed:

- `python3 -m compileall faim_native tests`
- `PYTHONPATH=faim_native pytest -q tests/unit/test_phase_k3_auth_enforcement.py tests/acceptance/test_AT_PK3_authz_enforcement_surface.py tests/acceptance/test_AT_S9_rate_limiting.py`
- `PYTHONPATH=faim_native pytest -q tests/security/test_api_key_hashing.py tests/unit/test_stage_7_1_hardening.py`
- `PYTHONPATH=faim_native pytest -q tests/unit/test_phase_k2_auth_model_upgrade.py`

Result:

- compile passed
- tests passed: `54 passed` (K3 + security/stage regression + K2 model checks)

## Notes

- K3 changes are additive and do not remove/rename existing routes.
- Scope enforcement remains disabled by default to allow controlled rollout.
- Env-key fallback is explicit compatibility behavior and blocked in production mode.
