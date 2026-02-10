# 07 - Storage Gap Analysis and Execution Backlog

This backlog maps work items to concrete modules.

## Priority Legend

- P0: blocking correctness/security
- P1: required for complete storage product
- P2: optimization/hardening

## P0 - Correctness and Contract Alignment

## Ingest Contract

- `api/routers/ingest.py`
  - enforce non-empty valid `raw_id` generation path
  - call raw persistence before orchestration
  - enforce upload validators

- `orchestration/ingest_flow.py`
  - ensure dedup path works for real runtime session
  - align raw_id typing with DB model

## Router/Repo API Alignment

- `api/routers/node.py` + `store/pg/repos/node_repo.py` + `store/pg/repos/edge_repo.py`
- `api/routers/metrics.py` + `store/pg/repos/graph_version_repo.py` + repos count methods
- `api/routers/admin.py` + repo method contracts

Goal: remove runtime method mismatch failures.

## Stream Path Alignment

- frontend stream proxy route contract must match backend events stream endpoint.

## P0 Implementation Status (2026-02-10)

P0 is implemented and validated.

## Completed Items

- [x] Ingest contract hardening (`api/routers/ingest.py`)
  - strict upload validators enforced
  - non-empty valid UUID raw_id path enforced
  - raw bytes are persisted before orchestration
  - tenant/session are passed into orchestration for runtime dedup

- [x] Orchestration dedup + typing (`orchestration/ingest_flow.py`)
  - runtime session path is active
  - dedup table write now stores UUID-safe `raw_id` (or null fallback)
  - ingest now rejects empty raw_id

- [x] Router/repo contract alignment
  - `store/pg/repos/node_repo.py`: `get_by_id`, `list_by_graph`, `count`
  - `store/pg/repos/edge_repo.py`: `get_parents`, `count`
  - `store/pg/repos/graph_version_repo.py`: `get_or_create`
  - `store/pg/repos/event_repo.py` + `store/pg/repos/snapshot_repo.py`: fixed runtime query import (`and_`)

- [x] Stream path alignment
  - `frontend/src/app/api/v1/stream/route.ts` now proxies to backend `/api/v1/events/stream`

## Validation Evidence

- `python3 -m compileall` on all changed backend P0 modules: passed.
- `PYTHONPATH=/home/sephi-asi/FAIM/faim_native pytest` targeted suites:
  - `tests/acceptance/test_AT_A3_ingest_emits_events.py`
  - `tests/acceptance/test_AT_A6_node_inspector_no_leak.py`
  - `tests/acceptance/test_AT_A4_sse_resume_after_seq.py`
  - `tests/acceptance/test_AT_S9_ingest_idempotency.py`
  - `tests/unit/test_stage_7_1_hardening.py`
  - `tests/unit/test_snapshot_repo.py`
- Result: all selected tests passed.

## P1 - Full Storage Feature Delivery

## P1 Implementation Status (2026-02-10)

P1 is implemented and validated.

## Completed Items

- [x] Raw truth wiring (`store/raw/raw_store.py`, `store/pg/repos/raw_repo.py`, `runtime/context.py`)
  - runtime now provides a shared `raw_store`
  - storage APIs and ingest path persist immutable raw bytes + `raw_refs` metadata before pipeline ingest
  - ingest endpoints now also write/update storage catalog lifecycle rows

- [x] Storage API surface (`api/routers/storage.py`)
  - `POST /api/v1/storage/uploads`
  - `GET /api/v1/storage/uploads/{job_id}`
  - `GET /api/v1/storage/uploads/{job_id}/events`
  - `GET /api/v1/storage/files`
  - `GET /api/v1/storage/files/{raw_id}`
  - `DELETE /api/v1/storage/files/{raw_id}`
  - `POST /api/v1/storage/files/{raw_id}/ingest`
  - `POST /api/v1/storage/files/{raw_id}/retry`
  - `GET /api/v1/storage/summary`
  - `GET /api/v1/storage/backends/health`

