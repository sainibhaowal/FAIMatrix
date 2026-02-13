# 26 - Phase K4 API Keys Management API + UI Report

Date: 2026-02-13

## Scope

Implement Phase K4 end-to-end:

1. backend API key management router under `/api/v1/api-keys/*`
2. router registration in app
3. frontend API Keys dashboard page (operational, not placeholder)
4. lifecycle actions: list/create/rotate/revoke + audit timeline

## Implemented

## Backend Router

Added:

- `faim_native/api/routers/api_keys.py`

Routes:

- `POST /api/v1/api-keys`
- `GET /api/v1/api-keys`
- `POST /api/v1/api-keys/{key_id}/rotate`
- `POST /api/v1/api-keys/{key_id}/revoke`
- `GET /api/v1/api-keys/audit`

Behavior:

- tenant-scoped operations only (via `FAIMContext.tenant_id`)
- one-time plaintext key reveal only on create/rotate responses
- no plaintext/hash exposure in list/audit payloads
- explicit key lifecycle conflict handling (`404`, `409`, `422`)
- scope validation against allowed scope set:
  - `keys.read`
  - `keys.write`
  - `memory.read`
  - `memory.write`
  - `memory.admin`

## Authz and Scope Enforcement

All K4 routes are guarded via K3 dependency:

- read routes require `keys.read`
- write routes require `keys.write`

Files:

- `faim_native/api/routers/api_keys.py`
- `faim_native/api/deps.py` (K3 dependency reused)

## Router Registration

Updated:

- `faim_native/api/routers/__init__.py`
- `faim_native/api/app.py`

`api_keys_router` is now included under `/api/v1`.

## Repository Support

Extended K2 repo with helper:

- `AuthRepo.get_tenant_key(tenant_id, key_id)`

File:

- `faim_native/store/pg/repos/auth_repo.py`

## Rate Limiting Alignment

Added dedicated API key category:

- `ENDPOINT_CATEGORIES["/api/v1/api-keys"] = "api_keys"`
- default `api_keys` limit bucket
- optional `api_keys_per_minute` config in `FAIM_RATE_LIMITS_JSON`

Files:

- `faim_native/api/middleware/ratelimit.py`
- `env.template`

## Frontend API Keys Page

Implemented real dashboard page:

- `frontend/src/app/(app)/dashboard/api-keys/page.tsx`

Capabilities delivered:

- list active/revoked/expired keys
- create key with scope selection + expiry preset
- one-time reveal panel for newly created key
- rotate key (old key revoked, new key revealed once)
- revoke key with confirmation and state guards
- audit timeline view with key filter
- refresh controls and action-level loading/error handling

## Tests

Added:

- `tests/acceptance/test_AT_PK4_api_keys_surface.py`
- `tests/unit/test_phase_k4_api_keys_router.py`

Updated:

- `tests/acceptance/test_AT_S9_rate_limiting.py`

## Validation

Executed:

- `python3 -m compileall faim_native tests`
- `PYTHONPATH=faim_native pytest -q tests/unit/test_phase_k4_api_keys_router.py tests/acceptance/test_AT_PK4_api_keys_surface.py tests/acceptance/test_AT_S9_rate_limiting.py tests/unit/test_phase_k3_auth_enforcement.py tests/acceptance/test_AT_PK3_authz_enforcement_surface.py`
- `npm run lint -- --file src/app/(app)/dashboard/api-keys/page.tsx` (from `frontend/`)

Result:

- compile passed
- pytest passed: `24 passed`
- frontend lint passed for touched page

## Notes

- K4 is additive and does not remove/rename existing routes.
- Scope enforcement depends on K3 flag rollout (`FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED`).
- Memory API contract routes (`/api/v1/memory/*`) remain Phase K5 scope.
