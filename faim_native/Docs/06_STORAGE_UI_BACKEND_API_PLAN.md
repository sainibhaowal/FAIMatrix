# 06 - Storage UI + Backend API Plan

This document started as the no-code implementation plan for storage.
It is now the design + status record for implemented phases P0/P1/P2, A-H, I, J, and K1-K8 documentation/validation reconciliation for authz + memory API stream alignment.

## Implementation Baseline (2026-02-10)

Actual implemented baseline:

- backend: `api/routers/storage.py` under `/api/v1/storage/*`
- frontend: `frontend/src/app/(app)/dashboard/storage/page.tsx`
- persistence: `storage_files` table + repo + migration

Use this doc as design intent + final status summary. Detailed implementation evidence lives in reports `09` through `29` plus K8 summary reports.

## Phase A-H Status Summary

1. Phase A (Contract Freeze + Guardrails): implemented
2. Phase B (Backend Completion): implemented
3. Phase C (Storage UI Completion): implemented
4. Phase D (Security Hardening): implemented
5. Phase E (Observability + Operations): implemented
6. Phase F (Validation + Non-Regression): implemented
7. Phase G (Documentation Reconciliation): implemented
8. Phase H (Commit and Release Hygiene): implemented

## Phase G Update (2026-02-11)

Documentation reconciliation completed in this phase:

- contradictory/outdated plan text removed
- endpoint/status sections aligned with implemented runtime
- future-only enhancements separated from completed scope

Evidence: `18_PHASE_G_DOCUMENTATION_RECONCILIATION_REPORT.md`

## Phase H Update (2026-02-11)

Commit/release hygiene completed in this phase:

- DoD mapping finalized in this plan doc
- deferred item ownership/reason records normalized in backlog
- release verification executed before release tag creation

Evidence: `19_PHASE_H_COMMIT_RELEASE_HYGIENE_REPORT.md`

## Phase I Update (2026-02-11)

OCR + UI polish + file coverage visibility completed:

- backend OCR service integrated for image uploads and scanned PDF pages (feature-flag controlled)
- storage API now exposes supported-file coverage endpoint
- storage UI now includes supported-files panel and rounded card polish
- docker/runtime configuration updated for OCR dependencies and flags

Evidence: `21_PHASE_I_OCR_UI_POLISH_REPORT.md`

## Phase J Update (2026-02-11)

Self-inventing runtime wiring completed:

- evolve path now executes bounded, flag-gated self-invention cycle
- invention runtime state persists incrementally in `self_invention_state`
- optional post-upload evolve enqueue supports storage-triggered invention flow
- evolve API surface now includes invention count (`inventions`)

Evidence: `22_PHASE_J_SELF_INVENTING_RUNTIME_INTEGRATION_REPORT.md`

## Phase K1 Update (2026-02-13)

API keys/authz + memory API contract freeze completed as an additive next-stream design step:

- existing storage/query/ingest/node routes frozen for compatibility
- new additive contract defined for `/api/v1/api-keys/*` and `/api/v1/memory/*`

Evidence: `23_API_KEYS_AUTHZ_AND_MEMORY_CONTRACT_PLAN.md`

## Phase K2 Update (2026-02-13)

Auth schema/model foundation upgrade completed:

- `tenant_api_keys` supports scope/expiry/lifecycle metadata
- append-only `auth_key_audit_log` table added
- ORM/repo support added for create/revoke/rotate audit metadata handling

Evidence: `24_PHASE_K2_AUTH_MODEL_UPGRADE_REPORT.md`

## Phase K3 Update (2026-02-13)

Auth middleware + scope enforcement baseline completed:

- DB-primary tenant key validation with compatibility-gated env fallback
- request context propagation (`auth_method`, `auth_key_id`, `auth_scopes`)
- scope dependency wired for protected API surfaces
- rate-limit category alignment under `/api/v1/*`

Evidence: `25_PHASE_K3_AUTH_MIDDLEWARE_AUTHZ_ENFORCEMENT_REPORT.md`

## Phase K4 Update (2026-02-13)

API key management runtime and UI completed:

- `/api/v1/api-keys/*` create/list/rotate/revoke/audit routes
- tenant-scoped lifecycle operations and one-time key reveal semantics
- dashboard API Keys page with scope/expiry controls and audit timeline

