# 06 - Storage UI + Backend API Plan

This is a no-code implementation plan for full storage setup.

## Implementation Update (2026-02-10)

P1 implementation now exists for the route set described in this document.

Actual implemented baseline:

- backend: `api/routers/storage.py` under `/api/v1/storage/*`
- frontend: `frontend/src/app/(app)/dashboard/storage/page.tsx`
- persistence: `storage_files` table + repo + migration

Use this doc as design intent, and `09_P1_IMPLEMENTATION_REPORT.md` as implementation record.

## Phase A Update (2026-02-10)

Contract freeze and safety guardrails are now implemented.

Implemented in Phase A:

- storage route/method matrix compatibility validator (`api/contracts/storage_contract.py`)
- startup contract check in API app (`api/app.py`)
- rollout feature flags and guardrail validation:
  - `FAIM_ENCRYPTION_FAIL_CLOSED`
  - `FAIM_STORAGE_HARD_DELETE_ENABLED`
  - `FAIM_STORAGE_LIVE_JOB_STREAM_ENABLED`
  - `FAIM_STORAGE_CONTRACT_STRICT`
- runtime config parsing/validation for new flags (`runtime/config.py`)
- regression tests for contract freeze and guardrail rules

See `11_PHASE_A_CONTRACT_FREEZE_REPORT.md` for implementation evidence.

## Phase B Update (2026-02-10)

Backend completion items are now implemented.

Implemented in Phase B:

- provenance inspect API:
  - `GET /api/v1/storage/files/{raw_id}/provenance`
- upload cancellation API + job cancellation model:
  - `POST /api/v1/storage/uploads/{job_id}/cancel`
- retention cleanup APIs:
  - `POST /api/v1/storage/retention/execute`
  - `POST /api/v1/storage/retention/jobs`
- retention worker execution path in `orchestration/jobs/worker.py` for `kind="storage_retention"`
- lifecycle audit event coverage:
  - `STORAGE_RAW_STORED`
  - `STORAGE_DEDUP_HIT`
  - `STORAGE_EXTRACT_FAILED`
  - `STORAGE_ENCRYPT_FAILED`
  - `STORAGE_DELETE_REQUESTED`
  - `STORAGE_DELETE_EXECUTED`

See `12_PHASE_B_BACKEND_COMPLETION_REPORT.md` for implementation evidence.

## Phase C Update (2026-02-10)

Storage UI completion items are now implemented.

Implemented in Phase C:

- drag-drop upload zone with multi-file append behavior
- real per-file queue lifecycle state model in UI:
  - `queued`, `uploading`, `ingesting`, `dedup_hit`, `ingested`, `failed`, `cancelled`
- per-file queue actions:
  - cancel (`POST /api/v1/storage/uploads/{job_id}/cancel` when job id exists)
  - retry (`POST /api/v1/storage/files/{raw_id}/retry` when raw_id exists)
- upload job status/event polling wired:
  - `GET /api/v1/storage/uploads/{job_id}`
  - `GET /api/v1/storage/uploads/{job_id}/events`
- provenance inspect drawer wired:
  - `GET /api/v1/storage/files/{raw_id}/provenance`
- summary cards + catalog filters/actions preserved from baseline

See `13_PHASE_C_STORAGE_UI_COMPLETION_REPORT.md` for implementation evidence.

## Phase D Update (2026-02-10)

Security hardening for production policy is now implemented.

Implemented in Phase D:

- production policy enforcement:
  - production requires `FAIM_ENCRYPTION_AT_REST=true`
  - production requires `FAIM_ENCRYPTION_FAIL_CLOSED=true`
- production plaintext fallback removal:
  - runtime raw store fails closed if encryption path is unavailable in production
  - storage/ingest routers do not use plaintext fallback store in production mode
- upload abuse protections:
  - explicit MIME/extension mismatch rejection
  - explicit path-like filename rejection
  - oversize rejection path retained (413)
- storage route authz/tenant isolation test coverage:
  - all storage routes require auth headers
  - cross-tenant job/file/provenance access is rejected

See `14_PHASE_D_SECURITY_HARDENING_REPORT.md` for implementation evidence.

## Phase E Update (2026-02-10)

Observability + operations baseline is now implemented.

Implemented in Phase E:

- storage observability API:
  - `GET /api/v1/storage/ops/metrics`
- metrics coverage:
  - upload count/bytes
  - dedup hit ratio
  - failure reason taxonomy
  - ingest phase latency aggregates from `INGEST_PHASE_LATENCY` events
  - backend health states (`up`/`degraded`/`down`) with probe latency
