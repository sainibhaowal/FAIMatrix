# Stage-11 Report: Security Hardening

## Status: ✅ COMPLETE

**Date:** 2026-01-17  
**Commits:** `941c9a8`, `0c223e1`

---

## Overview

Stage-11 addresses critical security gaps not covered by Stages 1-10:

| Gap                   | Resolution         |
| --------------------- | ------------------ |
| API keys plaintext    | Argon2id hashing   |
| Secrets in logs       | RedactingFilter    |
| No CVE scanning       | pip-audit + bandit |
| No threat model       | Documentation      |
| No encryption at rest | AES-256-GCM        |
| No input validation   | Validators module  |

---

## Phase 1: Critical Security

### 11.2 API Key Hashing

- **Algorithm:** Argon2id (PHC winner)
- **Storage:** Only hashes in `tenant_api_keys` table
- **Features:** Key rotation, revocation, constant-time compare

```python
from runtime.secrets import hash_api_key, verify_api_key

key_hash = hash_api_key("faim_abc123_secret")
# Returns: $argon2id$v=19$m=65536,t=3,p=4$...

is_valid = verify_api_key("faim_abc123_secret", key_hash)
# Returns: True (constant-time)
```

### 11.6 Log Redaction

Automatically redacts sensitive patterns:

- API keys (`X-Api-Key: *`)
- Database URLs (`postgresql://user:pass@...`)
- Bearer tokens
- Passwords

### 11.8 CVE Scanning

```bash
./scripts/security_audit.sh
# Runs: pip-audit, bandit, hardcoded secret scan
```

---

## Phase 2: Defense in Depth

### 11.1 Threat Model

See [THREAT_MODEL.md](./THREAT_MODEL.md) for:

- 9 threat categories
- 8 security invariants
- Trust boundaries diagram

### 11.5 Raw File Encryption

```python
from store.crypto import encrypt_for_storage, decrypt_from_storage

encrypted = encrypt_for_storage(file_bytes, dek)
decrypted = decrypt_from_storage(encrypted, dek)
```

### 11.7 Input Validation

```python
from api.validators import validate_upload_size, sanitize_filename

validate_upload_size(file.size)  # Max 10MB
safe_name = sanitize_filename(file.filename)  # No traversal
```

---

## Phase 3: Enterprise Features

### 11.3 Session Tokens

- HttpOnly cookies
- 15-minute rolling expiry
- HMAC-signed tokens

### 11.4 TLS Documentation

See [DEPLOYMENT_TLS.md](./DEPLOYMENT_TLS.md) for:

- Cloudflare, Caddy, Nginx configs
- Database TLS (PostgreSQL, Redis)
- Security headers

### 11.9 Container Hardening

```yaml
# docker-compose.yml
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
```

---

## Security Invariants

| ID  | Invariant                         | Enforcement         |
| --- | --------------------------------- | ------------------- |
| I1  | API keys NEVER stored plaintext   | Argon2id hash       |
| I2  | All queries filter by tenant_id   | DB trigger          |
| I3  | Logs NEVER contain raw API keys   | RedactingFilter     |
| I4  | Errors NEVER contain stack traces | errors.py           |
| I5  | User input ALWAYS validated       | validators          |
| I6  | DB queries ALWAYS parameterized   | SQLAlchemy          |
| I7  | File paths ALWAYS sanitized       | sanitize_filename   |
| I8  | Rate limits ALWAYS apply          | RateLimitMiddleware |

---

## Files Created

| File                                             | Purpose                 |
| ------------------------------------------------ | ----------------------- |
| `runtime/secrets.py`                             | Argon2id key hashing    |
| `store/pg/models_auth.py`                        | API key models          |
| `store/pg/repos/auth_repo.py`                    | Key CRUD                |
| `store/pg/migrations/0003_stage11_auth_keys.sql` | Auth tables             |
| `api/middleware/errors.py`                       | Generic error responses |
| `api/middleware/session.py`                      | Session tokens          |
| `api/validators/input_limits.py`                 | Input validation        |
| `store/crypto/envelope.py`                       | AES-256-GCM             |
| `store/pg/models_crypto.py`                      | Crypto key models       |
| `docs/THREAT_MODEL.md`                           | Threat documentation    |
| `docs/DATA_CLASSIFICATION.md`                    | Data sensitivity        |
| `docs/DEPLOYMENT_TLS.md`                         | TLS guide               |
| `scripts/security_audit.sh`                      | CVE scanning            |
| `tests/security/*`                               | 28 security tests       |

---

## Verification

```bash
# Security tests
python3 -m pytest tests/security/ -v
# 28 passed ✅
```

---

## Migration Guide

### Migrating from TENANT_KEYS_JSON

1. Run migration: `python -m store.pg.migrate up`
2. Create hashed keys via AuthRepo
3. Update clients with new keys
4. Remove TENANT_KEYS_JSON from env

Both old (env var) and new (DB hash) methods work during transition.
