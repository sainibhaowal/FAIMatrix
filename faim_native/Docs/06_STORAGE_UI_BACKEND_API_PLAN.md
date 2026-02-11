# 06 - Storage UI + Backend API Plan

This document started as the no-code implementation plan for storage.
It is now the design + status record for implemented phases P0/P1/P2 and A-F.

## Implementation Baseline (2026-02-10)

Actual implemented baseline:

- backend: `api/routers/storage.py` under `/api/v1/storage/*`
- frontend: `frontend/src/app/(app)/dashboard/storage/page.tsx`
- persistence: `storage_files` table + repo + migration

Use this doc as design intent + final status summary. Detailed implementation evidence lives in reports `09` through `17`.

## Phase A-F Status Summary

1. Phase A (Contract Freeze + Guardrails): implemented
2. Phase B (Backend Completion): implemented
3. Phase C (Storage UI Completion): implemented
4. Phase D (Security Hardening): implemented
5. Phase E (Observability + Operations): implemented
6. Phase F (Validation + Non-Regression): implemented

## Phase G Update (2026-02-11)

Documentation reconciliation completed in this phase:

- contradictory/outdated plan text removed
- endpoint/status sections aligned with implemented runtime
- future-only enhancements separated from completed scope

Evidence: `18_PHASE_G_DOCUMENTATION_RECONCILIATION_REPORT.md`

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

## 5) Multi-file Workflow (Implemented)

1. user selects N files
2. frontend sends multipart request
3. backend persists each raw blob + metadata first
4. backend runs ingest per file
5. backend returns job id and per-file result status
6. frontend polls `/uploads/{job_id}` and `/uploads/{job_id}/events`
7. frontend updates queue and catalog incrementally
8. retry/cancel can be executed per file/job without restarting whole batch

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

## 8) Observability Status

Implemented baseline includes:

- upload count/bytes metrics
- ingest phase latency metrics
- dedup hit ratio
- failure reason taxonomy
- backend dependency state (`up`/`degraded`/`down`)
- structured lifecycle logs with correlation IDs

## 9) Future Enhancements Only (Post-Phase G)

1. historical blob re-encryption program for pre-policy plaintext payloads
2. environment-level dashboard/alert wiring for storage/security SLOs
3. optional deeper cache/index/perf optimization beyond current deterministic baseline
