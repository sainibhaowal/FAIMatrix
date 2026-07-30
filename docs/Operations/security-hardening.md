# Security Hardening

This document captures the production security baseline that FAIM should keep
enabled.

## Baseline Controls

- Explicit CORS origin allowlist.
- No wildcard CORS with credentials in production.
- Production CSP without `unsafe-eval`.
- HTTPS redirect and HSTS at the edge.
- DB-backed auth as the primary path.
- Env-based auth fallback disabled in production.
- Security and dependency scans in CI.
- Secret detection on every pull request.
- GitHub branch protection on `main`/`master`:
  - Require the CI and security checks before merge.
  - Require at least one approval for normal code changes.
  - Require two approvals for `deploy/`, auth, middleware, and migrations.
  - Block direct pushes.
  - Require up-to-date branches before merge.

## Verification Points

- `FAIM_MODE=production` or equivalent staging mode uses strict origin rules.
- Security headers are present on API responses.
- CI fails on vulnerable dependencies or hardcoded secrets.
- Audit logs do not leak API keys or bearer tokens.

## Change Rule

Any change to auth, middleware, deployment, or migration code must be reviewed
as a security-sensitive change.
