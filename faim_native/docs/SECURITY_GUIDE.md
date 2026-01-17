# FAIM-Native Security Guide for Frontend Integration

> Stage-11: Security Hardening

This guide explains the security measures protecting FAIM-Native when connected to a frontend application.

## Security Summary

**Is it safe?** ✅ Yes — The API is production-hardened with multiple defense layers.

---

## Authentication & Authorization

| Protection            | Implementation                      | Status |
| --------------------- | ----------------------------------- | ------ |
| API Key Required      | `X-Tenant-Id` + `X-Api-Key` headers | ✅     |
| Keys Hashed           | Argon2id (never stored plaintext)   | ✅     |
| Tenant Isolation      | Each tenant sees ONLY their data    | ✅     |
| Session Tokens        | HttpOnly cookies for browser UI     | ✅     |
| Constant-Time Compare | Prevents timing attacks             | ✅     |

### How Authentication Works

```
Frontend Request
      │
      ▼
┌─────────────────────────────────────────┐
│  TenantAuthMiddleware                   │
│  ├── Check X-Tenant-Id header           │
│  ├── Check X-Api-Key header             │
│  ├── Verify against Argon2id hash       │
│  └── Attach tenant_id to request.state  │
└─────────────────────────────────────────┘
      │
      ▼
  Route Handler (sees only tenant's data)
```

---

## Rate Limiting (Anti-Abuse)

| Protection        | Implementation              | Status |
| ----------------- | --------------------------- | ------ |
| Per-Tenant Limits | Token bucket algorithm      | ✅     |
| 429 Response      | Too many requests = blocked | ✅     |
| Configurable      | `RATE_LIMIT_*` env vars     | ✅     |

---

## Input Validation (Anti-Injection)

| Attack Vector   | Protection                       | Status |
| --------------- | -------------------------------- | ------ |
| SQL Injection   | SQLAlchemy parameterized queries | ✅     |
| Path Traversal  | Filename sanitization            | ✅     |
| Large Uploads   | Max 10MB per file                | ✅     |
| Malicious Files | Content-type validation          | ✅     |
| Payload Bombs   | Max 4KB field size               | ✅     |
| Deep Nesting    | Max 10 levels                    | ✅     |

---

## Log Redaction (No Secret Leaks)

These patterns are **automatically redacted** from all logs:

- API keys (`X-Api-Key: ***`)
- Passwords (`password=***`)
- Database URLs (`postgresql://user:***@...`)
- Bearer tokens
- Authorization headers

---

## Error Handling (No Stack Traces)

| Scenario           | User Sees               | Logs Contain     |
| ------------------ | ----------------------- | ---------------- |
| 400 Bad Request    | Generic message         | Details          |
| 401 Unauthorized   | "Invalid credentials"   | IP, tenant       |
| 500 Internal Error | "Internal server error" | Full stack trace |

**Hackers never see internal paths or code structure.**

---

## Container Hardening

| Protection              | Implementation            | Status |
| ----------------------- | ------------------------- | ------ |
| Non-root user           | Container runs as `faim`  | ✅     |
| No privilege escalation | `no-new-privileges: true` | ✅     |
| Dropped capabilities    | `cap_drop: ALL`           | ✅     |
| Resource limits         | CPU/Memory limits set     | ✅     |

---

## Frontend Integration Checklist

When connecting your frontend:

### Required at API Level (Already Done) ✅

- [x] API key authentication
- [x] Tenant isolation
- [x] Rate limiting
- [x] Input validation
- [x] Log redaction
- [x] Generic error responses

### Required at Deployment Level

- [ ] **TLS/HTTPS** — Use Caddy, Nginx, or Cloudflare
- [ ] **CORS** — Restrict to your frontend domain
- [ ] **Security Headers** — Add via reverse proxy

### Recommended Deployment Architecture

```
┌─────────────┐     HTTPS      ┌─────────────┐      HTTP      ┌─────────────┐
│  Frontend   │──────────────▶│   Reverse   │───────────────▶│  FAIM API   │
│  (Browser)  │    (TLS 1.3)   │   Proxy     │  (localhost)   │   :8000     │
└─────────────┘                └─────────────┘                └─────────────┘
                                     │
                              Security headers:
                              - Strict-Transport-Security
                              - X-Frame-Options: DENY
                              - X-Content-Type-Options: nosniff
```

---

## What Hackers Cannot Do

| Attack                 | Why It Fails                    |
| ---------------------- | ------------------------------- |
| Steal API keys from DB | Keys are Argon2id hashed        |
| Access other tenants   | All queries filter by tenant_id |
| Read secrets from logs | RedactingFilter removes them    |
| SQL injection          | Parameterized queries only      |
| Upload malware         | Content-type + size validation  |
| Brute force            | Rate limiting blocks            |
| Privilege escalation   | Container runs as non-root      |

---

## Security Invariants

These MUST always hold:

1. **I1**: API keys are NEVER stored in plaintext
2. **I2**: All queries filter by tenant_id
3. **I3**: Logs NEVER contain raw API keys
4. **I4**: Error responses NEVER contain stack traces
5. **I5**: User input is ALWAYS validated
6. **I6**: Database queries ALWAYS use parameters
7. **I7**: File paths are ALWAYS sanitized
8. **I8**: Rate limits ALWAYS apply

---

## See Also

- [THREAT_MODEL.md](./THREAT_MODEL.md) — Full threat analysis
- [DATA_CLASSIFICATION.md](./DATA_CLASSIFICATION.md) — Data sensitivity levels
- [DEPLOYMENT_TLS.md](./DEPLOYMENT_TLS.md) — TLS configuration guide
