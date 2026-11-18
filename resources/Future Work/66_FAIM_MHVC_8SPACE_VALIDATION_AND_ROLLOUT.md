# FAIM-MHVC 8-Space Validation and Rollout Matrix

Status: planning only
Scope: validation gates, regression matrix, rollout safety for the 8-space FAIM-MHVC layer

## 1. Purpose

This document is the companion to the implementation plan.

It answers:
- what must be verified
- what must not break
- how to roll out safely
- how to roll back if a gate fails

## 2. Validation Principles

Every check must preserve:
- determinism
- tenant isolation
- auth safety
- storage integrity
- event ordering
- frontend compatibility
- baseline query behavior

No validation step may depend on fabricated benchmark numbers.

## 3. Validation Matrix

| Area | What to verify | Current files to compare against | New files to add | Failure condition |
| --- | --- | --- | --- | --- |
| HV schema | 8 spaces exist and are deterministic | `faim_native/encoding/vector_schema.py`, `faim_native/encoding/representation_v2.py` | `faim_native/hv/schema.py`, `faim_native/hv/packet.py` | fewer than 8 spaces, unstable seed, or nondeterministic packet hash |
| HV operators | bind/bundle/permute/oppose/inherit/decay/sleep/revive are pure and bounded | `faim_native/core/antisym.py`, `faim_native/core/operators/inheritance.py` | `faim_native/hv/operators.py` | operator output changes across repeated runs or violates bounds |
| Ingest integration | one node, multiple representations | `faim_native/orchestration/ingest_flow.py`, `faim_native/core/engine_native.py` | HV write path and sidecar repo | duplicate graph identities, duplicate node semantics, or missing sidecar writes |
| Query integration | baseline remains default; HV is opt-in | `faim_native/orchestration/query_flow.py`, `faim_native/core/query/query_engine.py` | HV scoring and recall path | baseline ranking changes when HV is disabled |
| Evolution integration | merge/prune safety is preserved | `faim_native/core/dynamics/evolution_native.py`, `faim_native/core/invariants.py` | HV diagnostics hooks | evolution becomes unstable, non-deterministic, or over-prunes |
| Storage | node, packet, and sidecar persistence remain tenant-safe | `faim_native/store/pg/models_faim.py`, `faim_native/store/pg/repos/representation_repo.py` | `faim_native/store/pg/models_hv.py` | cross-tenant access or schema corruption |
| Frontend | premium toggle is visible but non-disruptive | `frontend/src/app/(app)/dashboard/profile/page.tsx` | profile UX | default UX changes unexpectedly or breaks on mobile/desktop |
| Security | auth, encryption, and rate limits remain intact | `faim_native/api/middleware/*`, `tests/security/*` | none or minimal admin hooks | any auth bypass, tenant leak, or crypto regression |
| Benchmarks | FAIM vs FAIM-MHVC vs HDC/VSA comparisons are fair | `faim_native/benchmarks/*`, `docs/Benchmarks_Publication/BENCHMARK_SPEC.md` | HV benchmark runner extensions | mismatched dataset, seed, top-k, or compute budget |

## 4. Test Layers

### 4.1 Unit tests

Add unit tests for:
- deterministic seed generation
- packet serialization
- 8-space normalization
- operator idempotence
- bounded norms
- stable ordering
- replay equivalence

Keep existing tests green:
- `tests/unit/test_deterministic_ann.py`
- `tests/unit/test_inheritance_invariants.py`
- `tests/unit/test_antisym_idempotence.py`
- `tests/unit/test_representation_v2_determinism.py`
- `tests/unit/test_evolve_profile_persist_semantics.py`

### 4.2 Acceptance tests

Add acceptance tests for:
- baseline FAIM unchanged when HV is off
- HV enabled for enterprise profile only
- graph results remain tenant-safe
- query explain payloads remain valid
- ingest dedup still works

Keep existing acceptance coverage green:
- ingest idempotency
- query determinism
- no chunking / no ML safety
- profile/persist behavior
- tenant isolation
- graph API surface

### 4.3 Security tests

