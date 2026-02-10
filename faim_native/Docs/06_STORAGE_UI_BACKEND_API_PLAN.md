# 06 - Storage UI + Backend API Plan

This is a no-code implementation plan for full storage setup.

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
