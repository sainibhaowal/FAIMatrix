# 07 - Storage Gap Analysis and Execution Backlog

This backlog now separates completed delivery from true future enhancements.

## Priority Legend

- P0: blocking correctness/security
- P1: required for complete storage product
- P2: optimization/hardening

## Program Status (as of 2026-02-17)

## Completed Program Scope

1. P0 - Correctness and Contract Alignment: completed
2. P1 - Full Storage Feature Delivery: completed
3. P2 - Security/Performance Hardening: completed
4. Phase A - Contract Freeze and Guardrails: completed
5. Phase B - Backend Completion: completed
6. Phase C - Storage UI Completion: completed
7. Phase D - Production Security Hardening: completed
8. Phase E - Observability + Operations: completed
9. Phase F - Validation and Non-Regression: completed
10. Phase G - Documentation Reconciliation: completed
11. Phase H - Commit and Release Hygiene: completed
12. Phase I - OCR Integration + UI Polish + Supported-Types Surface: completed
13. Phase J - Self-Inventing Runtime Integration: completed
14. Phase K1 - API Keys/Authz + Memory Contract Freeze: completed
15. Phase K2 - Auth Data Model Upgrade (migration-first): completed
16. Phase K3 - Auth Middleware + Authz Enforcement: completed
17. Phase K4 - API Key Management API + Frontend Page: completed
18. Phase K5 - Memory Retrieval/Write API Runtime: completed
19. Phase K6 - Security Hardening + Audit + Rate Limits: completed
20. Phase K7 - Validation and Non-Regression: completed
21. Phase K8 - Documentation + Commits Reconciliation: completed
22. Phase S1 - Self-by-Default Contract + Guardrails: completed
23. Phase S2 - Durable Self-Evolution Scheduler State (migration-first): completed
24. Phase S3 - Centralized Self-Evolve Trigger (single source-of-truth): completed
25. Phase S4 - Worker Autonomous Scheduling Fallback: completed
26. Phase S5 - Evolve/Invention Core Hardening: completed
27. Phase S6 - End-to-End Validation + Non-Regression: completed
28. Phase S7 - Docs + Release Hygiene: completed
29. Phase EV-A - Evolution Dashboard Step A (UI Integration on Existing APIs): completed
30. Phase EV-B - Evolution Dashboard Step B (Runtime Status + Shared Due Evaluation): completed

## Completed Scope Summary

## P0 Completed

- ingest contract hardening and validator enforcement
- raw persistence before orchestration
- dedup runtime/session correctness and raw_id typing alignment
- router/repo contract alignment (node/metrics/admin)
- frontend stream proxy alignment with backend events endpoint

Evidence:

- `08_P0_IMPLEMENTATION_REPORT.md`

## P1 Completed

- storage API surface under `/api/v1/storage/*`
- storage catalog persistence (`storage_files`)
- multi-file upload lifecycle support
- storage UI operational baseline

Evidence:

- `09_P1_IMPLEMENTATION_REPORT.md`

## P2 Completed

- envelope encryption-at-rest integration path
- tenant DEK persistence (`tenant_crypto_keys`)
- cache/index contract alignment
- perf namespace isolation decision

Evidence:

- `10_P2_IMPLEMENTATION_REPORT.md`

## Phase A Completed

- storage contract freeze checks at startup
- feature-flag guardrail validation

Evidence:

- `11_PHASE_A_CONTRACT_FREEZE_REPORT.md`

## Phase B Completed

- provenance API
- upload cancellation model
- lifecycle audit events
- retention execute/enqueue paths with irreversible guardrails

Evidence:

- `12_PHASE_B_BACKEND_COMPLETION_REPORT.md`

## Phase C Completed

- drag-drop + multi-file queue UX
- per-file cancel/retry lifecycle
- upload status/events polling
- provenance drawer integration

Evidence:

- `13_PHASE_C_STORAGE_UI_COMPLETION_REPORT.md`

## Phase D Completed

- production encryption fail-closed enforcement
- plaintext fallback blocked in production profile
- upload abuse rejection paths
- authz/tenant-isolation coverage for storage routes

Evidence:

