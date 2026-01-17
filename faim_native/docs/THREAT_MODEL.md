# FAIM-Native Threat Model

> Stage-11: Security Hardening

This document describes the security threats relevant to FAIM-Native and the mitigations in place.

## 1. Threat Categories

### 1.1 Tenant Cross-Leak

**Threat:** Data from one tenant leaks to another tenant.

**Attack Vectors:**

- Query returns nodes from wrong tenant
- Events stream includes other tenants' events
- Shared cache returns wrong tenant's data

**Mitigations:**

- ✅ `tenant_id NOT NULL` on all tables (Stage-7.1)
- ✅ Database trigger rejects empty tenant_id
- ✅ All queries filter by tenant_id
- ✅ Query cache keys include tenant_id
- ✅ SSE stream filters by tenant_id

### 1.2 Credential Theft

**Threat:** API keys or admin credentials are stolen.

**Attack Vectors:**

- Keys exposed in logs
- Keys in plaintext in database
- Keys transmitted insecurely
- Keys in version control

**Mitigations:**

- ✅ API keys hashed with Argon2id (Stage-11)
- ✅ Log redaction filters sensitive patterns
- ✅ No secrets in docker-compose.yml
- ✅ .env files in .gitignore
- ✅ Constant-time key comparison (Stage-7.1)

### 1.3 Server-Side Request Forgery (SSRF)

**Threat:** Attacker tricks server into making internal requests.

**Attack Vectors:**

- URL injection in ingest
- Webhook callbacks to internal services

**Mitigations:**

- ✅ No external URL fetching in ingest pipeline
- ✅ Raw files stored as-is (no URL resolution)
- ⚠️ Consider: URL validation if webhooks added

### 1.4 Injection Attacks

**Threat:** SQL injection, command injection, or code injection.

**Attack Vectors:**

- Malicious SQL in query parameters
- Shell commands in filenames
- Code in uploaded files

**Mitigations:**

- ✅ SQLAlchemy parameterized queries
- ✅ No shell commands executed on user input
- ✅ Filename sanitization
- ✅ Input validation (tenant_id, graph_id patterns)

### 1.5 Remote Code Execution (RCE)

**Threat:** Attacker executes arbitrary code on server.

**Attack Vectors:**

- Deserialization vulnerabilities
- Template injection
- Dependency vulnerabilities

**Mitigations:**

- ✅ No pickle/yaml.load(untrusted)
- ✅ No user-controlled templates
- ✅ CVE scanning in CI (pip-audit, bandit)
- ✅ Minimal dependencies

### 1.6 Log Leaks

**Threat:** Sensitive data leaks through logs.

**Attack Vectors:**

- API keys in log messages
- Database URLs with passwords
- Stack traces with internal paths

**Mitigations:**

- ✅ RedactingFilter on all log handlers
- ✅ Generic error messages to clients
- ✅ Sensitive patterns auto-redacted

### 1.7 Replay Attacks

**Threat:** Attacker replays valid requests to cause harm.

**Attack Vectors:**

- Replaying ingest requests
- Replaying evolution commands

**Mitigations:**

- ✅ Ingest idempotency (dedup by content hash)
- ✅ Evolution advisory locks (single-writer)
- ⚠️ Consider: Request nonces for critical ops

### 1.8 Denial of Service (DoS)

**Threat:** Attacker overwhelms the system.

**Attack Vectors:**

- Excessive API requests
- Large file uploads
- Expensive queries
- SSE connection exhaustion

**Mitigations:**

- ✅ Rate limiting per tenant (Stage-9)
- ✅ Payload bounds (4KB)
- ✅ Upload size limits (Stage-11)
- ✅ SSE connection limits and timeouts

### 1.9 Supply Chain Attacks

**Threat:** Malicious code in dependencies.

**Attack Vectors:**

- Compromised PyPI packages
- Typosquatting packages
- Vulnerable dependencies

**Mitigations:**

- ✅ pip-audit in CI
- ✅ bandit security linting
- ✅ Pinned dependencies
- ⚠️ Consider: requirements.txt hash verification

## 2. FAIM Security Invariants

These invariants MUST always hold:

| Invariant | Description                                        |
| --------- | -------------------------------------------------- |
| **I1**    | API keys are NEVER stored in plaintext             |
| **I2**    | All queries filter by tenant_id                    |
| **I3**    | Logs NEVER contain raw API keys                    |
| **I4**    | Error responses NEVER contain stack traces         |
| **I5**    | User input is ALWAYS validated before use          |
| **I6**    | Database queries ALWAYS use parameters             |
| **I7**    | File paths are ALWAYS sanitized                    |
| **I8**    | Rate limits ALWAYS apply to authenticated requests |

## 3. Trust Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                      UNTRUSTED ZONE                          │
│  ┌─────────────┐                                            │
│  │   Client    │ ─────────────────────────────────────────┐ │
│  └─────────────┘                                          │ │
└───────────────────────────────────────────────────────────│─┘
                                                            │
┌───────────────────────────────────────────────────────────│─┐
│                      DMZ (Reverse Proxy)                  │ │
│  ┌─────────────┐                                          │ │
│  │  Nginx/     │◄─────────────────────────────────────────┘ │
│  │  Caddy      │                                            │
│  └──────┬──────┘                                            │
└─────────│───────────────────────────────────────────────────┘
          │ TLS Termination
┌─────────│───────────────────────────────────────────────────┐
│         ▼            TRUSTED ZONE                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  FAIM API   │───▶│  Postgres   │    │   Redis     │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## 4. Security Testing

- `tests/security/test_api_key_hashing.py` - Key hashing tests
- `tests/security/test_logs_redact_secrets.py` - Log redaction tests
- `scripts/security_audit.sh` - CVE scanning

## 5. Incident Response

1. **Key Compromise:** Immediately revoke via key_id, issue new keys
2. **Data Breach:** Check audit logs, identify affected tenants
3. **CVE Found:** Run pip-audit, update affected packages
