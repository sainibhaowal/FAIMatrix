# 44 - Profile/Persist Runtime Semantics Plan (Phase R1 Contract Freeze)

Date: 2026-02-20  
Owner: FAIM Native Runtime  
Status: Completed (R1 Contract Freeze)

## Objective

Freeze production semantics for `profile` and `persist_mode` across Storage and Evolution surfaces before runtime implementation (R2+), so behavior is explicit, testable, and non-ambiguous for users/operators.

This document is contract/spec only. It does not change runtime behavior.

## Exact R1 Scope

In scope:

1. Freeze semantics matrix for all six combinations.
2. Define requested vs effective mode contract.
3. Define additive API/event contract requirements for later phases.
4. Define verification gates and rollout safety constraints.

Out of scope:

1. Runtime algorithm changes.
2. Frontend behavior changes.
3. Database migrations.

## Verified Current State (Baseline)

1. Storage page sends `profile` + `persist_mode`:  
`frontend/src/app/(app)/dashboard/storage/page.tsx`
2. Evolution page sends `profile` + `persist_mode` on manual run:  
`frontend/src/app/(app)/dashboard/evolution/page.tsx`
3. Ingest runtime has partial `profile` effect (strict skips index upsert), while `persist_mode` is mostly metadata today:  
`faim_native/orchestration/ingest_flow.py`
4. Evolve runtime accepts both values but currently mostly logs/records them without full branch semantics:  
`faim_native/orchestration/evolve_flow.py`

## Contract: Requested vs Effective Modes

Backend is authoritative.

1. `requested_profile`: client input.
2. `requested_persist_mode`: client input.
3. `effective_profile`: backend-resolved runtime mode actually applied.
4. `effective_persist_mode`: backend-resolved durability mode actually applied.

Rule:

1. If requested values are allowed by policy, effective == requested.
2. If not allowed, backend coerces to safe default and records coercion reason.
3. UI and logs must surface effective values.

## Frozen Semantics Matrix (Target for R2+)

### Assumed mode meaning

1. `profile`
- `strict`: deterministic/conservative memory shaping.
- `fast`: performance-first with bounded approximations.
- `relaxed`: adaptive/aggressive shaping.
2. `persist_mode`
- `strict`: synchronous durability gates before success response.
- `relaxed`: core truth commit first; secondary work may complete asynchronously.

### Combination matrix

1. `strict + strict`
- Ingest/storage: full validation + synchronous durable completion.
- Evolution: deterministic/conservative actions + strict completion semantics.
- Latency: highest.
- Risk: lowest.

2. `strict + relaxed`
- Ingest/storage: deterministic core truth commit, secondary tasks async.
- Evolution: deterministic actions with async secondary persistence where safe.
- Latency: medium.
- Risk: low.

3. `fast + strict`
- Ingest/storage: optimized processing path with strict completion gate.
- Evolution: faster heuristics with strict completion.
- Latency: medium-high.
- Risk: medium-low.

4. `fast + relaxed`
- Ingest/storage: throughput-first path with async secondary tasks.
- Evolution: faster cycles + async secondary tasks.
- Latency: low.
- Risk: medium.

5. `relaxed + strict`
- Ingest/storage: adaptive/aggressive shaping with strict completion gate.
- Evolution: aggressive evolve/invention with strict completion.
- Latency: medium-high.
- Risk: medium-high.

6. `relaxed + relaxed`
- Ingest/storage: most permissive + eventual completion of secondary work.
- Evolution: most aggressive adaptive behavior.
- Latency: lowest.
- Risk: highest.

## Endpoint Contract Additions (Additive-only)

Future implementation must add response/event clarity without breaking clients.

1. Storage upload/retry/ingest responses include:
- `requested_profile`
- `requested_persist_mode`
- `effective_profile`
- `effective_persist_mode`
- `durability_path` (for example `sync_strict` or `core_sync_secondary_async`)

2. Memory write response includes same fields above.

3. Evolve response includes same fields above.

4. Event payloads for ingest/evolve include same fields above for observability.

## Safety Constraints

1. Additive-only API contract updates in R2+.
2. Default behavior must remain backward-compatible unless policy flag explicitly changes it.
3. No destructive data/schema operations for this feature set.
4. Tenant isolation and authz behavior must remain unchanged.
5. No plaintext secret/key logging.

## R1 Acceptance Criteria

R1 is complete when all are true:

1. Semantics matrix for 6 combinations is frozen and documented.
2. Requested vs effective mode contract is documented.
3. Additive endpoint/event contract requirements are documented.
4. Safety constraints and rollout gates are documented.
5. No runtime/frontend/db code changed.

## R2+ Implementation Queue (Reference)

1. Central policy resolver module for mode resolution.
2. Ingest/storage runtime semantics realization.
3. Evolve runtime semantics realization.
4. UI effective-mode alignment.
5. Unit/acceptance/regression matrix tests.
6. Release hygiene docs + rollout checklist.

## Outcome

R1 is complete:

- the semantics contract is frozen,
- requested vs effective mode behavior is defined,
- R2+ implementation phases already carry the runtime work forward.

## Production Defaults (Frozen Recommendation)

1. Consumer SaaS default: `strict + relaxed`
2. High-assurance/regulated: `strict + strict`
3. Internal high-throughput operations: `fast + relaxed`