Must pass unchanged:
- API key hashing
- JWT middleware
- log redaction
- authz enforcement
- tenant isolation

### 4.4 Performance tests

Must measure:
- ingest latency
- query latency p50/p95
- memory footprint
- storage overhead
- graph rebuild cost
- deterministic ANN shortlist cost

## 5. Rollout Matrix

| Rollout stage | Mode | Who gets it | What it does |
| --- | --- | --- | --- |
| Stage 0 | off | everyone | baseline FAIM only |
| Stage 1 | shadow | allowlisted tenants only | compute HV packet sidecar, do not influence results |
| Stage 2 | enterprise-preview | selected paid users | HV affects scoring, baseline still available as fallback |
| Stage 3 | enterprise-default | premium tenants | HV becomes default for eligible tenants, baseline remains switchable |
| Stage 4 | general-availability optional | broad users | feature remains opt-in, not forced |

No stage may disable the baseline path.

## 6. Rollback Rules

Rollback must be possible by:
- turning `FAIM_HV_ENABLED` off
- disabling `FAIM_HV_SHADOW_MODE`
- removing tenant allowlist entries

Rollback must leave:
- existing nodes intact
- existing sidecars readable
- baseline queries unaffected
- existing graph version and event history untouched

## 7. Non-Breaking Guarantees

The following must remain true:
- current `/api/v1/ingest` behavior stays valid
- current `/api/v1/query` behavior stays valid
- current `/api/v1/evolve` behavior stays valid
- current `Representation V2` behavior stays valid
- current auth and tenant boundaries stay valid
- current frontend routes and dashboard pages stay valid

## 8. Files And Surfaces To Watch During Validation

### Backend

- `faim_native/api/app.py`
- `faim_native/api/routers/*`
- `faim_native/api/middleware/*`
- `faim_native/orchestration/ingest_flow.py`
- `faim_native/orchestration/query_flow.py`
- `faim_native/orchestration/evolve_flow.py`
- `faim_native/core/engine_native.py`
- `faim_native/core/query/query_engine.py`
- `faim_native/core/dynamics/evolution_native.py`
- `faim_native/store/pg/models_faim.py`
- `faim_native/store/pg/repos/*`
- `faim_native/store/pg/repos/hv_packet_repo.py`

### Frontend

- `frontend/src/app/(app)/dashboard/profile/page.tsx`
- `frontend/src/contexts/UserContext.tsx`

### Docs

- `faim_native/Docs/64_FAIM_MHVC_Research_Paper.md`
- `faim_native/Docs/65_FAIM_MHVC_8SPACE_IMPLEMENTATION_PLAN.md`
- `faim_native/Docs/66_FAIM_MHVC_8SPACE_VALIDATION_AND_ROLLOUT.md`
- `docs/Benchmarks_Publication/BENCHMARK_SPEC.md`

## 9. Required Benchmark Discipline

To compare FAIM, FAIM-MHVC, and HDC fairly:
- same datasets
- same queries
- same qrels
- same retrieval depth
- same seed
- same metric implementation
- same compute budget

If any of those differ, the result is not a valid comparison.

## 10. Validation Gates

The rollout may proceed only when all gates pass:

1. baseline FAIM regression suite passes
2. HV unit tests pass
3. HV acceptance tests pass
4. security tests pass
5. tenant isolation remains intact
6. query determinism remains intact
7. storage persistence remains intact
8. benchmark protocol is reproducible

## 11. Documentation Gates

Before implementation starts, the docs must state:
- the 8-space decision
- the baseline-preserving rule
- the opt-in enterprise rollout rule
- the benchmark discipline rule

Required docs:
- research paper
- implementation plan
- validation matrix
- benchmark spec update if needed

## 12. Safe Exit Conditions

If a design problem appears in the first implementation phase:
- stop
- preserve the baseline
- revise only the new layer docs
- do not patch around the issue by mutating core FAIM behavior

## 13. Final Rule

The 8-space layer is a premium additive layer, not a replacement.
The baseline system stays healthy.
The validation plan must prove that before any coding begins.
