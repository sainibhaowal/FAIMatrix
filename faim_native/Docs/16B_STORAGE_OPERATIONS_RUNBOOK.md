# 16B - Storage Operations Runbook

Date: 2026-02-10

This runbook covers storage observability and incident operations for production FAIM Native deployments.

## 1) Runtime Flags

Core security/storage flags:

- `FAIM_ENCRYPTION_AT_REST`
- `FAIM_ENCRYPTION_FAIL_CLOSED`
- `FAIM_STORAGE_HARD_DELETE_ENABLED`
- `FAIM_STORAGE_LIVE_JOB_STREAM_ENABLED`
- `FAIM_STORAGE_CONTRACT_STRICT`

Phase E observability flags:

- `FAIM_STORAGE_OBSERVABILITY_ENABLED`
- `FAIM_STORAGE_STRUCTURED_LIFECYCLE_LOGS`

Recommended production baseline:

- `FAIM_ENCRYPTION_AT_REST=true`
- `FAIM_ENCRYPTION_FAIL_CLOSED=true`
- `FAIM_STORAGE_OBSERVABILITY_ENABLED=true`
- `FAIM_STORAGE_STRUCTURED_LIFECYCLE_LOGS=true`
- `FAIM_STORAGE_HARD_DELETE_ENABLED=false` unless explicitly needed

## 2) Operational Endpoints

- `GET /api/v1/storage/summary`
- `GET /api/v1/storage/backends/health`
- `GET /api/v1/storage/ops/metrics`

Use `window_seconds` on `/ops/metrics` for triage windows (`3600`, `21600`, `86400`).

## 3) Rollout Procedure

1. Deploy with observability flags enabled in canary environment.
2. Verify `/storage/ops/metrics` contract and dashboard ingestion.
3. Confirm lifecycle logs include correlation fields.
4. Run controlled upload/retry/cancel/delete-request scenarios.
5. Promote to production after 24h healthy signal window.

## 4) Rollback Procedure

If operational noise or pressure is too high:

1. Set `FAIM_STORAGE_OBSERVABILITY_ENABLED=false` to disable metrics endpoint.
2. Set `FAIM_STORAGE_STRUCTURED_LIFECYCLE_LOGS=false` to reduce lifecycle logging volume.
3. Keep security flags (`FAIM_ENCRYPTION_*`) unchanged.
4. Validate storage APIs still return normal business responses.

## 5) Incident Playbooks

## Upload Failure Spike

1. Call `/api/v1/storage/ops/metrics?window_seconds=3600`.
2. Check `failure_reasons` top category.
3. Correlate by `request_id`/`job_id` in logs.
4. If abuse-related (`upload_oversize`, `mime_extension_mismatch`), verify validator policy and client behavior.

## Dedup Ratio Anomaly

1. Compare recent dedup ratio to baseline.
2. Check packet hash and raw_id provenance links.
3. Investigate client-side repeated sends or stale retry loops.

## Backend Degradation

1. Inspect `backend_states` in `/storage/ops/metrics`.
2. If `postgres` is degraded/down, pause batch uploads and prioritize DB recovery.
3. If `raw_store` is down in production, treat as ingestion-stop incident.

## Encryption Errors

1. Search logs for `failure_reason=encryption_error` and `STORAGE_ENCRYPT_FAILED` events.
2. Verify master key/DEK env and secret injection status.
3. Keep fail-closed behavior in production; do not enable plaintext fallback.

## 6) Key Rotation Behavior

Tenant DEK rotation support is available via `TenantDEKManager.rotate_tenant_dek(...)`.

Operational notes:

- Rotation rewraps the tenant DEK under the active master key and records the new master-key fingerprint.
- Existing already-encrypted payloads are not re-encrypted during rotation; payload ciphertext remains untouched by design.
- If the active master key changed, keep the previous master key ring available until the rotation job completes.
- After rotation, validate new writes and read-path success on sample tenants.
- If decryption failures appear, isolate tenant traffic and validate key material consistency.

## 7) Audit/Compliance Notes

Lifecycle events that should remain present:

- `STORAGE_RAW_STORED`
- `STORAGE_DEDUP_HIT`
- `STORAGE_EXTRACT_FAILED`
- `STORAGE_ENCRYPT_FAILED`
- `STORAGE_DELETE_REQUESTED`
- `STORAGE_DELETE_EXECUTED`

Retention execution must remain guarded by:

- `dry_run=true` by default
- `irreversible=true` for physical delete
- `FAIM_STORAGE_HARD_DELETE_ENABLED=true`