- structured lifecycle logs with correlation fields:
  - `request_id`, `tenant_id`, `graph_id`, `job_id`, `raw_id`, `op`, `status`, `failure_reason`, `latency_ms`
- rollout flags for observability and structured lifecycle logging:
  - `FAIM_STORAGE_OBSERVABILITY_ENABLED`
  - `FAIM_STORAGE_STRUCTURED_LIFECYCLE_LOGS`
- operational documentation:
  - runbook with rollout/rollback/incident handling and key rotation notes

See `15_PHASE_E_OBSERVABILITY_OPERATIONS_REPORT.md` and `16_STORAGE_OPERATIONS_RUNBOOK.md` for implementation evidence.

## 1) Product Objective

Build a production Storage page that can:

- upload one or multiple files
- show per-file lifecycle and failures
- show storage usage and ingestion health
- expose provenance so graph memory can be traced to original source

## 2) Proposed Backend API Contract

All routes under `/api/v1/storage` plus ingest orchestration routes.

## Upload and Jobs

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/v1/storage/uploads` | Start multi-file upload batch |
| `GET` | `/api/v1/storage/uploads/{job_id}` | Batch status and per-file progress |
| `GET` | `/api/v1/storage/uploads/{job_id}/events` | Upload job timeline |

## File Catalog

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/v1/storage/files` | Paginated file catalog with statuses |
| `GET` | `/api/v1/storage/files/{raw_id}` | File metadata + provenance summary |
| `DELETE` | `/api/v1/storage/files/{raw_id}` | Controlled file delete request |

## Ingestion and Reprocessing

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/v1/storage/files/{raw_id}/ingest` | Re-ingest a stored raw file |
| `POST` | `/api/v1/storage/files/{raw_id}/retry` | Retry failed extraction/encode path |

## Usage and Health

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/v1/storage/summary` | totals by bytes/files/status/type |
| `GET` | `/api/v1/storage/backends/health` | Postgres/Redis/Qdrant/raw-store status |

## 3) Required Response Fields (minimum)

Every file item should include:

- `raw_id`
- `sha256`
- `filename`
- `mime_type`
- `size_bytes`
- `graph_id`
- `ingest_status`
- `packet_hash` (if available)
- `node_count`/`vector_count` (if completed)
- `error` (if failed)
- timestamps (`uploaded_at`, `ingested_at`, `updated_at`)

## 4) Storage Page UI Architecture

## Sections

1. Upload Panel
- drag-drop zone
- multiple selection
- profile/persist mode selector

2. Upload Queue
- per-file progress state
- retry/cancel controls

3. File Catalog Grid/Table
- filter by status/type/date
- search by filename/hash/raw_id
- actions: inspect, re-ingest, delete

4. Storage Summary Cards
- total files
- total bytes
- completion/failure counts
- dedup hit count

5. Backend Health Widget
- Postgres/Redis/Qdrant/raw-store readiness

## 5) Multi-file Workflow (planned)

1. user selects N files
2. frontend sends multipart batch request
3. backend persists each raw blob + metadata first
4. backend runs ingest per file
5. backend returns job id
6. frontend polls job or subscribes SSE
7. frontend updates queue and catalog incrementally

## 6) Data Consistency Rules

1. raw persistence must happen before extraction
2. no graph node write without valid provenance fields
3. dedup should be packet-hash based and idempotent
4. retries must not create duplicate nodes for same packet hash

## 7) Implementation Phases

## Phase 0 - Contract Repair

- align existing router/repo method names
- fix ingest raw_id contract
- wire session into ingest orchestration where required
- normalize dedup raw_id type handling

## Phase 1 - Raw File Truth Wiring

- store bytes in RawStore
- persist `raw_refs`
- pass valid raw_id to extraction and vector pipeline

## Phase 2 - Storage API Surface

- implement upload batch/job routes
- implement file catalog + summary routes
- implement reprocess/retry routes

## Phase 3 - Storage UI

- build upload queue and file catalog page
- add health + metrics cards
- add filtering and provenance drawer

## Phase 4 - Security and Operations

- enforce validators on upload endpoints
- enable encryption-at-rest path in production mode
- add audit trails and SLO metrics

## 8) Acceptance Criteria

