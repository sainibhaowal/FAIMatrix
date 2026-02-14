# 28 - Phase K6 Security Hardening + Audit + Rate Limits Report

## Date

2026-02-13

## Objective

Deliver production-grade hardening for API key auth and agent-facing memory/API
surfaces:

- complete key lifecycle security audit taxonomy
- reject revoked/expired keys with explicit policy paths
- enforce scope-denied behavior with audit events
- add endpoint-level rate-limit policy categories per tenant/identity
- ensure no plaintext key leakage in logs/audit metadata

## Implemented

## 1) Auth Audit Taxonomy Hardening

Updated auth request-time audit actions:

- `used`
- `denied(scope)`
- `denied(expired)`
- `denied(revoked)`

Implementation:

- `faim_native/api/middleware/auth.py`
- `faim_native/api/deps.py`
- `faim_native/store/pg/repos/auth_repo.py`

Notes:

- creation/rotation/revocation actions remain active from K2/K4 (`created`,
  `rotated`, `revoked`)
- K6 extends runtime request path coverage for usage and denials

## 2) Policy Check Strengthening

- DB verification path now distinguishes:
  - valid
  - revoked
  - expired
  - invalid credentials
- revoked/expired denials are not allowed to silently pass via env fallback in
  DB-primary mode.
- middleware returns explicit policy codes:
  - revoked -> `401`, `code=auth_key_revoked`
  - expired -> `401`, `code=auth_key_expired`
  - invalid -> `401`, `code=auth_invalid`

## 3) Scope Denial Audit (403)

- route scope guard (`require_scopes`) now emits key audit events when access is
  denied due to missing scopes.
- event includes bounded metadata:
  - missing scopes
  - route
  - method
  - request id (if present)

## 4) Endpoint-Level Rate Limit Policy

Rate limiting is now method+route aware with additive categories:

- `api_keys_read`, `api_keys_write`
- `memory_search`, `memory_read`, `memory_write`
- `storage_read`, `storage_write`
- `ingest_write`, `query_read`, `events_stream`

Compatibility:

- legacy `ENDPOINT_CATEGORIES` mapping remains for non-breaking behavior.

Implementation:

- `faim_native/api/middleware/ratelimit.py`
- `faim_native/runtime/config.py`

## 5) Production Guardrail Tightening

Production mode now requires:

- `FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED=true`

Implementation:

- `faim_native/runtime/config.py`
- `faim_native/runtime/feature_flags.py`

## 6) Plaintext Key Safety

- added audit metadata sanitizer to drop sensitive fields before persistence.
- added redaction-focused tests for logging pipeline to ensure API keys/Bearer
  tokens are not left in cleartext in log payloads.

## File Map

- `faim_native/store/pg/repos/auth_repo.py`
- `faim_native/api/middleware/auth.py`
- `faim_native/api/deps.py`
- `faim_native/api/middleware/ratelimit.py`
- `faim_native/runtime/config.py`
- `faim_native/runtime/feature_flags.py`
- `faim_native/Docs/23_API_KEYS_AUTHZ_AND_MEMORY_CONTRACT_PLAN.md`

Tests:

- `tests/unit/test_phase_k3_auth_enforcement.py`
- `tests/unit/test_phase_k2_auth_model_upgrade.py`
- `tests/unit/test_phase_f_backend_error_paths.py`
- `tests/unit/test_phase_a_feature_flags.py`
- `tests/unit/test_phase_d_production_policy.py`
- `tests/acceptance/test_AT_PK3_authz_enforcement_surface.py`

## Validation Evidence

Executed:

- `python3 -m compileall faim_native`
- `PYTHONPATH=faim_native pytest -q tests/unit/test_phase_k2_auth_model_upgrade.py tests/unit/test_phase_k3_auth_enforcement.py tests/unit/test_phase_f_backend_error_paths.py tests/acceptance/test_AT_PK3_authz_enforcement_surface.py`
- `PYTHONPATH=faim_native pytest -q tests/unit/test_phase_a_feature_flags.py tests/unit/test_phase_d_production_policy.py tests/acceptance/test_AT_PK4_api_keys_surface.py tests/acceptance/test_AT_PK5_memory_api_surface.py tests/acceptance/test_AT_S9_rate_limiting.py`
- `PYTHONPATH=faim_native pytest -q tests/acceptance/test_AT_PK5_memory_lifecycle.py tests/unit/test_phase_k5_memory_idempotency.py`

Results:

- K6-focused suite: 51 passed
- regression suite A: 20 passed
- regression suite B: 5 passed
- compile step passed

## Rollout Notes

- Keep `FAIM_AUTH_DB_PRIMARY=true`.
- Keep `FAIM_AUTH_ENV_FALLBACK_ENABLED=false` in production.
- Enable `FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED=true` before production rollout.
- Tune `FAIM_RATE_LIMITS_JSON` with new endpoint-level keys if custom quotas are
  required.