Evidence: `26_PHASE_K4_API_KEYS_MANAGEMENT_API_UI_REPORT.md`

## Phase K5 Update (2026-02-13)

Agent-facing memory API runtime completed:

- `/api/v1/memory/search|get|provenance|write|patch`
- idempotency ledger and optimistic update guard
- strict tenant and graph isolation semantics

Evidence: `27_PHASE_K5_MEMORY_API_IMPLEMENTATION_REPORT.md`

## Phase K6 Update (2026-02-13)

Security hardening completed for API key and memory surfaces:

- key lifecycle audit taxonomy (`used`, `denied(scope|expired|revoked)`)
- explicit revoked/expired denial policy paths
- sanitized audit metadata and redaction-safe logging expectations
- endpoint-level read/write/search rate-limit categories

Evidence: `28_PHASE_K6_SECURITY_HARDENING_AUDIT_RATELIMIT_REPORT.md`

## Phase K7 Update (2026-02-14)

Validation and non-regression completion:

- expanded unit + acceptance coverage for key lifecycle/scope matrix/memory lifecycle
- frontend e2e coverage for API key actions and error states
- runtime recency timestamp normalization fix validated in query path

Evidence: `29_PHASE_K7_VALIDATION_NON_REGRESSION_REPORT.md`

## Phase K8 Update (2026-02-14)

Documentation + commit hygiene reconciliation:

- storage/security/backlog docs aligned with K1-K7 implemented state
- consolidated API key/authz and memory contract summary reports added
- commit stream split into scoped doc/report integration steps

Evidence:

- `24_PHASE_K_API_KEYS_AUTHZ_REPORT.md`
- `25_PHASE_K_MEMORY_API_CONTRACT_REPORT.md`

## 1) Product Objective

Build and operate a production Storage page that can:

- upload one or multiple files
- show per-file lifecycle and failures
- show storage usage and ingestion health
- expose provenance so graph memory can be traced to original source

## 2) Backend API Contract (Implemented)

All routes under `/api/v1/storage`.

## Upload and Jobs

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/v1/storage/uploads` | Start multi-file upload batch |
| `GET` | `/api/v1/storage/uploads/{job_id}` | Batch status and per-file progress |
| `GET` | `/api/v1/storage/uploads/{job_id}/events` | Upload job timeline |
| `POST` | `/api/v1/storage/uploads/{job_id}/cancel` | Request safe job cancellation |

## Supported File Coverage

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/v1/storage/supported-types` | Validator/extractor/OCR capability matrix for UI |

## File Catalog and Provenance

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/v1/storage/files` | Paginated file catalog with statuses |
| `GET` | `/api/v1/storage/files/{raw_id}` | File metadata detail |
| `GET` | `/api/v1/storage/files/{raw_id}/provenance` | Provenance inspect (`raw_id -> dedup/nodes/events`) |
| `DELETE` | `/api/v1/storage/files/{raw_id}` | Controlled delete request |

## Ingestion and Reprocessing

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/v1/storage/files/{raw_id}/ingest` | Re-ingest a stored raw file |
| `POST` | `/api/v1/storage/files/{raw_id}/retry` | Retry failed extraction/encode path |

