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

## P1 - Full Storage Feature Delivery

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
| Storage UI | placeholder |
| Core ingest math | implemented |
| Multi-file workflow | missing |
| Raw immutable persistence in ingest path | missing wiring |
| Dedup runtime correctness | partial/broken path |
| Router/repo API consistency | broken in multiple routes |
| Redis cache usage in query path | mostly not wired |
| Qdrant acceleration in query path | fallback-dominant |
| Security primitives | strong foundation, partial integration |

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
