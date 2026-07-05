# 27 - Phase K5 Memory API Implementation Report

Date: 2026-02-13

Status: Completed

## Scope

Implement dedicated agent-facing memory API runtime with additive contracts:

- `POST /api/v1/memory/search`
- `GET /api/v1/memory/{node_id}`
- `GET /api/v1/memory/{node_id}/provenance`
- `POST /api/v1/memory/write`
- `PATCH /api/v1/memory/{node_id}`

Including:

- write idempotency key support
- optimistic update guard for patch
- strict tenant + graph isolation
- route-level authz scope guards

## Implemented

## Router and App Wiring

Added:

- `faim_native/api/routers/memory.py`

Registered:

- `faim_native/api/routers/__init__.py`
- `faim_native/api/app.py`

## Data Model and Migration (K5 Idempotency Ledger)

Added migration:

- `faim_native/store/pg/migrations/0009_memory_write_idempotency.sql`

Schema and model updates:

- `faim_native/store/pg/schema.sql`
- `faim_native/store/pg/models_faim.py` (`MemoryWriteRequestModel`)

Repository:

- `faim_native/store/pg/repos/memory_write_idempotency_repo.py`
- export in `faim_native/store/pg/repos/__init__.py`

## Service Helpers

Added:

- `faim_native/api/services/memory_service.py`

Includes:

- strict base64 decode helper
- deterministic memory write request hashing
- idempotency key parsing/validation (header/body)
- UTC datetime normalization

## Endpoint Behavior

## `POST /api/v1/memory/search`

- reuses `orchestration.query_flow.run_query`
- supports profile + explain flags
- returns ranked memory results with score metadata

## `GET /api/v1/memory/{node_id}`

- tenant-scoped node lookup by `graph_id`
- returns node memory details (raw linkage, vector hash, touch/residual, timestamps)

## `GET /api/v1/memory/{node_id}/provenance`

- reuses existing storage/node provenance patterns
- includes:
  - raw reference (if available)
  - dedup linkage via packet hash
  - parent inheritance summary
  - bounded event timeline

## `POST /api/v1/memory/write`

- accepts `text` or `bytes_base64` payload
- enforces existing upload validators and filename/content-type checks
- reuses ingest path (`run_ingest`) and raw persistence helpers
- supports idempotency:
  - first request => creates in-progress record
  - same key + same payload => deterministic replay
  - same key + different payload => `409`
  - in-progress same key => `409`
  - failed same key => `409` (requires new key for retry)

## `PATCH /api/v1/memory/{node_id}`

- safe mutable fields only:
  - `kind`
  - `level`
  - `residual`
  - `anchor`
  - `opp_signature`
- optimistic update guard via `expected_updated_at`
- conflict returns `409`

## Security and Authz

All routes are scope-gated using K3 dependency:

- read routes: `memory.read`
- write/update routes: `memory.write`

Tenant isolation:

- all DB access uses tenant-scoped repos/session context
- node/raw/event lookups require graph scoping where applicable

## Rate Limiting

No breaking changes required in K5.

Existing K3 categories already cover:

- `/api/v1/memory/search` -> query bucket
- `/api/v1/memory/write` -> ingest bucket
- `/api/v1/memory/*` -> memory prefix bucket mapping

## Validation

Executed:

- `python3 -m compileall faim_native tests`
- `PYTHONPATH=faim_native pytest -q tests/unit/test_phase_k5_memory_idempotency.py tests/unit/test_phase_k5_memory_router_contract.py tests/acceptance/test_AT_PK5_memory_api_surface.py tests/acceptance/test_AT_PK5_memory_lifecycle.py tests/acceptance/test_AT_S9_rate_limiting.py tests/unit/test_phase_k4_api_keys_router.py tests/unit/test_phase_k3_auth_enforcement.py`

Result:

- compile passed
- tests passed: `26 passed`

## Notes

- K5 is additive and does not remove/rename existing routes.
- K5 reuses proven ingest/query/storage internals to minimize risk.
- Memory write idempotency is persistent and tenant+graph isolated.