- `14_PHASE_D_SECURITY_HARDENING_REPORT.md`

## Phase E Completed

- storage ops metrics endpoint
- ingest phase latency instrumentation and aggregation
- structured lifecycle logs with correlation fields
- operations runbook and observability feature flags

Evidence:

- `15_PHASE_E_OBSERVABILITY_OPERATIONS_REPORT.md`
- `16_STORAGE_OPERATIONS_RUNBOOK.md`

## Phase F Completed

- backend unit tests for error/crypto/compat paths
- acceptance lifecycle coverage (upload/retry/cancel/delete/retention/provenance)
- frontend Playwright coverage (queue + provenance)
- retry queue stale-poll race fix

Evidence:

- `17_PHASE_F_VALIDATION_NON_REGRESSION_REPORT.md`

## Phase H Completed

- release-hygiene DoD mapping and explicit deferred ownership
- final verification gate execution before release tagging
- commit/tag release audit trail finalized

Evidence:

- `19_PHASE_H_COMMIT_RELEASE_HYGIENE_REPORT.md`

## Phase I Completed

- OCR service integrated for image uploads and scanned PDF pages (feature-flag controlled)
- storage supported-types API implemented for UI capability visibility
- storage UI includes supported-files panel and rounded corner polish
- OCR dependencies and runtime flags wired into docker/runtime config
- Phase I regression coverage added (unit + acceptance + frontend e2e updates)

Evidence:

- `21_PHASE_I_OCR_UI_POLISH_REPORT.md`

## Phase J Completed

- self-inventing logic wired into live evolve runtime (flag-gated)
- incremental invention cursor/counter state added (`self_invention_state`)
- evolve responses include invention counts
- optional post-upload evolve enqueue path added for storage-triggered invention flow
- Phase J regression coverage added (unit + acceptance)

Evidence:

- `22_PHASE_J_SELF_INVENTING_RUNTIME_INTEGRATION_REPORT.md`

## Phase K1 Completed

- additive contract freeze for existing API routes
- formal API key management contract defined (`create/list/rotate/revoke/audit`)
- formal agent memory contract defined (`search/fetch/provenance/write/update`)

Evidence:

- `23_API_KEYS_AUTHZ_AND_MEMORY_CONTRACT_PLAN.md`

## Phase K2 Completed

- additive DB migration for tenant key scopes/expiry/lifecycle metadata
- new append-only auth key audit table
- ORM and auth repository upgraded for scope/expiry/revoke/rotate metadata paths
- unit coverage added for model/repo/migration markers

Evidence:

- `24_PHASE_K2_AUTH_MODEL_UPGRADE_REPORT.md`

## Phase K3 Completed

- DB-primary API key auth flow with explicit env fallback control
- scope enforcement dependency (`require_scopes`) integrated
- auth context propagation (`auth_method`, `auth_key_id`, `auth_scopes`)
- `/api/v1/*` rate-limit category alignment with tenant+identity bucket keys

Evidence:

- `25_PHASE_K3_AUTH_MIDDLEWARE_AUTHZ_ENFORCEMENT_REPORT.md`

## Phase K4 Completed

- `/api/v1/api-keys/*` management routes implemented (create/list/rotate/revoke/audit)
- API keys router registered in app
- API Keys dashboard page implemented with lifecycle actions and one-time reveal flow
- K4 validation coverage added (unit + acceptance + frontend lint)

Evidence:

- `26_PHASE_K4_API_KEYS_MANAGEMENT_API_UI_REPORT.md`

## Phase K5 Completed

- `/api/v1/memory/*` route surface implemented (`search/get/provenance/write/patch`)
- memory write idempotency ledger added (migration + model + repository)
- optimistic concurrency guard added for memory patch updates
- strict tenant+graph scoped memory retrieval/update behavior in router paths
- K5 validation coverage added (unit + acceptance)

Evidence:

- `27_PHASE_K5_MEMORY_API_IMPLEMENTATION_REPORT.md`

## Phase K6 Completed

- lifecycle audit events for key runtime paths (`used`, `denied(scope|expired|revoked)`)
- policy hardening for revoked/expired key rejection codes
- route-level scope denied audit metadata emission
- endpoint-level read/write/search rate-limit category policies