- [x] Storage UI (`frontend/src/app/(app)/dashboard/storage/page.tsx`)
  - multi-file upload with profile/persist selectors
  - per-batch result queue and progress
  - searchable/filterable catalog
  - re-ingest, retry, and delete-request actions
  - summary cards + backend health badges

- [x] Additive persistence model for storage catalog
  - new table/model: `storage_files`
  - migration: `store/pg/migrations/0005_storage_files.sql`
  - repo: `store/pg/repos/storage_file_repo.py`

## Validation Evidence

- compile checks: changed backend modules compile successfully
- backend regression suites from P0 still pass
- new tests:
  - `tests/acceptance/test_AT_P1_storage_api_surface.py`
  - `tests/unit/test_storage_file_repo.py`
- frontend storage page lint check passes:
  - `npx eslint src/app/(app)/dashboard/storage/page.tsx --max-warnings=0`

## Notes

- Full frontend project lint still reports pre-existing unrelated errors in other pages.
- P2 security/performance hardening is implemented (see section below and `10_P2_IMPLEMENTATION_REPORT.md`).

## Raw Truth Wiring

- `store/raw/raw_store.py`
- `store/pg/repos/raw_repo.py`
- `runtime/context.py`

Goal: upload writes immutable blob + raw_ref metadata before ingest.

## Storage API Surface

- add dedicated storage routes for:
  - batch upload jobs
  - file catalog/list/detail
  - summary metrics
  - retry/reprocess/delete operations

## Storage UI

- `frontend/src/app/(app)/dashboard/storage/page.tsx`
- supporting frontend lib/types/hooks

Goal: operational UI with multi-file ingestion lifecycle.

## P2 - Security/Performance Hardening

## P2 Implementation Status (2026-02-10)

P2 is implemented and validated.

## Completed Items

- [x] Encryption-at-rest integration
  - `runtime/context.py`: env-gated encrypted raw store wiring per tenant
  - `store/raw/crypto.py`: envelope cipher mode wired to tenant DEK manager
  - `store/raw/encrypted_payload_store.py`: production parity methods (`get_stats`, `load_by_sha`, `exists_by_sha`)
  - `store/crypto/envelope.py`: tenant DEK lifecycle manager (`tenant_crypto_keys` backing table)
  - `store/pg/models_crypto.py`, `store/pg/models_faim.py`, `store/pg/schema.sql`, `store/pg/migrations/0006_tenant_crypto_keys.sql`

- [x] Cache/index integration
  - `orchestration/query_flow.py`: query candidate recall cache get/set wired
  - `api/routers/query.py`: query flow now receives cache object from runtime context
  - `core/query/query_engine.py`: index recall aligned to `top_k` contract with stable fallback to legacy `search`
  - `index/qdrant_index.py`: added legacy `search(...)` compatibility wrapper
  - `orchestration/ingest_flow.py`: index upsert now uses canonical `write_result.node_ids` instead of vector hash fallback

- [x] Perf layer evaluation
  - decision: **isolate** legacy perf namespace from active ingest/query flow until explicit integration program
  - marker added at `orchestration/perf/__init__.py` with `PERF_LAYER_STATUS = "isolated_legacy"`

## Validation Evidence

- `python3 -m compileall faim_native` for modified modules: passed.
- targeted tests added and passing:
  - `tests/unit/test_p2_encryption_at_rest.py`
  - `tests/unit/test_p2_query_cache_index_alignment.py`
  - `tests/acceptance/test_AT_P2_security_perf_surface.py`

## Encryption-at-Rest Integration

- `store/crypto/envelope.py`
- `store/raw/encrypted_payload_store.py`
- `store/pg/models_crypto.py`

Goal: activate tenant DEK workflow in live ingest/storage path.

## Cache/Index Integration

- `cache/query_cache.py` in query flow
- Qdrant index method contract alignment in query engine

## Perf Layer Evaluation

