# 24 - Phase K2 Auth Model Upgrade Report

Status: Completed

## 1) Scope

Phase K2 implemented the migration-first auth data model upgrade defined in `23_API_KEYS_AUTHZ_AND_MEMORY_CONTRACT_PLAN.md`.

Goals delivered:

- extend `tenant_api_keys` with scope/expiry/lifecycle metadata
- add append-only key audit table
- update ORM + repository support while preserving backward compatibility

## 2) Implemented Changes

## Database Migration

- added migration:
  - `faim_native/store/pg/migrations/0008_auth_key_scopes_audit.sql`
- migration adds to `tenant_api_keys`:
  - `scopes` (JSONB)
  - `expires_at` (TIMESTAMPTZ)
  - `revoked_reason` (TEXT)
  - `created_by` (TEXT)
  - `last_used_at` (TIMESTAMPTZ)
  - `rotated_from_key_id` (TEXT)
- migration creates table:
  - `auth_key_audit_log`

## Schema Baseline

- updated `faim_native/store/pg/schema.sql` with:
  - full `tenant_api_keys` definition (K2 columns)
  - `auth_key_audit_log` definition
  - indexes and comments

## ORM Model Updates

- updated `faim_native/store/pg/models_auth.py`:
  - upgraded `TenantApiKey` model fields + `is_expired` / enhanced `is_active`
  - added `AuthKeyAuditLog` model
  - retained `UserModel` compatibility

## Repository Updates

- updated `faim_native/store/pg/repos/auth_repo.py`:
  - scope normalization support
  - tenant key create supports `scopes`, `expires_at`, `created_by`, lineage fields
  - verify path now rejects expired/revoked and updates `last_used_at`
  - revoke supports reason + audit metadata
  - rotate method added with lineage + audit records
  - audit append/list helpers added
- updated exports in:
  - `faim_native/store/pg/repos/__init__.py` (includes `AuthRepo`)

## Tests Added

- `tests/unit/test_phase_k2_auth_model_upgrade.py`
  - model columns and lifecycle checks
  - audit model existence checks
  - repo create + audit behavior checks
  - migration/schema marker checks

## 3) Backward Compatibility

- additive schema only (no route/path removals)
- existing key verification API remains callable
- no middleware enforcement changes introduced in K2
- no storage API contract break introduced
- any old admin-key storage references are historical only and are not part of the live product surface

## 4) Validation Summary

Executed:

- `python3 -m compileall faim_native`
- `PYTHONPATH=faim_native pytest -q tests/unit/test_phase_k2_auth_model_upgrade.py tests/security/test_api_key_hashing.py tests/unit/test_stage_7_1_hardening.py`

Result:

- compile check: passed
- targeted unit/security checks: `37 passed`

Additional legacy acceptance check executed:

- `PYTHONPATH=faim_native pytest -q tests/acceptance/test_AT_S10_migration_readiness.py`

Result:

- failed in sqlite path on pre-existing migration compatibility issue (`0003_stage11_auth_keys.sql`), not introduced by K2 changes.
- K2 migration file (`0008`) was not the failure point.
