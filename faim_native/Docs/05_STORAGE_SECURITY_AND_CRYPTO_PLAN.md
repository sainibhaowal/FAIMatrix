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

## 2) Security Gap Status (Post Phase D/E)

Implemented:

1. Raw file encryption-at-rest path is wired and production fail-closed policy is enforced.
2. Envelope encryption runtime integration is active with tenant DEK manager support.
3. Upload validators are consistently enforced on ingest/storage upload paths.
4. Production plaintext fallback is blocked in runtime and routers.
5. Storage route authz/tenant isolation coverage exists in acceptance tests.

Remaining hardening focus:

1. Historical payload re-encryption program for pre-rollout plaintext blobs.
2. Environment-level alerting/dashboard integration for security observability signals.

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

1. Make raw-store write mandatory before extraction (no bypass in production mode).
2. Enforce upload content-type, extension, filename, and size limits in ingest router.
3. Require valid `raw_id` format contract and canonical UUID handling where needed.
4. Ensure no plaintext secrets/tokens are logged (keep redaction filters active).
5. Turn off insecure fallback paths in production (env-guarded).
6. Add storage action audit events:
- raw stored
- dedup hit
- extraction failed
- encryption failure
- deletion requests

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

- These gate categories are largely implemented in unit/acceptance suites for Phase D and Phase E.
- Key rotation behavior is documented in runbook (`16_STORAGE_OPERATIONS_RUNBOOK.md`) and supported by tenant DEK manager rotation API.
