# FAIM-Native threat model

This document identifies the main threats at the current API, storage, worker,
and deployment boundaries. A listed control is a design requirement; it is
not a claim that every deployment has been independently audited.

## Threats and controls

| Threat | Required controls | Evidence to verify |
| --- | --- | --- |
| Tenant cross-leak | Tenant scope on auth, queries, events, cache keys, and storage actions | Tenant-isolation tests and an authenticated two-tenant smoke test |
| Credential theft | Argon2id/API-key hashing, secret redaction, no secrets in Git, HTTPS at the edge | Auth tests, secret scan, proxy/log review |
| Injection | Parameterized database access, input validation, filename/path sanitization | Unit/integration tests and code review |
| SSRF or unsafe fetch | Do not fetch arbitrary user URLs from ingest without an explicit reviewed allowlist | Ingest code review and negative tests |
| Deserialization/RCE | Avoid unsafe deserialization and user-controlled templates; scan dependencies | Security tests, pip-audit, and dependency review |
| Replay or duplicate writes | Idempotency keys/content hashes and single-writer/advisory-lock rules where applicable | Duplicate-ingest and concurrent-evolution tests |
| Denial of service | Request/body limits, upload limits, rate limits, bounded SSE connections, timeouts | Load/saturation test and configured limit review |
| Data loss | PostgreSQL plus raw-store backups, migration gating, restore drills | Recorded isolated restore |
| Supply chain | Pinned dependencies and security scans | CI artifacts for the release commit |

## Invariants

1. Plaintext API keys are never stored in the database.
2. Protected reads and writes remain tenant-scoped.
3. Secrets are excluded from logs and benchmark artifacts.
4. User input is validated before it reaches storage or execution paths.
5. Release claims cite a reproducible test or deployment artifact.

## Incident response

1. Revoke compromised credentials.
2. Stop writes if data integrity is uncertain.
3. Preserve logs, request IDs, migration versions, and affected tenant IDs.
4. Assess impact from canonical PostgreSQL, journal, and raw-store data.
5. Restore into an isolated environment before repairing production state.
6. Add a regression test or operational check for the failure mode.
