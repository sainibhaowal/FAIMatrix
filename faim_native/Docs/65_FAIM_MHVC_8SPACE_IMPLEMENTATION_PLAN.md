# FAIM-MHVC 8-Space Implementation Plan

Status: planning only
Scope: additive FAIM-native 8-space hypervector layer, baseline FAIM remains default and untouched unless feature-flagged

## 1. Decision

We will build a new FAIM-native hypervector layer with **8 spaces** from the start.

No compromise on the space count.

The 8 spaces are:
- identity
- semantic
- temporal
- provenance
- conflict
- inheritance
- policy
- usage

The existing FAIM system stays intact:
- current `v_native` stays 256-d and compatible
- current graph, auth, tenant isolation, and event contracts stay stable
- the new layer is additive and opt-in

## 2. What To Do

Build a new hypervector packet layer that sits beside the existing FAIM memory atom and stores a coordinated 8-space representation per node.

What this layer must provide:
- deterministic packet generation
- typed space registry
- bind / bundle / permute operators
- opposition and conflict operators
- inheritance-aware compression
- policy and usage-aware recall
- explainable retrieval reasons per space
- safe opt-in enterprise/premium activation

## 3. Why To Do It

The current FAIM engine already has deterministic memory, graph lineage, antisymmetry, semantic typing, multi-signal reranking, and evolution diagnostics.

The new layer is needed to:
- increase representational capacity without replacing the baseline
- reduce noise with explicit typed spaces
- separate current truth from historical truth
- make conflict first-class rather than implicit
- enable premium users to get stronger memory behavior without breaking normal users
- create a research contribution that is FAIM-native, not a relabeled HDC clone

## 4. Design Principle

The new layer must be:
- additive
- deterministic
- auditable
- tenant-safe
- rollback-safe
- benchmarkable
- explainable

It must not become a second isolated system.
It must be a second layer inside the same FAIM graph and tenant model.

## 5. Current System Boundary

The plan must respect these existing code paths:

- `faim_native/encoding/vector_schema.py`
- `faim_native/encoding/text_vectorizer.py`
- `faim_native/encoding/representation_v2.py`
- `faim_native/core/engine_native.py`
- `faim_native/core/operators/inheritance.py`
- `faim_native/core/antisym.py`
- `faim_native/core/operators/semantic_typing.py`
- `faim_native/core/query/query_engine.py`
- `faim_native/core/query/graph_semantics.py`
- `faim_native/core/dynamics/evolution_native.py`
- `faim_native/orchestration/ingest_flow.py`
- `faim_native/orchestration/query_flow.py`
- `faim_native/store/pg/models_faim.py`
- `faim_native/store/pg/repos/representation_repo.py`
- `faim_native/store/pg/migrations/0012_representation_v2.sql`

The new layer should attach at those boundaries, not replace them.

## 6. Proposed New Files

The following files are planned, not yet implemented:

- `faim_native/hv/__init__.py`
- `faim_native/hv/schema.py`
- `faim_native/hv/spaces.py`
- `faim_native/hv/seed.py`
- `faim_native/hv/generator.py`
- `faim_native/hv/operators.py`
- `faim_native/hv/packet.py`
- `faim_native/hv/recall.py`
- `faim_native/hv/compat.py`
- `faim_native/store/pg/models_hv.py`
- `faim_native/store/pg/repos/hv_packet_repo.py`
- `faim_native/store/pg/migrations/0023_hv_packet.sql`
- `tests/unit/test_hv_schema.py`
- `tests/unit/test_hv_seed.py`
- `tests/unit/test_hv_operators.py`
- `tests/unit/test_hv_packet.py`
- `tests/unit/test_hv_recall.py`
- `tests/acceptance/test_AT_HV_profile_switch.py`
- `tests/acceptance/test_AT_HV_no_regression.py`

## 7. Proposed Config Flags

The new layer should be gated behind explicit config, defaulting to off.

Planned flags:
- `FAIM_HV_ENABLED`
- `FAIM_HV_SHADOW_MODE`
- `FAIM_HV_ENTERPRISE_ONLY`
- `FAIM_HV_PACKET_SPACES=8`
- `FAIM_HV_SPACE_WIDTH`
- `FAIM_HV_BINDING_MODE`
- `FAIM_HV_RECALL_MODE`
- `FAIM_HV_ROLLOUT_ALLOWLIST`

The plan should avoid any new public behavior unless the flag is enabled.

## 8. Eight-Space Model

### 8.1 Identity

Purpose:
- stable memory identity
- deterministic seed namespace
- replayable object binding

Source in FAIM:
- `node_id`
- `raw_id`
- `block_id`

### 8.2 Semantic

Purpose:
- topic and meaning
- concept overlap
- query relevance

Source in FAIM:
- native vector
- Representation V2
- semantic edges

### 8.3 Temporal

Purpose:
- current vs historical truth
- recency
- event order

