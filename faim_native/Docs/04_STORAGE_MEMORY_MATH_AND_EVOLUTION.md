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
- Representation V2 sidecars (sparse lexical-semantic channels)
- canonical semantics sidecars (graph-local lexicon + corpus term stats)
- graph edges (structural)
- provenance metadata (traceability)

Agents should consume ranked nodes + explain payload + raw provenance references.

## 9) Determinism Guarantees (Design Intent)

Current code strongly favors deterministic behavior:

- canonical sorting before hashing
- stable tie-breaking for merges and ranking
- fixed vector dimension and normalization rules
- additive sidecars that do not mutate the canonical 256-d vector contract
- explicit invariant checks for boundedness/fractions

## 10) Practical Notes for Storage Setup

When implementing full Storage page/backend:

- preserve determinism in async/batch ingestion
- keep raw immutable truth separate from derived graph/index data
- keep Representation V2 as additive sidecar data; never repurpose `v_native`
- for older graphs, rebuild Representation V2 from raw truth via the storage backfill route instead of mutating node vectors
- keep canonical semantics additive and graph-scoped; rebuild through the storage canonical-semantics route instead of mutating node vectors or raw truth
- treat Qdrant and Redis as accelerators only
- keep provenance (`raw_id`, `block_id`, `anchor`) first-class in all API responses

## 11) Self-Default Runtime Status (S7 Reconciliation)

As of 2026-02-17, self-evolution is production-routed by default contract when enabled via runtime flags and jobs:

- shared due-enqueue trigger is wired for storage upload, ingest, and memory write paths
- worker autonomous due-scan fallback is available for periodic/hybrid trigger modes
- evolve/invention decisioning is config/orchestration driven (no direct env reads in evolve core)
- practical prune default is aligned with real node touch lifecycle (`max_touch_count <= 1`)
- explicit skip observability exists through `EVOLUTION_SKIPPED` reasons

This means self behavior is now runtime-governed and deterministic, while keeping write-path latency non-blocking via async scheduling.

## 12) Profile/Persist Runtime Semantics (R8 Reconciliation)

As of 2026-02-20, profile/persist behavior is implemented end-to-end for storage ingest and evolve orchestration through a shared resolver:

- resolver: `orchestration/profile_persist_policy.py`
- ingest/runtime application: `orchestration/ingest_flow.py`
- evolve/runtime application: `orchestration/evolve_flow.py`

Operational model:

1. Client sends requested values (`profile`, `persist_mode`).
2. Backend resolves authoritative effective values.
3. Runtime executes using effective policy knobs.
4. API responses/events expose both requested and effective values plus `durability_path`.

Additive observability fields:

- `requested_profile`
- `requested_persist_mode`
- `effective_profile`
- `effective_persist_mode`
- `durability_path`

Compatibility control:

- `FAIM_PROFILE_PERSIST_COMPAT_MODE=true` keeps legacy-safe behavior envelope during rollout.
- `FAIM_PROFILE_PERSIST_COMPAT_MODE=false` enables fully differentiated profile/persist runtime semantics.

Evolution-specific notes:

- profile controls action-budget and aggressiveness knobs (merge/prune/invention settings).
- persist mode controls completion semantics:
  - `strict`: state durability update is required before successful completion.
  - `relaxed`: core evolve completion is committed first; state update is best-effort.

Storage/ingest-specific notes:

- `strict` profile keeps deterministic/conservative ingest behavior and may skip acceleration paths.
- `persist_mode=strict` enforces synchronous secondary durability where required.
- `persist_mode=relaxed` allows secondary work to complete asynchronously (with safe fallback when jobs are unavailable).

## 13) Evolution Dashboard Runtime Alignment (2026-02-20)

Observed runtime mismatch that affected dashboard visibility (not core graph truth):

1. `DIAGNOSTICS_SNAPSHOT` events are emitted with flat fields (`D_hat`, `H_hat`, `lambda_hat`, `redundancy_R`, `novelty_N`, `energy_E`).
2. `/api/v1/metrics/scorecard` previously read nested-only keys (`payload.metrics.*`), which produced `-` in dashboard metric cards.

Resolution applied:

1. Metrics router now supports both payload shapes (nested + flat) with backward-compatible fallback mapping.
2. `graph_hash` now falls back to `diagnostics_hash` when `graph_hash` is absent in event payload.

Operational UX alignment:

1. Evolution page graph switching is now feature-flagged for operator mode (`NEXT_PUBLIC_FAIM_ENABLE_GRAPH_SWITCH=true`).
2. Default user mode is session-bound single-graph behavior (no manual graph switching control required).
3. Timeline layout and scheduler reason presentation were adjusted for clearer runtime interpretation.
4. Source coverage section now surfaces ingested file evidence (count/status/node/vector) for the active graph.

## 14) Phase 3 Graph Semantics and Diffusion

