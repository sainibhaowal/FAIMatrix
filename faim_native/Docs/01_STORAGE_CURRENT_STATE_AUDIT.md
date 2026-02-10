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

Current state is **backend-heavy and partially wired**:

- Core ingest, vectorization, graph write, and evolution math exist.
- Storage page UI is currently placeholder only.
- Multi-file upload workflow is not implemented in UI or API contract.
- Raw immutable blob storage exists as modules, but is not connected to ingest API flow.
- Several router-to-repository method mismatches indicate broken runtime paths.

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

- encryption-at-rest activation for live ingest path (P2)
- query cache/index contract hardening (P2)
- operational retention/deletion execution semantics beyond delete-request state (P2)

## Frontend Storage Page (Current)

- `frontend/src/app/(app)/dashboard/storage/page.tsx` is a placeholder shell only.
- No file picker, no drop zone, no upload queue, no progress state, no storage metrics.
- No frontend API calls for ingest or storage catalog.

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

## Verified Gaps and Risks

## Critical (must fix first)

1. Ingest upload default fails when `raw_id` empty.
- API upload path passes `raw_id=""`.
- validation requires non-empty `block.raw_id` and `packet.raw_id`.
- Effect: multipart upload path fails unless caller forces non-empty raw_id.

2. Storage UI is non-functional for ingestion.
- no upload UX and no ingest API usage from storage page.

3. Frontend SSE proxy path mismatch.
- frontend proxies to `/api/v1/stream`
- backend exposes `/api/v1/events/stream`
- Effect: stream route contract mismatch.

## High

4. Router/repository contract mismatches in node/metrics/admin routers.
- Routers call methods not present in repos (`get_by_id`, `get_parents`, `get_or_create`, `count`, `list_by_graph`).
- Effect: endpoints can fail at runtime.

5. Ingest dedup is not effectively active from API ingest path.
- `run_ingest` dedup path depends on `session` parameter.
- API ingest router does not pass session into `run_ingest`.

6. Dedup raw_id typing mismatch risk.
- dedup model stores `raw_id` as UUID type.
- ingest inputs treat `raw_id` as generic string.

## Medium

7. Raw blob store modules are not wired into ingest API.
- bytes are processed in-memory for extraction/encoding but raw files are not persisted to RawStore in current API path.

8. Query cache is instantiated but not used in query flow.

9. Index contract mismatch in query path.
- query engine calls `index.search(...)` while FAIMIndex exposes `top_k`/`radius_search`.
- currently falls back to brute-force path.

10. Encryption-at-rest modules exist but are not integrated end-to-end for ingest raw content.

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
