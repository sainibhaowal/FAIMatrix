# 20B - Storage UI Runtime Workflow and Modes (Human Guide)

Date: 2026-02-11

## 1) Why this document

This is a plain-language guide for how Storage works now in real runtime:

- what the user sees on the Storage page
- what happens after clicking upload/cancel/retry/inspect
- where data is stored
- what `profile` and `persist_mode` mean

## 2) What user sees on Storage page

On `frontend/src/app/(app)/dashboard/storage/page.tsx`, users get:

1. Summary cards
- total files
- total bytes
- ingested/dedup counts
- failure count

2. Upload panel
- drag-drop area
- multi-file selector
- `profile` selector (`strict`, `fast`, `relaxed`)
- `persist_mode` selector (`strict`, `relaxed`)
- `Supported Files` button (opens backend-driven coverage panel)

3. Live queue
- per-file status and progress
- per-file timeline events
- per-file actions: cancel, retry, remove

4. File catalog
- list/search/filter by status
- actions: inspect, re-ingest, retry, delete request

5. Provenance drawer
- file metadata
- raw reference metadata
- dedup linkage
- linked nodes and events

6. Supported Files panel
- backend-supported extensions and MIME types
- upload-size limit
- OCR policy status (enabled/engine/fail-closed)

## 3) End-to-end upload workflow

## A) Upload start

1. User adds one or more files in UI.
2. UI creates queue items (`queued`).
3. UI starts uploads with bounded concurrency.
4. UI sends `POST /api/v1/storage/uploads` with `graph_id`, `profile`, `persist_mode`, files.

## B) Backend ingest path

In `api/routers/storage.py`:

1. Validate upload (size/type/filename/extension/mime match).
2. Persist raw bytes first (immutable raw store + `raw_refs` metadata).
3. Upsert `storage_files` row and mark ingesting.
4. Run ingest orchestration (`orchestration/ingest_flow.py`):
- extract blocks
- packetize/hash
- dedup check
- encode vectors
- write graph nodes/edges/events
- optional index upsert depending on `profile`
5. Update `storage_files` with final status/result.
6. Emit lifecycle audit events + job timeline events.

## C) UI live progress

For each running queue item, UI polls:

- `GET /api/v1/storage/uploads/{job_id}`
- `GET /api/v1/storage/uploads/{job_id}/events`

UI merges these into queue state and timeline until terminal status.

## D) Cancel / Retry / Inspect

Cancel:
- UI calls `POST /api/v1/storage/uploads/{job_id}/cancel`
- backend marks cancel requested and stops at safe points

Retry:
- UI calls `POST /api/v1/storage/files/{raw_id}/retry`
- backend re-runs ingest for failed files only

Inspect:
- UI calls `GET /api/v1/storage/files/{raw_id}/provenance`
- UI shows raw -> dedup -> node/event lineage

Supported files:
- UI calls `GET /api/v1/storage/supported-types`
- UI shows allowed extensions, MIME types, extractor mapping, and OCR policy flags

Optional post-upload evolve:
- when `FAIM_SELF_INVENT_ENABLED=true` and `FAIM_SELF_INVENT_AFTER_UPLOAD=true`,
  successful upload batches can enqueue a follow-up `evolve` job for macro invention.

## 4) Where data is stored

## Source of truth

1. Raw file bytes:
- filesystem raw store (content-addressed blobs by sha256)

2. Metadata and graph state:
- Postgres tables (`raw_refs`, `storage_files`, `nodes`, `edges`, `events`, `jobs`, `job_events`, `ingest_dedup`, etc.)

## Acceleration layers (not truth)

1. Redis: cache/locks/rate-limits/coordination
2. Qdrant: vector acceleration index

If Redis or Qdrant are unavailable, core truth path still relies on Postgres + raw store.

## 5) What `profile` means

Defined in `orchestration/ingest_flow.py` as:

- `strict`
- `fast`
- `relaxed`

Practical meaning today:

1. `strict`
- deterministic-oriented path
- skips index upsert (Qdrant acceleration write skipped)

2. `fast`
- allows acceleration path behavior where available

3. `relaxed`
- most permissive execution profile

Note:
- Core extraction/packetize/encode/write pipeline still runs for all profiles.
- Profile mostly affects acceleration/operational behavior around ingest path.

## 6) What `persist_mode` means

Defined in `orchestration/ingest_flow.py`:

- `strict` = wait-for-durable semantics intent
- `relaxed` = faster/less blocking semantics intent

Current runtime note:

- `persist_mode` is passed from UI/API/job payload and recorded in ingest events.
- In current storage ingest path, behavior difference is limited; it is primarily a policy input and forward-compatible control.

