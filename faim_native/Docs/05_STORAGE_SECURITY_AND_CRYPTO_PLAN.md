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

## 2) Current Security Gaps Affecting Storage

1. Raw file encryption at rest is not yet wired through ingest API flow.
2. Envelope encryption modules exist but are not integrated end-to-end.
3. Upload validators exist but are not consistently enforced by ingest endpoints.
4. Some auth code paths still permit fallback behavior that should be environment-gated for production.

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