Evidence:

- `28_PHASE_K6_SECURITY_HARDENING_AUDIT_RATELIMIT_REPORT.md`

## Phase K7 Completed

- expanded unit and acceptance coverage for key lifecycle and scope matrix
- memory write/search/get/provenance non-regression coverage
- frontend API keys e2e flow and failure-state coverage
- runtime query recency timezone normalization fix validated

Evidence:

- `29_PHASE_K7_VALIDATION_NON_REGRESSION_REPORT.md`

## Phase K8 Completed

- storage/security/backlog/index documentation reconciled to implemented K1-K7 state
- consolidated summary reports added for API keys/authz and memory contract runtime
- commit flow executed in scoped documentation commits

Evidence:

- `24_PHASE_K_API_KEYS_AUTHZ_REPORT.md`
- `25_PHASE_K_MEMORY_API_CONTRACT_REPORT.md`

## Phase S1 Completed

- additive self-evolve configuration contract added with safe defaults
- self-evolve trigger mode contract validated at startup (`manual|post_upload|periodic|hybrid`)
- guardrails enforce job dependency for async self-evolve modes
- bounds validation added for interval/version-delta/max-actions knobs
- no runtime behavior change by default (contract/guardrail phase only)

Evidence:

- `30_PHASE_S1_SELF_BY_DEFAULT_GUARDRAILS_REPORT.md`

## Phase S2 Completed

- additive `self_evolution_state` schema/model/migration delivered
- scheduler state repository added with idempotent update primitives
- due-graph selection logic added (version delta + interval + active evolve job exclusion)
- tenant isolation validated in repository query paths
- no runtime trigger behavior change in S2 (state foundation only)

Evidence:

- `31_PHASE_S2_SELF_EVOLUTION_STATE_REPORT.md`

## Phase S3 Completed

- centralized shared enqueue helper added: `enqueue_self_evolve_if_due(...)`
- storage follow-up evolve path now routes through shared helper (legacy behavior preserved)
- ingest JSON + multipart success paths now route through shared helper
- memory write success path now routes through shared helper
- one pending/running evolve job per tenant+graph dedupe enforced in shared scheduler path
- due evaluation now uses durable scheduler state (`self_evolution_state`) for version delta + interval checks

Evidence:

- `32_PHASE_S3_CENTRALIZED_SELF_EVOLVE_TRIGGER_REPORT.md`

## Phase S4 Completed

- worker periodic autonomous scheduler fallback added
- worker now performs due-graph scans on interval and enqueues evolve jobs for periodic/hybrid modes
- centralized S3 helper remains single source-of-truth for enqueue/dedupe decisions
- one pending/running evolve job per tenant+graph dedupe preserved
- per-scan action cap enforced via `FAIM_SELF_EVOLVE_MAX_ACTIONS`
- new runtime knob added: `FAIM_SELF_EVOLVE_SCAN_INTERVAL_SECONDS`

Evidence:

- `33_PHASE_S4_WORKER_AUTONOMOUS_SCHEDULER_REPORT.md`

## Phase S5 Completed

- evolve core invention decision moved to config/orchestration settings (no direct env reads)
- explicit `EVOLUTION_SKIPPED` observability reasons added:
  - `insufficient_nodes`
  - `no_actions_after_evaluation`
- prune defaults made practically effective with real touch-count behavior
  - default `PrunePolicy.max_touch_count = 1`
- orchestration/worker now pass invention request intent through run-time evolve wiring
- deterministic ordering and strict-mode invariants preserved

Evidence:

- `34_PHASE_S5_EVOLVE_INVENTION_CORE_HARDENING_REPORT.md`

## Phase S6 Completed

- unit validation gate completed for:
  - self-evolve flags and due-logic (S1/S2/S3/S4)
  - evolve/invention hardening (S5)
  - prune policy behavior
  - invention flag wiring and idempotence
  - production security/auth hardening regression units
- acceptance validation gate completed for full self-evolve chain:
  - write -> due enqueue -> worker execution -> evolve diagnostics/events
  - invention runtime + diagnostics acceptance paths
