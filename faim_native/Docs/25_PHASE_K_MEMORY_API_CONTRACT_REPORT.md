# 25 - Phase K Memory API Contract + Runtime Consolidated Report

## Date

2026-02-14

## Scope

Consolidated implementation record for agent-facing memory contract and runtime
delivery across K1-K8 documentation reconciliation.

## Implemented End-to-End

## 1) Contract and Route Surface

Additive memory contract is implemented under `/api/v1/memory`:

- `POST /api/v1/memory/search`
- `GET /api/v1/memory/{node_id}`
- `GET /api/v1/memory/{node_id}/provenance`
- `POST /api/v1/memory/write`
- `PATCH /api/v1/memory/{node_id}`

## 2) Runtime Behavior

- search path reuses FAIM query flow/rerank pipeline
- write path reuses ingest/raw persistence/validator pipeline
- provenance path reuses storage/node/event linkage patterns
- update path supports safe mutable fields only

## 3) Safety and Consistency Controls

- idempotency ledger for memory writes (`0009_memory_write_idempotency.sql`)
- deterministic replay for same idempotency key + same payload
- conflict protection for same key + different payload (`409`)
- optimistic update guard via `expected_updated_at`
- strict tenant + graph scoping on retrieval/write/update paths

## 4) Authz and Security Controls

- read routes guarded by `memory.read`
- write/update routes guarded by `memory.write`
- scope denied path audited (`denied(scope)`)
- key status policy enforced (expired/revoked rejected upstream)
- rate-limit categories include:
  - `memory_search`
  - `memory_read`
  - `memory_write`

## 5) Validation and Stability

Validated in K5-K7 suites:

- route contract tests
- lifecycle acceptance tests (`write -> replay -> search -> fetch -> provenance -> patch`)
- scope matrix tests
- frontend integration where memory behavior intersects API key authz flow

K7 additional runtime stability fix:

- `recency_boost()` now normalizes naive/aware timestamps to UTC before age
  arithmetic to avoid mixed-timezone subtraction failures.

## Source Reports

- `23_API_KEYS_AUTHZ_AND_MEMORY_CONTRACT_PLAN.md`
- `27_PHASE_K5_MEMORY_API_IMPLEMENTATION_REPORT.md`
- `28_PHASE_K6_SECURITY_HARDENING_AUDIT_RATELIMIT_REPORT.md`
- `29_PHASE_K7_VALIDATION_NON_REGRESSION_REPORT.md`

## Remaining Work (Operations, Not Core Runtime Gap)

1. production SLO dashboards and alert thresholds for memory route latency/error
2. extended concurrency/load soak for idempotency ledger under spike scenarios
3. environment rollout governance for strict scope policy and rate-limit tuning
