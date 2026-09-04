# Security policy

FAIM-Native handles memory, uploaded files, tenant-scoped data, API keys, authentication tokens, background jobs, and cryptographic material. Security reports should be handled privately.

## Reporting a vulnerability

Please do not open a public issue for an exploitable vulnerability. Use GitHub's private vulnerability reporting or contact the repository maintainers privately through the project owner's configured contact channel. Include:

- a concise description and impact;
- affected commit, version, service, or configuration;
- reproducible steps or a minimal proof of concept;
- relevant logs with secrets and personal data removed; and
- a suggested mitigation, if known.

If private reporting is not enabled, open a non-sensitive issue asking for a private contact channel without publishing exploit details.

## In scope

Reports are especially important for:

- authentication, authorization, API-key scope enforcement, and tenant isolation;
- raw-file exposure, unsafe uploads, path traversal, SSRF, and deserialization;
- encryption, key rotation, secret handling, and log redaction;
- SQL injection, query manipulation, and unsafe graph operations;
- event-stream or WebSocket authorization and cross-tenant leakage;
- dependency or container vulnerabilities that affect the shipped deployment; and
- migration, backup, restore, or retention paths that can destroy or expose data.

## Safe testing

Test only against a local or explicitly authorized deployment. Do not access another user's data, exfiltrate secrets, run denial-of-service tests against shared infrastructure, or modify production data. Use synthetic tenants and sample files.

## Maintainer response

Maintainers will acknowledge reports when possible, reproduce the issue, assess impact, coordinate a fix, and publish a remediation note when disclosure is safe. Credit will be given to reporters who want attribution and who follow coordinated disclosure.

The security implementation references are in [`docs/2) BackEnd/Security`](<docs/2) BackEnd/Security/), [`docs/Operations/security-hardening.md`](docs/Operations/security-hardening.md), and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