## 7) Status model used by UI

Queue/status mapping includes:

- `queued`
- `uploading`
- `ingesting`
- `ingested`
- `dedup_hit`
- `failed`
- `cancelled`

Catalog also includes lifecycle states like `delete_requested`.

## 8) Self-Inventing runtime behavior

Self-inventing is now active in live evolve runtime (flag-gated):

1. evolve computes diagnostics (`D/H/lambda`)
2. invention scanner consumes new event journal slices incrementally
3. coactivation counts are persisted in `self_invention_state`
4. macro invention runs when thresholds pass

Primary flags:

1. `FAIM_SELF_INVENT_ENABLED`
2. `FAIM_SELF_INVENT_ON_EVOLVE`
3. `FAIM_SELF_INVENT_AFTER_UPLOAD`
4. `FAIM_SELF_INVENT_MAX_MACROS_PER_CYCLE`
5. `FAIM_SELF_INVENT_EVENT_WINDOW`
6. `FAIM_SELF_INVENT_MIN_COACTIVATION_COUNT`
7. `FAIM_SELF_INVENT_LAMBDA_THRESHOLD`
8. `FAIM_SELF_INVENT_MIN_REDUNDANCY_REDUCTION`

## 9) Security path in this workflow

1. Frontend session auth (NextAuth) + middleware auth header injection.
2. Backend storage routes enforce tenant isolation/authz.
3. Upload validation blocks malformed/abusive inputs.
4. Production policy enforces encryption-at-rest fail-closed.
5. Structured lifecycle logs + audit events include correlation fields.

## 10) Quick architecture diagram

```text
[Storage Page UI]
  -> /api/v1/storage/* (Next middleware + auth)
  -> Next rewrites proxy to backend
  -> [FAIM API storage router]
       -> raw store (immutable blobs)
       -> Postgres (raw_refs/storage_files/nodes/events/jobs)
       -> Redis/Qdrant (acceleration)
  -> UI polls job status/events
  -> UI renders queue/catalog/provenance
```

## 11) How to verify quickly

1. Open `/dashboard/storage`.
2. Upload 2-3 files.
3. Confirm queue transitions and terminal states.
4. Cancel one in-progress file.
5. Retry one failed file.
6. Open Inspect and verify provenance drawer fields.
7. Check summary/catalog update after actions.

## 12) File Type Handling Matrix (What happens per upload type)

This is the practical behavior in current runtime (Phase I + J).

| Input Type | Allowed Upload | Extraction Behavior | Result Quality Notes |
|---|---|---|---|
| PDF with selectable text | yes | page text extracted into text blocks | high fidelity for text pages |
| PDF page with only image/scanned content | yes | OCR attempted when `FAIM_OCR_ENABLED=true`; otherwise image stub block | OCR-enabled mode extracts text blocks; fallback mode keeps `image_stub` with low confidence |
| DOC/DOCX | yes | paragraph + table extraction with anchors | good for typical office docs |
| PPT/PPTX | yes | slide text extraction | good for text-heavy slides |
| XLS/XLSX | yes | sheet rows extracted as table blocks | structured/tabular ingestion |
| CSV | yes | grouped row blocks as table content | structured/tabular ingestion |
| TXT/MD/RST/HTML/XML/JSON/YAML/TOML | yes | text extraction; markdown section-aware | good for textual/config content |
| Code files (`.py`, `.js`, `.ts`, `.java`, etc.) | yes | routed as text extraction and vectorized | treated as text/code content, no language-specific compiler analysis |
| Images (`png/jpg/jpeg/gif/webp/svg/bmp/tiff`) | yes | OCR attempted when enabled; otherwise image stub block | OCR-enabled mode yields text blocks; non-text/failed OCR returns `image_stub` |
| Unsupported extension/MIME mismatch | no | rejected at validator layer | returns validation error (e.g., 415/400) |
| Oversized file (> max upload limit) | no | rejected at validator layer | default max is 10 MB unless reconfigured |

## 13) Validation and security checks on upload

Before ingestion, storage upload path enforces:

1. filename sanitization and path-traversal rejection
2. extension allowlist
3. MIME type allowlist
4. MIME-extension compatibility check
5. file size limit check

If checks fail, upload is rejected early and does not enter graph write path.

OCR runtime is additionally controlled by:

1. `FAIM_OCR_ENABLED`
2. `FAIM_OCR_ENGINE` (current supported engine: `tesseract`)
3. `FAIM_OCR_FAIL_CLOSED` (if true, OCR failures fail extraction instead of silent fallback)

---

This document is explanatory only and aligned with implemented runtime through Phase J.