Phase 3 extends FAIM query-time graph reasoning without changing `v_native`, raw truth, or core write semantics.

Implemented behavior:

- bounded multi-hop graph traversal from deterministic seed nodes
- additive graph path scoring with hop decay
- fixed-step diffusion with deterministic ordering
- concept neighborhood support scoring
- contradiction-aware suppression using `opposition` edges and node timestamps
- additive explain payload fields for Phase 3 graph paths and graph score components

Safety properties:

- all traversal is tenant-scoped and graph-scoped
- hop depth and fanout are bounded
- traversal order and tie-breaking are deterministic
- graph-derived score is additive and bounded; it does not replace FAIM base scoring
- opposition edges are used as contradiction signals, not expansion edges

Operational note:

- no frontend changes are required for correctness
- richer Phase 3 explain/debug rendering can be added later without backend contract breakage

## 15) Phase 4 Deterministic Reranker V2

Phase 4 strengthens reranking without introducing learned models.

Implemented behavior:

- deterministic proposition extraction from normalized lexical text
- additive evidence span scoring
- additive entity/time/proposition score fusion
- bounded pairwise dominance suppression for duplicate/conflicting candidates
- additive explain payload fields for Phase 4 reranker reasoning

Safety properties:

- query-time only; no mutation of stored node vectors or graph truth
- deterministic tie-breaking and suppression ordering
- proposition logic uses bounded rule-based extraction only
- suppression is shortlist-bounded and additive to existing opposition logic

Operational note:

- no frontend changes are required for correctness
- richer explain/debug rendering can be added later from existing response payloads

## 16) Phase 5 Scale and Deterministic ANN

Phase 5 adds a deterministic acceleration layer ahead of graph expansion and reranking.

Implemented behavior:

- sparse inverted index over Representation V2 sidecars
- deterministic WAND-style sparse shortlist pruning
- deterministic VP-tree dense shortlist for native vectors
- stable union of sparse and dense candidates before existing graph semantics/reranking
- additive metrics for sparse and dense candidate counts

Safety properties:

- acceleration only; graph truth and `v_native` remain canonical
- feature-gated by `FAIM_PHASE5_ENABLED`
- existing recall path remains intact as fallback
- stable ordering by `(-score, node_id)` at every stage
- tenant and graph scoping preserved through repo-backed artifact building

Operational note:

- no frontend changes are required for correctness
- optional UI work later can expose retrieval-stage counts or phase-5 diagnostics

## 17) Phase 6 Multilingual and Cross-Lingual

Phase 6 adds deterministic English/German cross-lingual expansion without introducing embeddings or learned models.

Implemented behavior:

- Unicode normalization and German transliteration
- light German stemming plus existing English stemming
- checked-in EN/DE bilingual lexicon
- graph-scoped multilingual lexicon table
- concept nodes stored in the existing node graph
- additive `concept_surface` and `translation` edges
- query-time multilingual canonical expansion
- explicit rebuild route for existing graphs

Safety properties:

- additive only; existing atom vectors are unchanged
- multilingual graph state is tenant-scoped and graph-scoped
- no runtime network or cloud dependency
- no destructive multilingual merge/prune behavior
- existing query and graph routes remain backward compatible

Operational note:

- no frontend changes are required for correctness
- multilingual explain/debug rendering can be added later from existing graph edges and storage rebuild status

## 18) Phase 7 Multimodal Without ML

Phase 7 adds deterministic multimodal indexing and optional Docling-backed extraction without changing FAIM core graph truth.

Implemented behavior:

- additive multimodal sidecar keyed by node
- deterministic OCR/table/layout/file-metadata feature extraction
- deterministic image hash proxy
- optional Docling extractor path behind `FAIM_DOCLING_ENABLED`
- explicit multimodal rebuild route for existing graphs
- additive modality score in query reranking

Safety properties:

- sidecar only; existing vectors and edges remain canonical
- Docling is optional and falls back to the current extractor stack
- modality score is bounded and additive
- storage/query/frontend contracts remain backward compatible

Operational note:

- no frontend changes are required for correctness
- later UI work can expose multimodal evidence or rebuild status from existing backend payloads

## Phase 8

Phase 8 adds deterministic long-tail knowledge coverage and domain adaptation without introducing learned retrieval models.

Current implementation includes:

- graph-scoped domain lexicon table
- graph-scoped offline KB source registry
- offline KB import route
- explicit domain-profile rebuild route
- additive `entity`, `relation`, `fact`, `value`, and `time` nodes
- additive domain knowledge edges such as `entity_relation`, `fact_value`, and `fact_time`
- deterministic query-time entity linking and bounded domain scoring

Safety constraints:

- additive only
- tenant-scoped and graph-scoped only
- no mutation of `v_native`
- no destructive merge or prune logic
- bounded domain contribution inside reranking
