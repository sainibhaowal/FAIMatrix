# 04 - Memory Math and Evolution Model

This document maps requested FAIM concepts to current implementation.

## 1) Fractal Metrics

Implemented in `core/metrics/fractal_physics.py`.

Primary diagnostics:

- `D_hat`: fractal-dimension estimate from pairwise distance scaling
- `H_hat`: normalized entropy of similarity distribution
- `R`: redundancy ratio
- `N`: novelty from residual mean
- `lambda_hat`: evolution pressure
- `E`: energy/boundedness

Conceptual role:

- measures graph complexity/disorder/novelty
- guides adaptive evolution thresholds

## 2) Inheritance

Implemented in `core/operators/inheritance.py` and used by engine write path.

For each new node:

1. choose top-k parent candidates by cosine similarity
2. normalize similarities into parent fractions (`sum = 1`)
3. compute residual novelty as `1 - cosine(child, inherited_mix)`

This encodes semantic lineage and novelty in graph structure.

## 3) Antisymmetric / Opposition Logic

Implemented in `core/antisym.py` and called during ingest/evolution.

- opposition score uses cosine-like similarity as redundancy proxy
- merge occurs above threshold
- deterministic winner selection by hash/id tie-break
- opposition edge is persisted to graph

Requested term mapping:

- "antisymeetric" -> antisymmetric merge/cancel operator
- "opposition" -> explicit edge relation in `edges.kind = opposition`

## 4) Pruning

Implemented in `core/operators/prune.py`, used by evolution.

A node can be pruned only if all are true:

- old enough
- low usage (`touch_count`, default policy now allows pruning at `touch_count <= 1`)
- high redundancy similarity
- optional macro protection policy

Goal: reduce stale redundant memory while preserving raw truth doctrine.

## 5) Deduplication

Logical dedup key is packet hash (`packet_hash`).

- packet hash computed from deterministic canonical blocks
- table `ingest_dedup` exists for replay-safe idempotency

Current status:

- ingest API/runtime path activates session-based dedup flow
- dedup hits return stable `dedup_hit` status and do not duplicate graph writes

## 6) Self-Evolving

Implemented in `core/dynamics/evolution_native.py` and orchestrated by `orchestration/evolve_flow.py`.

Cycle behavior:

1. compute diagnostics
2. adapt merge/prune thresholds
3. merge redundant pairs
4. prune safe low-value nodes
5. bump graph version
6. emit evolution events

Observability behavior:

- emits `DIAGNOSTICS_SNAPSHOT` for each evolve cycle
- emits `EVOLUTION_COMPLETE` when actions are applied
- emits `EVOLUTION_SKIPPED` with explicit reason when no action is applied
  - `insufficient_nodes`
  - `no_actions_after_evaluation`

## 7) Self-Inventing (Macro Invention)

Implemented in `core/dynamics/invention_native.py` and now wired into live evolve runtime.

Logic:

- detect repeated co-activation sets from events
- require minimum lambda and coactivation count
- estimate redundancy reduction benefit
- create macro node as normalized mean of member vectors
- connect member inheritance edges to macro

Runtime notes:

- self-inventing runs during evolve cycles when:
  - `FAIM_SELF_INVENT_ENABLED=true`
  - `FAIM_SELF_INVENT_ON_EVOLVE=true`
- evolve core invention gating is config/orchestration driven (no direct env reads inside evolve core)
- processing is incremental and bounded using persisted state (`self_invention_state` table)
- post-upload evolve enqueue is optional with:
  - `FAIM_SELF_INVENT_AFTER_UPLOAD=true`

This is the current "self inventing" mechanism in live runtime, not only a library module.

## 8) Data Forms Used by AI and Agents

FAIM operates across these memory forms:

- text evidence blocks (symbolic)
- vector atoms/macros (numeric 256-dim)
- graph edges (structural)
- provenance metadata (traceability)

Agents should consume ranked nodes + explain payload + raw provenance references.

## 9) Determinism Guarantees (Design Intent)

Current code strongly favors deterministic behavior:

- canonical sorting before hashing
- stable tie-breaking for merges and ranking
- fixed vector dimension and normalization rules
- explicit invariant checks for boundedness/fractions

## 10) Practical Notes for Storage Setup

When implementing full Storage page/backend:

- preserve determinism in async/batch ingestion
- keep raw immutable truth separate from derived graph/index data
- treat Qdrant and Redis as accelerators only
- keep provenance (`raw_id`, `block_id`, `anchor`) first-class in all API responses