- storage/memory/query/auth regression gate completed and healthy
- targeted frontend validation completed:
  - typecheck pass
  - API keys Playwright e2e pass after aligning test to current one-time reveal UX
- development-only acceptance fixtures hardened:
  - explicit auth fallback mode for sqlite/dev acceptance suites
  - isolated sqlite DB for memory lifecycle acceptance to remove lock flakiness

Evidence:

- `35_PHASE_S6_END_TO_END_VALIDATION_REPORT.md`

## Phase S7 Completed

- reconciled memory/evolution design doc with final self-default runtime status notes
- updated backlog completion ledger to include S7 close-out
- updated Docs index with S7 report reference and intent mapping
- finalized release-hygiene trace with scoped docs-only completion report

Evidence:

- `36_PHASE_S7_DOCS_RELEASE_HYGIENE_REPORT.md`

## Phase EV-A Completed

- replaced evolution dashboard placeholder with production UI wired to existing contracts
- integrated control panel for graph/profile/persist mode + manual evolve execution
- integrated diagnostics scorecard cards from `/api/v1/metrics/scorecard`
- integrated graph event timeline from `/api/v1/events` + `/api/v1/events/latest`
- added polling/live status, evolution-only filtering, and run outcome observability cards
- no backend schema or route changes in Step A (frontend-only safe integration)

Evidence:

- `37_PHASE_EVOLUTION_STEP_A_UI_INTEGRATION_REPORT.md`

## Phase EV-B Completed

- added read-only evolve runtime status route: `GET /api/v1/evolve/status`
- exposed scheduler/runtime observability in one additive contract:
  - self-evolve/self-invent runtime flags
  - durable scheduler state (`last_seen`, `last_evolved`, `last_enqueued_job`)
  - due-evaluation reason and thresholds
  - active evolve job + last enqueued evolve job summaries
  - last event summary (`last event`, `snapshot hash`, `last skip reason`)
- centralized due decision logic into shared read-only helper and reused it for:
  - enqueue path (`enqueue_self_evolve_if_due`)
  - status path (`/api/v1/evolve/status`)
- added evolve endpoint rate-limit classification coverage for:
  - `GET /api/v1/evolve/*` -> read category
  - `POST /api/v1/evolve` -> write category
- integrated Evolution page Step B UI with status endpoint for live runtime/scheduler visibility
- validated with new unit + acceptance coverage and non-regression checks

Evidence:

- `38_PHASE_EVOLUTION_STEP_B_RUNTIME_STATUS_REPORT.md`

## Phase R2 Completed

- implemented centralized runtime resolver for `profile` + `persist_mode`:
  - single mapping contract for ingest/evolve operations
  - requested/effective mode normalization and coercion handling
- added compatibility guard (`FAIM_PROFILE_PERSIST_COMPAT_MODE`) with safe default `true`
- integrated resolver into:
  - ingest flow
  - evolve flow
  - self-evolve enqueue path
  - worker evolve execution path
- added additive observability fields on evolve/ingest start events:
  - requested/effective profile and persist mode
  - durability path
  - compat mode
  - coercion reason when applicable
- fixed worker evolve execution to pass `persist_mode` (previously dropped)
- validated with new R2 unit/acceptance coverage and regression suites

Evidence:

- `45_PHASE_R2_CENTRAL_POLICY_RESOLVER_REPORT.md`

## Phase R3 Completed

- realized profile/persist runtime behavior in ingest/storage/memory execution paths
- `persist_mode` now materially affects ingest secondary durability behavior:
  - strict path (compat off): synchronous secondary index completion
  - relaxed path (compat off): async queued secondary index job when jobs are enabled
  - fallback sync path when jobs are unavailable
- preserved compatibility guard behavior when `FAIM_PROFILE_PERSIST_COMPAT_MODE=true`
- added additive response/event mode metadata surfacing:
  - requested/effective profile and persist mode
  - durability path
  - index write mode
  - secondary task status + job ID
- extended worker to execute `ingest_secondary_index` jobs and emit async completion observability
- validated with new R3 unit/acceptance coverage plus storage/memory regression suites