Source in FAIM:
- `created_at`
- `last_access`
- event journal
- evolution state

### 8.4 Provenance

Purpose:
- source traceability
- confidence context
- anchor and extractor lineage

Source in FAIM:
- `RawRef`
- `EvidenceBlock`
- `anchor`
- `provenance`

### 8.5 Conflict

Purpose:
- opposition and contradiction handling
- suppression and dominance
- historical preservation

Source in FAIM:
- `antisym.py`
- opposition edges
- contradiction notes

### 8.6 Inheritance

Purpose:
- lineage tree encoding
- parent-child compression
- residual novelty control

Source in FAIM:
- `core/operators/inheritance.py`
- inheritance edges
- semantic parent metadata

### 8.7 Policy

Purpose:
- tenant or enterprise rules
- visibility and access constraints
- memory routing policy

Source in FAIM:
- auth context
- profile/persist runtime policy
- feature flags

### 8.8 Usage

Purpose:
- touch count
- access decay
- recall bias

Source in FAIM:
- `touch_count`
- `last_access`
- query updates

## 9. Implementation Phases

### Phase 0: Baseline Freeze and Inventory

What to do:
- confirm current FAIM behavior
- confirm the 8-space decision
- map exact touchpoints
- freeze baseline tests

Why:
- prevent accidental scope drift
- make sure the new layer does not mutate the current engine by mistake

Where:
- docs:
  - `faim_native/Docs/64_FAIM_MHVC_Research_Paper.md`
  - `faim_native/Docs/README.md`
- code inventory:
  - the current core, encoding, storage, orchestration, and query files listed above

How:
- document the new layer as additive only
- define the packet schema before any code is touched
- lock the default path to baseline FAIM

Must not break:
- current query results
- ingest determinism
- graph versioning
- tenant isolation

### Phase 1: Packet Schema and Sidecar Storage

What to do:
- define the HV packet schema
- add a sidecar storage model for the packet
- add a migration for packet persistence
- keep the 256-d baseline vector untouched

Why:
- one node, multiple representations
- avoid changing the canonical vector contract

Where:
- new package:
  - `faim_native/hv/schema.py`
  - `faim_native/hv/packet.py`
  - `faim_native/hv/spaces.py`
- storage:
  - `faim_native/store/pg/models_hv.py`
  - `faim_native/store/pg/migrations/0023_hv_packet.sql`
- repository:
  - `faim_native/store/pg/repos/hv_packet_repo.py` if needed

How:
- store packet by `node_id`, `tenant_id`, and `graph_id`
- preserve idempotent upsert semantics
- keep the packet sidecar additive, never destructive

Must not break:
- `NodeModel`
- `RepresentationV2`
- `packet_hash`
- raw storage
- event journal

### Phase 2: Deterministic HV Operators

What to do:
- implement seed derivation
- implement `bind`, `bundle`, `permute`, `oppose`, `inherit`, `decay`, `sleep`, `revive`
- define stable tie-breaking and bounded normalization

Why:
- this is the mathematical core of the new layer
- it must be deterministic and replayable

Where:
- `faim_native/hv/seed.py`
- `faim_native/hv/generator.py`
- `faim_native/hv/operators.py`
- `faim_native/core/invariants.py` if shared checks are needed

How:
- derive all space vectors from stable seed material
- keep operators pure and side-effect free
- require bounded norms and fixed ordering

Must not break:
- `FAIMVector` hash semantics
- query determinism
- merge idempotence

### Phase 3: Ingest Integration

What to do:
- dual-write the HV packet at ingest time
- preserve existing node write path
- keep baseline and new layer keyed to the same node

Why:
- the new layer must not create duplicate graphs or duplicate memory identities

Where:
- `faim_native/orchestration/ingest_flow.py`
- `faim_native/core/engine_native.py`
- `faim_native/encoding/representation_v2.py` if packet hydration reuses its sidecar path

How:
- baseline `v_native` write stays as-is
- packet sidecar write happens after canonical node upsert
- if the HV layer is disabled, ingest behaves exactly as today

Must not break:
- ingest idempotency
- deduplication
- node ordering
- event emission

### Phase 4: Query Integration

What to do:
- add HV packet scoring to query shortlist and rerank
- preserve current query flow as fallback
- expose explainable reasons per space

Why:
- this is where enterprise users should feel the power of the layer
- the system should stay explainable, not opaque

Where:
- `faim_native/orchestration/query_flow.py`
- `faim_native/core/query/query_engine.py`
- `faim_native/core/query/graph_semantics.py`
- `faim_native/index/*` if a shortlist needs to be packet-aware
- `faim_native/encoding/representation_v2.py` for compatibility fusion

How:
- score packet-space similarity separately
- combine space scores with deterministic weights
- keep baseline candidate generation as a fallback path

Must not break:
- current query API shape
- deterministic ranking order on ties
- tenant-safe recall
- existing explain payloads

