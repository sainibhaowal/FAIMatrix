# 23 - API Keys + Authz + Memory Contract Plan (Phase K1)

This document freezes current API behavior and defines additive contracts for API key management and agent memory access.

Status: Frozen contract baseline; downstream phases K2-K7 implemented

## Implementation Update (2026-02-13)

K2 (auth data model upgrade), K3 (auth middleware + authz enforcement), K4
(API key management API + frontend page), and K5 (agent-facing memory API
runtime) are now implemented.

Current product posture:

- verified users authenticate through OTP/session flow
- tenant API keys are the programmatic access path
- there is no live admin control plane in the shipped app
- any higher-privilege key scope is a tenant/programmatic privilege, not a separate admin persona

K6 (security hardening + audit + rate limits) is now implemented:

- auth key usage/denial audit taxonomy completed (`used`, `denied(scope)`,
  `denied(expired)`, `denied(revoked)`)
- middleware policy hardened for revoked/expired rejection paths
- scope-denied 403 path now emits audit events
- endpoint-level rate-limit policy categories added (method + route aware)
- production guardrail tightened: scope enforcement required in production
- no-plaintext-key log/audit safety coverage expanded with tests

Implementation reports:

- `24_PHASE_K2_AUTH_MODEL_UPGRADE_REPORT.md`
- `25_PHASE_K3_AUTH_MIDDLEWARE_AUTHZ_ENFORCEMENT_REPORT.md`
- `26_PHASE_K4_API_KEYS_MANAGEMENT_API_UI_REPORT.md`
- `27_PHASE_K5_MEMORY_API_IMPLEMENTATION_REPORT.md`
- `28_PHASE_K6_SECURITY_HARDENING_AUDIT_RATELIMIT_REPORT.md`

## 1) Scope and Safety Rules

- phase: K1 (contract freeze and design spec only)
- no breaking route removals or renames
- no response field removals
- additive-only contract changes
- strict tenant isolation and auditability requirements

## 2) Current Route Freeze Baseline

The following existing routes are frozen for compatibility and must remain stable:

- auth:
  - `POST /api/v1/auth/otp/request`
  - `POST /api/v1/auth/otp/verify`
  - `GET /api/v1/auth/me`
- ingest/query/core:
  - `POST /api/v1/ingest`
  - `POST /api/v1/ingest/upload`
  - `POST /api/v1/query`
  - `GET /api/v1/node/{node_id}`
  - `GET /api/v1/node/{node_id}/explain`
- storage:
  - full `/api/v1/storage/*` surface from Phase A-J

## 3) Additive API Key Management Contract

New route group: `/api/v1/api-keys`

### 3.1 Create Key

- `POST /api/v1/api-keys`
- purpose: create tenant-scoped API key (one-time plaintext reveal)
- request:
  - `label` (optional)
  - `scopes` (required list)
  - `expires_at` (optional RFC3339 timestamp)
- response:
  - key metadata (`key_id`, `key_prefix`, `tenant_id`, `scopes`, `created_at`, `expires_at`)
  - `plaintext_key` (returned once only)

### 3.2 List Keys

- `GET /api/v1/api-keys`
- purpose: list tenant keys with active/revoked/expired state
- query:
  - `include_revoked` (optional bool)
- response:
  - list of key metadata
  - no plaintext secrets

### 3.3 Rotate Key

- `POST /api/v1/api-keys/{key_id}/rotate`
- purpose: create replacement key and revoke previous key
- request:
  - `reason` (optional)
  - `expires_at` (optional)
- response:
  - old key state (`revoked_at`)
  - new key metadata + one-time `plaintext_key`

### 3.4 Revoke Key

- `POST /api/v1/api-keys/{key_id}/revoke`
- purpose: revoke active key
- request:
  - `reason` (optional)
- response:
  - revoked key metadata

### 3.5 Key Audit History (optional but planned)

- `GET /api/v1/api-keys/audit`
- filters:
  - `key_id`, `action`, `after`, `limit`
- response:
  - append-only audit events (`action`, `actor`, `request_id`, `meta`, `created_at`)

## 4) Scope Model (Authz)

Minimum scope set:

- `keys.read`
- `keys.write`
- `memory.read`
- `memory.write`
- `memory.admin` (reserved elevated tenant/programmatic privilege)

Rules:

- missing required scope -> `403`
- revoked key -> `401`
- expired key -> `401`
- scope checks are route-level and default deny

## 5) Additive Agent Memory Contract

New route group: `/api/v1/memory`

### 5.1 Search Memory

- `POST /api/v1/memory/search`
- request:
  - `graph_id`
  - `query_text`
  - `k`
  - `profile`
  - `return_explain`
- response:
  - ranked memory results + score/explain/provenance references

### 5.2 Fetch Memory Item

- `GET /api/v1/memory/{node_id}?graph_id=...`
- response:
  - node payload + summary metadata + source anchors

### 5.3 Fetch Memory Provenance

- `GET /api/v1/memory/{node_id}/provenance?graph_id=...`
- response:
  - upstream raw references, event linkage, dedup lineage

### 5.4 Write Memory Safely

- `POST /api/v1/memory/write`
- request:
  - `graph_id`
  - content payload (`text` and optional metadata)
  - optional `idempotency_key`
  - ingest options (`profile`, `persist_mode`)
- response:
  - packet hash, write status, node/vector counts, provenance linkage

### 5.5 Update Memory Safely

- `PATCH /api/v1/memory/{node_id}`
- request:
  - `graph_id`
  - allowed mutable fields only
  - optional concurrency guard (`expected_updated_at`)
- response:
  - updated node metadata and audit info

## 6) Security and Isolation Contract

- all routes require authenticated tenant context
- all data access must include tenant filter in DB path
- graph-level scoping required where applicable
- plaintext keys are never logged or persisted
- key creation responses are one-time secret exposure only
- all lifecycle actions emit auditable events

## 7) Error Contract (Normalized)

- `400`: invalid request shape/parameters
- `401`: auth failed, revoked key, or expired key
- `403`: authenticated but missing scope
- `404`: resource not found in tenant scope
- `409`: state conflict (already revoked, rotate conflict, stale update)
- `422`: semantic validation failure

Error payload baseline:

- `error`
- `code`
- `request_id`
- `detail` (bounded, non-secret)

## 8) Backward Compatibility Guarantees

- existing `/api/v1/storage/*`, `/api/v1/query`, `/api/v1/ingest`, `/api/v1/node/*` remain unchanged
- new K-phase endpoints are additive and opt-in
- legacy env-key fallback behavior remains during transition window
- database schema changes are additive and nullable-safe
- admin-oriented compatibility tables or env knobs, if still present in schema or deploy templates, are legacy-only and not part of the live product surface

## 9) K1 Deliverables

- this contract plan document (`23`)
- backlog/status update to include K1/K2 execution stream
- implementation to begin in K2 with migration-first approach