Evidence:

- `46_PHASE_R3_STORAGE_INGEST_RUNTIME_REALIZATION_REPORT.md`

## Module Status Snapshot

| Area | Status |
|---|---|
| Storage UI | implemented (queue lifecycle, cancel/retry, provenance drawer, supported-files panel) |
| Storage API surface | implemented |
| Raw immutable persistence | implemented |
| Dedup runtime correctness | implemented |
| Contract guardrails | implemented |
| Production security hardening | implemented |
| Observability metrics/log correlation | implemented |
| Validation/non-regression suite | implemented |
| OCR extraction path (image + scanned PDF) | implemented (feature-flag controlled, fail-closed capable) |
| Self-inventing runtime path | implemented (flag-gated evolve integration + incremental state) |
| Self-evolution durable scheduler state | implemented (state + due-selection repo, no behavior switch yet) |
| Self-evolution trigger source-of-truth | implemented (shared helper wired for storage + ingest + memory writes) |
| Self-evolution autonomous worker fallback | implemented (periodic due-scan enqueue for periodic/hybrid modes) |
| Self-evolution core hardening (config-driven invention, skip observability, practical prune defaults) | implemented (S5) |
| Self-evolution validation and non-regression matrix | implemented (S6) |
| Self-default docs and release-hygiene reconciliation | implemented (S7) |
| Evolution dashboard integration (existing APIs only) | implemented (EV-A) |
| Evolution dashboard runtime status integration (shared due helper + status contract) | implemented (EV-B) |
| Central profile/persist policy resolver with compatibility guard | implemented (R2) |
| Storage/ingest runtime realization for profile/persist durability semantics | implemented (R3) |
| API keys/authz and memory API contract freeze | implemented (K1) |
| Auth key schema foundation for scopes/expiry/audit | implemented (K2 migration + ORM/repo) |
| Auth middleware + route scope enforcement baseline | implemented (K3) |
| API key management runtime API + dashboard UI | implemented (K4) |
| Agent-facing memory API runtime | implemented (K5) |
| API key lifecycle audit and policy hardening | implemented (K6) |
| K-series validation and non-regression matrix | implemented (K7) |
| K-series documentation and commit reconciliation | implemented (K8) |

## Future Enhancements Only

These are the remaining non-blocking roadmap items after P0/P1/P2, A-H, and K1-K8 completion.

## F1 - Security Operations Maturity (P1)

- historical blob re-encryption program for pre-policy plaintext payloads
- operator playbooks for key-rotation rehearsal and emergency rollback drills at deployment level
Reason: rollout-safe migration and drill scheduling must be coordinated per tenant and environment.
Owner: Storage Security Team.

## F2 - Observability Operations Maturity (P1)

- deployment-specific dashboards and alerting integration (SLO burn alerts, dependency outage paging)
- environment-level runbook automation hooks
Reason: environment tooling integration is deployment-specific and outside core runtime implementation.
Owner: SRE / Platform Operations.

## F3 - Performance Extensions (P2)

- deeper cache/index optimization tuning beyond current deterministic baseline
- optional perf namespace reintegration plan (or archive finalization)
Reason: requires dedicated benchmark cycle and controlled tuning acceptance criteria.
Owner: Performance Engineering.

## F4 - Expanded Validation Matrix (P2)

- broader environment matrix (staging/prod-like load and chaos scenarios)
- additional long-run endurance checks for retention worker and background job durability
Reason: long-run and chaos validation requires separate infra windows and release timing.
Owner: QA / Release Engineering.

## F5 - Memory API Operations Maturity (P1)

- complete environment-level auth scope rollout with explicit `memory.read`/`memory.write` policy gates
- add production SLO dashboards for memory route latency/error buckets
- run extended load and replay testing for idempotency ledger under concurrency spikes
Reason: K5 runtime is implemented; remaining work is production operations hardening and rollout governance.
Owner: API Platform + SRE.

## Definition of Done (Current Program)

Core storage program delivery is complete for P0/P1/P2 and phases A-H.

Remaining backlog now represents deployment maturity and optional optimization work, not missing core storage functionality.