### Phase 5: Evolution and Pruning Integration

What to do:
- feed packet diagnostics into evolve
- make prune and merge policies space-aware
- keep current evolution engine stable

Why:
- the new layer should improve lifecycle control, not destabilize it

Where:
- `faim_native/core/dynamics/evolution_native.py`
- `faim_native/core/operators/prune.py`
- `faim_native/core/antisym.py`
- `faim_native/core/invariants.py`

How:
- compute packet-level redundancy and novelty signals
- keep hard safety thresholds
- emit diagnostics before any destructive action

Must not break:
- graph versioning
- evolution job flow
- self-invention gating
- prune safety

### Phase 6: Premium / Enterprise Control Surface

What to do:
- add a profile or control-plane way to enable the new layer
- expose baseline vs premium mode to trusted users
- keep normal users on baseline FAIM

Why:
- enterprises need controlled rollout and clear operating modes

Where:
- frontend:
  - `frontend/src/app/(app)/dashboard/control-plane/page.tsx`
  - `frontend/src/components/storage/ControlPlanePanel.tsx`
  - `frontend/src/components/admin/AdminControlPlane.tsx`
  - `frontend/src/app/(app)/dashboard/profile/page.tsx`
- backend:
  - existing auth and profile/persist runtime paths

How:
- use feature flags and profile policy
- avoid a new public API surface unless needed

Must not break:
- current frontend behavior
- auth flows
- tenant isolation
- control plane safety

### Phase 7: Benchmarking and Validation

What to do:
- compare baseline FAIM vs FAIM-HV
- compare both against HDC/VSA baselines
- run determinism and regression tests

Why:
- this is the only way to justify the new layer

Where:
- `faim_native/benchmarks/*`
- `tests/unit/*`
- `tests/acceptance/*`
- `tests/security/*`
- `docs/Benchmarks_Publication/BENCHMARK_SPEC.md`

How:
- same dataset
- same seed
- same top-k
- same compute budget
- same metric code

Must not break:
- existing acceptance suite
- security suite
- production readiness checks

## 10. Exact Files And Surfaces To Watch

### Backend files

- `faim_native/api/app.py`
- `faim_native/api/routers/*`
- `faim_native/api/middleware/*`
- `faim_native/orchestration/ingest_flow.py`
- `faim_native/orchestration/query_flow.py`
- `faim_native/orchestration/evolve_flow.py`
- `faim_native/core/engine_native.py`
- `faim_native/core/query/query_engine.py`
- `faim_native/core/query/graph_semantics.py`
- `faim_native/core/dynamics/evolution_native.py`
- `faim_native/store/pg/models_faim.py`
- `faim_native/store/pg/repos/*`
- `faim_native/store/pg/migrations/*`

### Frontend files

- `frontend/src/app/(app)/dashboard/control-plane/page.tsx`
- `frontend/src/app/(app)/dashboard/profile/page.tsx`
- `frontend/src/components/storage/ControlPlanePanel.tsx`
- `frontend/src/components/admin/AdminControlPlane.tsx`
- `frontend/src/contexts/UserContext.tsx`
- `frontend/src/types/api.ts`

### Tests

- `tests/unit/*`
- `tests/acceptance/*`
- `tests/security/*`
- new HV-specific tests listed above

### Docs

- `faim_native/Docs/64_FAIM_MHVC_Research_Paper.md`
- `faim_native/Docs/65_FAIM_MHVC_8SPACE_IMPLEMENTATION_PLAN.md`
- `faim_native/Docs/66_FAIM_MHVC_8SPACE_VALIDATION_AND_ROLLOUT.md`
- `faim_native/Docs/README.md`
- `docs/Benchmarks_Publication/BENCHMARK_SPEC.md`

## 11. Safety Rules

The plan must preserve:
- existing code structure
- existing integrations and connections
- auth and tenant isolation
- security, encryption, and cryptography-related safety
- backend and frontend behavior
- workflows, APIs, jobs, storage, memory, evolution, and events

The plan must avoid:
- replacing the current engine
- changing the default behavior without a flag
- creating a second graph identity
- relaxing tenant boundaries
- inventing benchmark claims

## 12. Acceptance Gates

The new layer is not ready until all of these are true:
- baseline FAIM tests still pass
- HV unit tests pass
- HV acceptance tests pass
- security tests still pass
- no tenant leakage
- no API contract breakage
- no frontend regression
- benchmark evidence exists for any claimed improvement

## 13. Implementation Order

The safe order is:
1. freeze and inventory
2. schema and storage
3. operators and packet generation
4. ingest integration
5. query integration
6. evolution and pruning integration
7. enterprise/premium toggle
8. benchmark and rollback validation

## 14. Final Rule

The space count is fixed at 8.
The baseline FAIM contract stays untouched.
The new layer is additive, deterministic, and production-safe.
