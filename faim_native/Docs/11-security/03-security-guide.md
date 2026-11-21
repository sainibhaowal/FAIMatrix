# Security guide for frontend integration

This guide documents the security boundary that the current frontend/API
integration must preserve. It is a control checklist, not a certification.

## Authentication

Protected API routes use tenant-scoped authentication. The normal API-key
headers are:

```http
X-Tenant-Id: <tenant-id>
X-Api-Key: <api-key>
```

Production configuration must use database-primary authentication, disable the
legacy environment fallback, and enable scope enforcement. Browser sessions
must use the configured secure cookie/session path.

## Required frontend controls

- Use HTTPS at the public edge.
- Keep API keys out of browser bundles, URLs, logs, and analytics.
- Use an explicit CORS origin allowlist.
- Preserve tenant and graph scope when proxying requests.
- Redact authorization headers and secrets from client/server logs.
- Treat upload, delete, retention, re-encryption, and rotation actions as
  privileged operations.

## Verification

Verify the actual deployed configuration and run an authenticated smoke test.
Do not infer security from a green health endpoint or from a UI status badge.
