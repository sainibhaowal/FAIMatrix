# 01 - Storage Current State Audit

## Scope Reviewed

Audit covered the requested FAIM Native areas and linked frontend storage UI:

- `frontend/src/app/(app)/dashboard/storage/page.tsx`
- `faim_native/api/*`
- `faim_native/orchestration/*`
- `faim_native/perception/*`
- `faim_native/encoding/*`
- `faim_native/core/*`
- `faim_native/cache/*`
- `faim_native/index/*`
- `faim_native/runtime/*`
- `faim_native/store/*`

Also reviewed migrations, docker/env wiring, and selected acceptance/security tests.

## Executive Summary

Current state is **implemented end-to-end for storage baseline (P0/P1/P2)**:

- Core ingest, vectorization, graph write, and evolution math are active.
- Storage page supports operational multi-file upload and lifecycle actions.
- Raw immutable blob persistence is wired in ingest and storage API paths.
- Router/repository contract mismatches from the original audit were repaired.
- Security/performance hardening from P2 is integrated with env-gated rollout.

## Post-P0 Update (2026-02-10)

The P0 correctness scope from `07_STORAGE_GAP_ANALYSIS_AND_EXECUTION_BACKLOG.md` has now been implemented.

Resolved from this audit:

- ingest endpoints now enforce upload validators and valid raw_id contract
- raw blob persistence is wired before orchestration in ingest API path
- dedup runtime path is active (tenant/session passed into orchestration)
- dedup raw_id type mismatch risk is handled for UUID-backed storage
- node/metrics/admin router-to-repo method mismatches are aligned
- frontend stream proxy path now matches backend `/api/v1/events/stream`

Still pending (non-P0):

- storage UI remains placeholder
- multi-file upload product workflow is not yet implemented
- encryption-at-rest integration remains pending
- cache/index integration hardening remains pending

## Post-P1 Update (2026-02-10)

P1 feature delivery is now implemented.

Resolved from prior audit gaps:

- storage backend API surface is now available under `/api/v1/storage/*`
- storage catalog persistence is implemented (`storage_files` table + repo)
- upload batch jobs/events are exposed for UI progress tracking
- storage page now supports:
  - multi-file upload
  - per-file lifecycle display
  - summary + backend health display
  - re-ingest/retry/delete-request actions
- ingest endpoints now also populate/update storage catalog metadata

Still pending:

- operational retention/deletion execution semantics beyond delete-request state
- historical blob re-encryption tooling for previously stored plaintext payloads

## Post-P2 Update (2026-02-10)

P2 hardening scope is now implemented.

Resolved from prior audit gaps:

- envelope encryption-at-rest can be activated in live runtime path
- tenant DEK persistence is wired (`tenant_crypto_keys`)
- query flow now uses Redis query cache for candidate recall acceleration
- query/index contract mismatch is resolved (`top_k` + legacy `search` compatibility)
- ingest index upsert now uses canonical node IDs from write result
- perf namespace is explicitly marked isolated (`PERF_LAYER_STATUS=isolated_legacy`)

## Post-Phase-A Update (2026-02-10)

Contract freeze and startup guardrails are now implemented:

- storage API method/path + response field contract is validated at startup
- feature-flag guardrails are validated at startup
- new rollout flags are defined for contract strictness, hard-delete gate, and live-job-stream rollout

## Frontend Storage Page (Current)

- `frontend/src/app/(app)/dashboard/storage/page.tsx` is implemented and operational.
- Supports multi-file upload, batch progress, catalog filtering, and lifecycle actions.
- Uses storage API surface under `/api/v1/storage/*`.

## Current Ingest Pipeline (Implemented Core)

Pipeline in `faim_native/orchestration/ingest_flow.py`:

1. extract blocks via `perception.router.route_extraction`
2. packetize via `perception.packetize.create_packet`
3. validate via `perception.validate.assert_valid`
4. encode via `encoding.vectorize_blocks`
5. write nodes/edges/events via `core.engine.FAIMNativeEngine.write_atoms`
6. optional Qdrant upsert only for non-STRICT profile

Supported extraction formats (extension-routed): PDF, DOCX, PPTX, XLSX/CSV, TXT/MD/code-like text, image stubs.

## Storage Backends (Current)

### Postgres

Primary source of truth for graph and operational metadata:

- nodes, edges, events, graph_version, snapshots
- raw_refs metadata table exists
- ingest_dedup table exists
- jobs/job_events exist
- auth tables and users table exist

### Redis

Available for:

- query cache
- stats cache
- locks fallback coordination
- auth OTP/rate-limit/lockout state

### Qdrant

Optional acceleration index via `faim_native/index/qdrant_index.py`.
Not intended as truth store.

### Filesystem Raw Store

`faim_native/store/raw/raw_store.py` provides immutable SHA256-addressed blob store.
`EncryptedRawStore` wrapper exists.

## Remaining Gaps and Risks

1. Retention/deletion is still request-state only for storage files (`delete_requested`), not full physical purge workflow.
2. Existing plaintext blobs from before encryption rollout are not automatically re-encrypted.
3. Query cache currently accelerates candidate recall path only; deeper stats cache wiring remains optional.

## Existing Strengths

- Deterministic vector schema and hashing.
- Deterministic inheritance/antisym logic.
- Fractal diagnostics framework (D, H, lambda, R, N, E).
- Multi-tenant schema and auth middleware foundation.
- Structured logging + redaction primitives.

## Conclusion

The platform has strong computational core pieces but **storage product surface is incomplete**.
The next implementation phase should focus on:

1. repairing ingest/storage contract correctness
2. wiring raw immutable storage + metadata persistence
3. building batch/multi-file API layer
4. implementing Storage page UX on top of stable endpoints