- `orchestration/perf/*` currently appears decoupled/legacy namespace-linked
- decide: integrate, isolate, or archive

## Module Status Snapshot

| Area | Status |
|---|---|
| Storage UI | implemented (P1 baseline) |
| Core ingest math | implemented |
| Multi-file workflow | implemented (batch upload endpoint + UI queue) |
| Raw immutable persistence in ingest path | wired for ingest endpoints |
| Dedup runtime correctness | active in API path |
| Router/repo API consistency | aligned for node/metrics/admin routes |
| Frontend SSE proxy path | aligned with backend events stream |
| Storage API surface | implemented |
| Redis cache usage in query path | wired for candidate recall cache |
| Qdrant acceleration in query path | contract-aligned with stable fallback |
| Security primitives | integrated into runtime path (tenant DEK envelope mode) |

## Implementation Order (Recommended)

1. P0 contract repairs
2. raw persistence wiring
3. storage endpoints
4. storage UI
5. security integration and operations hardening
6. cache/index/perf optimization

## Definition of Done for Storage Program

- Uploading single/multi-file works from Storage page.
- Raw file metadata + provenance are durable and queryable.
- Ingest pipeline emits consistent status and events.
- Retrieval/explain path traces results back to immutable raw source.
- Security baseline enforced (authz, validation, redaction, encryption where required).
- Deterministic behavior preserved in STRICT mode.

## Phase A - Contract Freeze and Safety Guardrails

Status (2026-02-10): implemented.

Completed:

- [x] Storage API contract matrix frozen and validated at startup.
- [x] Required response-model fields checked via contract validator.
- [x] Feature-flag guardrail validation added for risky rollout paths.
- [x] New rollout flags defined and parsed in runtime config:
  - `FAIM_ENCRYPTION_FAIL_CLOSED`
  - `FAIM_STORAGE_HARD_DELETE_ENABLED`
  - `FAIM_STORAGE_LIVE_JOB_STREAM_ENABLED`
  - `FAIM_STORAGE_CONTRACT_STRICT`

Validation:

- `tests/unit/test_phase_a_storage_contract.py`
- `tests/unit/test_phase_a_feature_flags.py`

## Phase B - Backend Completion

Status (2026-02-10): implemented.

Completed:

- [x] Provenance inspect API surface
  - `GET /api/v1/storage/files/{raw_id}/provenance`
  - implementation: `api/routers/storage.py`

- [x] Upload cancellation model + safe stop points
  - `POST /api/v1/storage/uploads/{job_id}/cancel`
  - `orchestration/jobs/job_store.py` cancellation primitives
  - upload loop cancellation checkpoints in `api/routers/storage.py`

- [x] Full storage lifecycle audit events
  - wired events:
    - `STORAGE_RAW_STORED`
    - `STORAGE_DEDUP_HIT`
    - `STORAGE_EXTRACT_FAILED`
    - `STORAGE_ENCRYPT_FAILED`
    - `STORAGE_DELETE_REQUESTED`
    - `STORAGE_DELETE_EXECUTED`
  - implementation:
    - `api/routers/storage.py`
    - `api/routers/ingest.py`
    - `orchestration/jobs/storage_retention.py`

- [x] Retention cleanup worker path (dry-run + irreversible guardrails)
  - execution APIs:
    - `POST /api/v1/storage/retention/execute`
    - `POST /api/v1/storage/retention/jobs`
  - worker integration:
    - `orchestration/jobs/worker.py` supports `kind="storage_retention"`
  - hard-delete guardrails enforced using:
    - `FAIM_STORAGE_HARD_DELETE_ENABLED`
    - `irreversible=true` for physical delete

Validation:

- `tests/unit/test_phase_b_job_cancellation.py`
- `tests/unit/test_phase_b_storage_retention.py`
- `tests/acceptance/test_AT_PB_storage_phase_b_surface.py`

Implementation evidence:

- `12_PHASE_B_BACKEND_COMPLETION_REPORT.md`
