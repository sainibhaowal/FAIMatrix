# FAIM-Native Quality Gates & Verification

## Production Truth Gate

Final verification checklist for production readiness:

| Gate           | Command                               | Expected                       |
| -------------- | ------------------------------------- | ------------------------------ |
| CI Pipeline    | `scripts/ci_postgres.sh`              | GREEN (all tests pass)         |
| Docker Ready   | `docker compose up -d && curl /ready` | 200 with `migrations_ok: true` |
| SSE Stream     | `curl -H "X-Api-Key: ..." /v1/events` | Returns events JSON            |
| Auth Rejection | `curl -H "X-Api-Key: wrong" ...`      | 401 "Invalid credentials"      |

---

## Verification Result (2026-01-17)

```
✅ CI Pipeline:     444 passed, 1 skipped
✅ Docker /ready:   {"status":"ready","migrations_ok":true}
✅ SSE with auth:   Returns events
✅ Auth rejection:  401 Invalid credentials
```

---

## Quality Tools

| Tool      | Purpose                | Command                  |
| --------- | ---------------------- | ------------------------ |
| pytest    | Unit/Integration Tests | `python -m pytest`       |
| mypy      | Static Type Checking   | `mypy faim_native/`      |
| ruff      | Linting + Formatting   | `ruff check`             |
| bandit    | Security Scan          | `bandit -r faim_native/` |
| pip-audit | Dependency CVE Scan    | `pip-audit`              |
| black     | Code Formatter         | `black --check .`        |
| isort     | Import Sorter          | `isort --check-only .`   |

---

## Test Categories

| Category   | Count   | Purpose              |
| ---------- | ------- | -------------------- |
| Unit       | 180+    | Core logic isolation |
| Acceptance | 230+    | End-to-end flows     |
| Security   | 28      | Hashing, redaction   |
| **Total**  | **445** | Full coverage        |

---

## Scripts

| Script                            | Purpose                        |
| --------------------------------- | ------------------------------ |
| `scripts/verify.sh`               | Run all tests (fast)           |
| `scripts/ci_postgres.sh`          | Full CI pipeline with Postgres |
| `scripts/security_audit.sh`       | CVE + security scan            |
| `scripts/drill_backup_restore.sh` | Backup/restore verification    |

---

## Security Verification

```bash
# Run security audit
./scripts/security_audit.sh

# Outputs:
# 🔍 [1/3] pip-audit (CVE scanner)
# 🔍 [2/3] bandit (security linter)
# 🔍 [3/3] Hardcoded secrets check
```

---

## Migration Verification

```bash
# Check migration status
curl http://localhost:8000/ready | jq

# Expected:
{
  "status": "ready",
  "db_connected": true,
  "tables_ok": true,
  "migrations_ok": true,
  "latest_migration": 3,
  "applied_migration": 3
}
```
