# 31 - Phase S2 Self-Evolution Scheduler State Report

Date: 2026-02-17

## Scope

Implement Phase S2 only (migration-first):

1. Add durable self-evolution scheduler state table.
2. Add repository for due-graph selection and idempotent state updates.
3. Keep schema additive and avoid runtime behavior switch in this phase.

## Implemented

1. Migration added:
- `faim_native/store/pg/migrations/0010_self_evolution_state.sql`

2. Canonical schema updated:
- `faim_native/store/pg/schema.sql`

3. ORM model added:
- `SelfEvolutionStateModel` in `faim_native/store/pg/models_faim.py`

4. Repository added:
- `faim_native/store/pg/repos/self_evolution_state_repo.py`
- exported via `faim_native/store/pg/repos/__init__.py`

## Self-Evolution State Contract

Table: `self_evolution_state`

- `tenant_id` (PK part)
- `graph_id` (PK part)
- `last_seen_version` (BIGINT, default 0)
- `last_evolved_version` (BIGINT, default 0)
- `last_evolved_at` (TIMESTAMPTZ, nullable)
- `last_enqueued_job_id` (UUID, nullable)
- `updated_at` (TIMESTAMPTZ, default NOW)

Indexes:

- `idx_self_evolution_state_updated`
- `idx_self_evolution_state_due`

## Repository Surface

Added methods:

1. `get(graph_id)`
2. `get_or_create(graph_id)`
3. `mark_seen_version(graph_id, seen_version)` (monotonic)
4. `mark_enqueued(graph_id, job_id, seen_version=None)` (idempotent)
5. `mark_evolved(graph_id, evolved_version, evolved_at=None)` (monotonic)
6. `select_due_graphs(...)`

Due-graph selection semantics:

- requires `current_version - last_evolved_version >= min_version_delta`
- enforces `min_interval_seconds` since `last_evolved_at` (if present)
- excludes graphs with active evolve jobs (`pending` / `running`)
- tenant isolated
- deterministic ordering

## Validation

Executed:

```bash
python3 -m compileall faim_native/store/pg faim_native/runtime tests/unit/test_phase_s2_self_evolution_state_repo.py
PYTHONPATH=.:faim_native pytest -q \
  tests/unit/test_phase_s2_self_evolution_state_repo.py \
  tests/unit/test_phase_s1_self_evolve_flags.py \
  tests/unit/test_phase_a_feature_flags.py \
  tests/unit/test_phase_j_self_invention_flags.py
```

Result:

- compile succeeded
- `22 passed` in targeted unit suites

## Safety Notes

1. Additive-only schema/model changes; no destructive migration.
2. No encryption/auth policy changes in S2.
3. No runtime self-evolve trigger behavior switch in S2.

## Files Changed

- `faim_native/store/pg/migrations/0010_self_evolution_state.sql`
- `faim_native/store/pg/schema.sql`
- `faim_native/store/pg/models_faim.py`
- `faim_native/store/pg/repos/self_evolution_state_repo.py`
- `faim_native/store/pg/repos/__init__.py`
- `tests/unit/test_phase_s2_self_evolution_state_repo.py`
- `faim_native/Docs/README.md`
- `faim_native/Docs/07_STORAGE_GAP_ANALYSIS_AND_EXECUTION_BACKLOG.md`
- `faim_native/Docs/31_PHASE_S2_SELF_EVOLUTION_STATE_REPORT.md`

