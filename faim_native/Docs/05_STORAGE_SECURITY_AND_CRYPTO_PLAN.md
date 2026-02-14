# 05 - Storage Security and Crypto Plan

This is the security baseline and hardening plan for storage + ingestion.

## 1) Current Security Controls (Present)

## Authentication and Access

- tenant API key middleware with constant-time compare
- JWT middleware for NextAuth bearer tokens
- admin key validation path
- auth OTP flow with rate limiting and lockout

## Hashing and Integrity

- API keys hashed using Argon2id (`runtime/secrets.py`)
- OTP values stored/verified as HMAC hashes
- packet hash and vector hash for deterministic integrity
- event checksum for append-only journal integrity

## Transport and Headers

- security headers middleware (HSTS/CSP/frame options/etc.)
- request correlation IDs
- structured logging with sensitive value redaction

## 2) Security Gap Status (Post Phase D/E/F + K1-K8)

Implemented:

1. Raw file encryption-at-rest path is wired and production fail-closed policy is enforced.
2. Envelope encryption runtime integration is active with tenant DEK manager support.
3. Upload validators are consistently enforced on ingest/storage upload paths.
4. Production plaintext fallback is blocked in runtime and routers.
5. Storage route authz/tenant isolation coverage exists in acceptance tests.
6. Phase F non-regression suites cover lifecycle/retry/cancel/delete/retention flows.
7. API keys/authz + memory API additive contract freeze is defined and documented (K1).
8. Auth key data model supports scopes/expiry/lifecycle metadata and append-only key audit table (K2).
9. DB-primary API key auth + scope enforcement dependency + tenant/key-aware rate-limit alignment are implemented (K3).
10. API key management runtime surface (`/api/v1/api-keys/*`) is implemented with tenant-scoped lifecycle operations (K4).
11. Agent-facing memory API routes (`/api/v1/memory/*`) are implemented with idempotency and optimistic update guards (K5).
12. Key lifecycle audit taxonomy and denial policy paths are enforced (`denied(scope|expired|revoked)`) with sanitized metadata (K6).
13. K7 validation confirms authz lifecycle, memory lifecycle, and frontend/API key UI non-regression coverage.

Remaining hardening focus:

1. Historical payload re-encryption program for pre-rollout plaintext blobs.
2. Environment-level dashboard/alert wiring for security observability signals.
3. Extended multi-environment soak/chaos security validation (staging/prod-like load windows).

## 3) Required Security Model for Storage Setup

## Data Classification

- Tier A: raw files and extracted text evidence (high sensitivity)
- Tier B: vectors/graph metadata (sensitive)
- Tier C: diagnostics/aggregates (lower sensitivity)

## Encryption at Rest

- raw bytes: mandatory encryption before durable storage
- DB sensitive fields: optional column-level encryption for highest-risk payloads
- backups: encrypted backup artifacts + key separation

## Key Hierarchy

- Master Key (KMS or securely injected env)
- Tenant DEK (wrapped by master key)
- DEK rotates per policy and incident response

## Crypto Requirements

- AES-256-GCM for authenticated encryption of raw payloads
- per-record nonce uniqueness
- key rotation without data loss (rewrap model)

## Hashing Requirements

- SHA-256 for content identity and dedup fingerprints
- Argon2id for stored authentication secrets
- HMAC for tamper-sensitive token/email-bound codes

## 4) Production Hardening Checklist

1. Make raw-store write mandatory before extraction (no bypass in production mode): implemented.
2. Enforce upload content-type, extension, filename, and size limits in ingest router: implemented.
3. Require valid `raw_id` format contract and canonical UUID handling where needed: implemented.
4. Ensure no plaintext secrets/tokens are logged (keep redaction filters active): implemented.
5. Turn off insecure fallback paths in production (env-guarded): implemented.
6. Add storage action audit events: implemented.
- raw stored
- dedup hit
- extraction failed
- encryption failure
- deletion requests
7. Enforce DB-primary API key validation with explicit production-safe fallback policy: implemented.
8. Enforce route-level scope checks for memory/key-management surfaces: implemented and validated.

## 5) Deletion and Retention Security

For account deletion and retention policies:

- delete graph records transactionally
- purge vector index artifacts
- remove raw blobs by reference policy
- record signed/auditable deletion event receipts

## 6) Security Test Gates Before Launch

Required automated gates:

- unit tests for crypto wrappers and key handling
- API tests for authz/authn on all storage endpoints
- upload abuse tests (oversize, traversal names, malformed payload)
- encryption/decryption roundtrip tests with rotated keys
- deletion and restore policy tests

Current status:

- These gate categories are implemented in unit/acceptance coverage across Phases D/E/F/K6/K7.
- Key lifecycle events (`created`, `rotated`, `revoked`, `used`, `denied(scope|expired|revoked)`) are implemented with append-only audit persistence.
- Key rotation behavior is documented in runbook (`16_STORAGE_OPERATIONS_RUNBOOK.md`) and supported by tenant DEK manager rotation API.
- Remaining work is deployment-level operations integration (dashboards/alerts, historical blob re-encryption, and extended soak windows).
