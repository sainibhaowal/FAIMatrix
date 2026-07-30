# 14 - Phase D Security Hardening Report (Production Grade)

Date: 2026-02-10

Status: Completed

Scope completed:

1. production encryption policy enforcement
2. plaintext fallback removal in production profile
3. upload abuse protection hardening
4. storage-route authz/tenant-isolation test coverage

## 1) Production Encryption Policy Enforcement

Updated modules:

- `faim_native/runtime/config.py`
- `faim_native/runtime/feature_flags.py`

Production (`FAIM_ENV=production`) now requires:

- `FAIM_ENCRYPTION_AT_REST=true`
- `FAIM_ENCRYPTION_FAIL_CLOSED=true`

Invalid combinations now fail validation explicitly.

## 2) Remove Unsafe Plaintext Fallback in Production

Updated modules:

- `faim_native/runtime/context.py`
- `faim_native/api/routers/storage.py`
- `faim_native/api/routers/ingest.py`

Behavior:

- production raw-store initialization now fails if cipher mode is plain/noop
- production raw-store initialization fails closed on cipher/dek init errors
- API routers no longer silently fall back to local plaintext `RawStore` when production mode is active

## 3) Upload Abuse Protection Hardening

Updated modules:

- `faim_native/api/validators/input_limits.py`
- `faim_native/api/validators/__init__.py`
- `faim_native/api/routers/ingest.py`
- `faim_native/api/routers/storage.py`

Hardening added:

- strict path-like filename rejection (`/`, `\\`, basename mismatch)
- explicit MIME/extension compatibility checks via:
  - `validate_mime_extension_match(...)`
- existing oversize rejection path retained (`413`)
- ingestion/storage upload routes now enforce MIME/extension mismatch rejection consistently

## 4) Storage Route Authz + Tenant Isolation Coverage

Added acceptance coverage:

- `tests/acceptance/test_AT_PD_storage_auth_tenant_isolation.py`
  - every storage route requires tenant auth headers (401 without auth)
  - tenant B cannot access tenant A job/file/provenance resources
  - tenant-scoped list endpoint does not leak cross-tenant rows

## 5) Tests Added/Updated

Updated:

- `tests/unit/test_phase_a_feature_flags.py`

Added:

- `tests/unit/test_phase_d_production_policy.py`
- `tests/unit/test_phase_d_upload_abuse_guards.py`
- `tests/acceptance/test_AT_PD_storage_auth_tenant_isolation.py`

Validation:

- targeted Phase D + Phase A + storage contract suites passed
- targeted Phase B/P2 regression suites passed

## 6) Operational Outcome

Production profile now enforces encryption-at-rest fail-closed behavior, rejects plaintext fallback, and has explicit upload abuse and route-level auth/tenant isolation coverage for storage APIs.