## Usage, Health, and Operations

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/v1/storage/summary` | totals by bytes/files/status/type |
| `GET` | `/api/v1/storage/backends/health` | Postgres/Redis/Qdrant/raw-store health |
| `GET` | `/api/v1/storage/ops/metrics` | upload/dedup/failure/latency/backend-state metrics |
| `POST` | `/api/v1/storage/retention/execute` | retention execution (dry-run + guarded irreversible mode) |
| `POST` | `/api/v1/storage/retention/jobs` | enqueue retention cleanup worker job |

## 3) Required Response Fields (Minimum)

Every file item should include:

- `raw_id`
- `sha256`
- `filename`
- `mime_type`
- `size_bytes`
- `graph_id`
- `ingest_status`
- `packet_hash` (if available)
- `node_count` / `vector_count` (if completed)
- `error` (if failed)
- timestamps (`uploaded_at`, `ingested_at`, `updated_at`)

## 4) Storage Page UI Architecture (Implemented)

## Sections

1. Upload Panel
- drag-drop zone
- multiple selection
- profile/persist mode selector

2. Upload Queue
- per-file progress state
- retry/cancel controls
- per-file timeline events

3. File Catalog Grid/Table
- filter by status/type/date
- search by filename/hash/raw_id
- actions: inspect, re-ingest, retry, delete-request

4. Storage Summary Cards
- total files
- total bytes
- completion/failure counts
- dedup hit count

5. Backend Health Widget
- Postgres/Redis/Qdrant/raw-store readiness

6. Provenance Drawer
- file/raw metadata
- dedup linkage
- node and event summaries

7. Supported Files Panel
- endpoint-backed supported extension/MIME list
- OCR capability status and policy flags
- upload size limit visibility

## 5) Multi-file Workflow (Implemented)

1. user selects N files
2. frontend sends multipart request
3. backend persists each raw blob + metadata first
4. backend runs ingest per file
5. backend returns job id and per-file result status
6. frontend polls `/uploads/{job_id}` and `/uploads/{job_id}/events`
7. frontend updates queue and catalog incrementally
8. retry/cancel can be executed per file/job without restarting whole batch
9. optional follow-up evolve job can be enqueued for self-inventing when enabled

## 6) Data Consistency Rules (Enforced)

1. raw persistence happens before extraction
2. no graph node write without provenance linkage
3. dedup is packet-hash based and idempotent
4. retries do not duplicate graph nodes for same packet hash
5. production encryption policy is fail-closed

## 7) Acceptance Criteria Status

1. single and multi-file uploads complete through graph write path: met
2. uploaded files are visible in catalog with accurate status: met
3. dedup retry does not duplicate graph nodes: met
4. strict deterministic behavior remains stable: met
5. provenance is explainable from `raw_id` to graph artifacts: met
6. storage endpoints enforce auth and tenant isolation: met
7. supported file coverage and OCR policy visibility are available in UI: met

## 8) Observability Status

Implemented baseline includes:

- upload count/bytes metrics
- ingest phase latency metrics
- dedup hit ratio
- failure reason taxonomy
- backend dependency state (`up`/`degraded`/`down`)
- structured lifecycle logs with correlation IDs

## 9) Future Enhancements Only (Post-Phase K8)

1. historical blob re-encryption program for pre-policy plaintext payloads
2. environment-level dashboard/alert wiring for storage/security SLOs
3. optional deeper cache/index/perf optimization beyond current deterministic baseline

## 10) Deferred Items Register (Reason + Owner)

These items are explicitly deferred and are not blockers for the completed core storage program.

| Deferred Item | Reason | Owner | Target |
|---|---|---|---|
| Historical blob re-encryption for pre-policy plaintext payloads | Existing data remains readable and policy already fail-closed for new production writes; migration requires controlled tenant-by-tenant rollout window | Storage Security Team | Post-H release stream |
| Environment-specific dashboards/alerts for storage/security SLOs | Runtime metrics/log contracts are implemented; deployment tooling differs by environment and must be wired by platform ops | SRE / Platform Operations | Post-H operations sprint |
| Deep cache/index/perf tuning beyond deterministic baseline | Current deterministic fallback is correct and production-safe; higher-risk tuning requires dedicated perf benchmarking cycle | Performance Engineering | Post-H performance program |

## 11) Phase H Release-Hygiene DoD Mapping

| DoD Requirement | Status | Evidence |
|---|---|---|
| Every item in this plan is implemented or explicitly deferred with reason and owner | met | sections `2` to `8` (implemented), section `10` (deferred register) |
| Security/ops requirements are enforced in production mode (not optional defaults) | met | section `6`, `14_PHASE_D_SECURITY_HARDENING_REPORT.md`, `16_STORAGE_OPERATIONS_RUNBOOK.md` |
| Storage flow works end-to-end with provenance and operational controls | met | sections `2`, `4`, `5`, `7`, `13_PHASE_C_STORAGE_UI_COMPLETION_REPORT.md`, `12_PHASE_B_BACKEND_COMPLETION_REPORT.md` |
| Tests and docs prove production readiness and non-regression | met | `17_PHASE_F_VALIDATION_NON_REGRESSION_REPORT.md`, `18_PHASE_G_DOCUMENTATION_RECONCILIATION_REPORT.md`, `19_PHASE_H_COMMIT_RELEASE_HYGIENE_REPORT.md` |
