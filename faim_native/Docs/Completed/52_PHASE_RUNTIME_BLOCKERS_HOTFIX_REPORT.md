# 52 Phase Runtime Blockers Hotfix Report

Date: 2026-02-20

## Scope

This hotfix closes two production blockers discovered during real-world runtime verification:

1. Evolution failures caused by duplicate `opposition` edge inserts.
2. Worker claiming non-executable `storage_upload` jobs and failing them as unknown kind.

## Root Cause

### Blocker A: duplicate opposition edge insert in evolve runtime

- Constraint:
  - `faim_native/store/pg/schema.sql` (`uq_edges_tenant_graph_src_dst_kind`)
- Call path:
  - `faim_native/core/dynamics/evolution_native.py` -> `edge_repo.add_opposition_edge(...)`
- Failure mode:
  - repeated evolve runs attempted to insert the same logical opposition edge again,
    causing `UniqueViolation` on Postgres.

### Blocker B: worker consuming API-managed upload jobs

- Enqueue path:
  - `faim_native/api/routers/storage.py` enqueues `storage_upload` for API progress tracking.
- Worker behavior before fix:
  - `faim_native/orchestration/jobs/worker.py` claimed any pending job kind,
    including `storage_upload`, then failed with `Unknown job kind: storage_upload`.

## Implemented Fixes

### 1) Idempotent opposition edge persistence

Updated:
- `faim_native/store/pg/repos/edge_repo.py`

Behavior after fix:
- Deterministic node ordering retained.
- Postgres path uses conflict-safe upsert keyed by:
  - `(tenant_id, graph_id, src_node_id, dst_node_id, kind)`
- Existing edge is updated in place (weight/meta/timestamp) instead of duplicate insert.
- Non-Postgres fallback updates existing edge if present.

Result:
- repeated evolve cycles no longer fail on duplicate opposition-edge insertion.

### 2) Worker claim filtering by executable kinds

Updated:
- `faim_native/orchestration/jobs/job_store.py`
- `faim_native/orchestration/jobs/worker.py`

Behavior after fix:
- Added filtered claim API:
  - `JobStore.claim_next_of_kinds(...)`
- Worker now claims only executable kinds:
  - `evolve`
  - `ingest_secondary_index`
  - `storage_retention`
- `storage_upload` remains API-managed and is not consumed by worker.

Result:
- no more `Unknown job kind: storage_upload` failures in worker logs.

## Tests Added

New tests:
- `tests/unit/test_edge_repo_opposition_idempotency.py`
- `tests/unit/test_job_store_claim_kind_filter.py`
- `tests/unit/test_worker_executable_kinds.py`
- `tests/acceptance/test_AT_evolve_opposition_edge_idempotency.py`

## Validation Results

Executed and passed:

1. `python3 -m compileall faim_native tests`
2. `PYTHONPATH=.:faim_native pytest -q`
   - `tests/unit/test_edge_repo_opposition_idempotency.py`
   - `tests/unit/test_job_store_claim_kind_filter.py`
   - `tests/unit/test_worker_executable_kinds.py`
   - `tests/acceptance/test_AT_evolve_opposition_edge_idempotency.py`
3. `PYTHONPATH=.:faim_native pytest -q`
   - `tests/unit/test_profile_persist_policy_matrix.py`
   - `tests/unit/test_ingest_profile_persist_semantics.py`
   - `tests/unit/test_evolve_profile_persist_semantics.py`
   - `tests/acceptance/test_AT_profile_persist_storage_matrix.py`
   - `tests/acceptance/test_AT_profile_persist_evolve_matrix.py`
   - `tests/acceptance/test_AT_R5_api_response_clarity.py`
   - `tests/acceptance/test_AT_S6_self_evolve_end_to_end.py`
4. Frontend checks:
   - `cd frontend && npm run typecheck`
   - `cd frontend && npx next lint --file 'src/app/(app)/dashboard/storage/page.tsx' --file 'src/app/(app)/dashboard/evolution/page.tsx'`

## Safety Notes

- Additive-only runtime changes.
- No destructive DB schema changes.
- No auth scope/tenant isolation weakening.
- No encryption/crypto behavior changes.

## Operational Outcome

After this hotfix:

- evolve path is conflict-safe for opposition-edge persistence,
- worker no longer steals API-managed upload jobs,
- storage + profile/persist + evolve matrix remains stable under existing regression gates.