1. single and multi-file uploads complete through graph write path
2. each uploaded file is visible in storage catalog with accurate status
3. dedup retry of same file does not duplicate graph nodes
4. strict mode deterministic behavior remains stable
5. storage page can explain provenance (`raw_id` -> nodes/events)
6. all storage endpoints require valid auth and tenant isolation

## 9) Observability Required

Track at minimum:

- upload count/bytes by tenant
- ingest latency by phase (extract/encode/write/index)
- dedup hit ratio
- failure reasons grouped by extractor/type
- backend dependency availability (Postgres/Redis/Qdrant/raw-store)














What’s Still Left (from current code vs plan)

UI drag-drop upload UX is missing.
UI upload queue does not support cancel/retry controls per-file during processing.
UI does not consume /uploads/{job_id} and /uploads/{job_id}/events for live timeline/progress.
UI lacks a provenance inspect/drawer flow (raw_id -> packet -> nodes/events view).
Security/ops is partial: encryption exists but not enforced as production-default fail-closed policy.
Audit trail coverage is incomplete for all required storage lifecycle events.
Observability/SLO metrics are not fully implemented as specified.
Retention/deletion is still logical (delete_requested), not full physical policy workflow.
Automated tests are not yet full production-grade for authz/abuse/deletion/encryption rotation scenarios.
Docs 01/02/03/05 still contain outdated contradictions and need reconciliation.
Production Implementation Plan (End-to-End)

Phase A: Freeze Contracts + Safety Guardrails
Lock API contract and response schema for all storage routes.
Add strict compatibility checks so existing UI/backend calls do not break.
Define rollout flags for risky features (encryption fail-closed, hard delete worker, live job stream mode).


Phase B: Backend Completion
Add missing provenance API surface for inspect flow.
Add cancellation model for upload jobs and enforce safe stop points.
Add complete storage lifecycle audit events: raw stored, dedup hit, extract failed, encrypt failed, delete requested, delete executed.
Add retention worker path for physical cleanup policy (with dry-run + irreversible mode guardrails).


Phase C: Storage UI Completion
Implement drag-drop zone with multi-file selection.
Implement real upload queue state machine with per-file cancel/retry behavior.
Wire polling/stream consumption from /uploads/{job_id} and /uploads/{job_id}/events.
Add provenance drawer/detail panel connected to backend provenance endpoint.
Keep existing summary/cards/catalog behavior intact.


Phase D: Security Hardening to Production Grade
Enforce production policy mode: encryption-at-rest fail-closed in production env.
Remove unsafe plaintext fallback in production profile.
Add upload abuse protections and explicit rejection paths (oversize, malformed mime/ext mismatch, path traversal names).
Ensure tenant isolation and authz checks on every storage route are covered by tests.


Phase E: Observability + Operations
Add metrics for upload count/bytes, phase latency, dedup ratio, failure reason taxonomy, backend health states.
Add structured logs for storage lifecycle with request_id/tenant_id/job_id/raw_id correlation.
Add operational runbook notes (flags, rollback, incident actions, key rotation behavior).


Phase F: Validation and Non-Regression
Unit tests for new backend logic and crypto/error paths.
API/acceptance tests for full storage lifecycle, authz isolation, retry idempotency, cancellation, delete flow.
Frontend tests for queue states and provenance interactions.
Run compile, backend test suite, targeted frontend checks, and regression suites.


Phase G: Documentation Reconciliation
Update 01..07 docs to remove contradictions and mark final status accurately.
Add final implementation report for this completion phase with exact file map, env flags, and test evidence.
Keep backlog updated with what is done vs future enhancements only.


Phase H: Commit and Release Hygiene
Use small scoped commits per phase.
Final squashed/release commit only after all validations pass.
Tag release after your final verification.
Definition of Done for This Plan

Every item in 06_STORAGE_UI_BACKEND_API_PLAN.md is implemented or explicitly marked deferred with reason and owner.


Security/ops requirements are enforced in production mode, not optional defaults.


Storage flow works end-to-end with provenance and operational controls.


Tests and docs prove production readiness and no regressions.


If you approve, I will start Phase A immediately and execute this in order without skipping steps.




  first build a plan-- what you have to do and what  you will to by maintaing all about what we discusss about about security, maintainece, proper gap problem -- so build a proper Phase B and others implememtation technical plan so you can do proper work without any mistake and ẃithout any damage other codes files and data and folder and workflows-- so build first end to end proper production mature and production grade professional plan acurately then with my permission you can start work -- dont forget to ducmenting everything at the end  please. make sure acurate and production matue

