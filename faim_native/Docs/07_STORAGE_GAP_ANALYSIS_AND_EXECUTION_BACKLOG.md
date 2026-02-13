# 07 - Storage Gap Analysis and Execution Backlog

This backlog now separates completed delivery from true future enhancements.

## Priority Legend

- P0: blocking correctness/security
- P1: required for complete storage product
- P2: optimization/hardening

## Program Status (as of 2026-02-13)

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
| API keys/authz and memory API contract freeze | implemented (K1) |
| Auth key schema foundation for scopes/expiry/audit | implemented (K2 migration + ORM/repo) |
| Auth middleware + route scope enforcement baseline | implemented (K3) |
| API key management runtime API + dashboard UI | implemented (K4) |

## Future Enhancements Only

These are the remaining non-blocking roadmap items after P0/P1/P2 and A-H delivery.

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

## F5 - Memory API Runtime Delivery (P1)

- implement dedicated agent memory route surface under `/api/v1/memory/*`
- map route-level scopes (`memory.read`/`memory.write`) end-to-end with acceptance coverage
- publish operational docs for memory write/update idempotency behavior
Reason: K1-K4 delivered API key contract, auth runtime baseline, and key management UI; memory route runtime remains.
Owner: API Platform + Agent Interfaces.

## Definition of Done (Current Program)

Core storage program delivery is complete for P0/P1/P2 and phases A-H.

Remaining backlog now represents deployment maturity and optional optimization work, not missing core storage functionality.
