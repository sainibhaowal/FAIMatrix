# Stage-10.1 Report: Production Deployment Pack

## Status: ✅ COMPLETE

**Date:** 2026-01-17  
**Commits:** `a4d6413`, `d62d7a0`, `bae9d42`, `4aec5aa`, `d5c651c`

---

## Overview

Stage-10.1 hardens FAIM-Native for production deployment with:

- Operator-controlled migrations
- No secrets in version control
- Startup gating (API refuses to start if schema is behind)
- Optional acceleration services

---

## Verification Results

**CI Pipeline (`scripts/ci_postgres.sh`):**

- **Tests**: 416 PASSED, 1 SKIPPED
- **Migrations**: Applied successfully
- **Backup Drill**: Completed (dump → restore → verify)
- **Exit Code**: 0 (SUCCESS)

---

## Deliverables

### 1. `dev.sh` — Native Migration Runner

- Replaced `alembic upgrade head` with `python -m store.pg.migrate up`

### 2. `docker-compose.yml` — Production Hardened

| Feature              | Implementation                                   |
| -------------------- | ------------------------------------------------ |
| No hardcoded secrets | `env_file: .env` + `${VAR}` syntax               |
| Safe default         | `FAIM_AUTO_MIGRATE: ${FAIM_AUTO_MIGRATE:-false}` |
| One-shot migrate     | `migrate:` service                               |
| Optional accel       | `profiles: ["accel"]` for Redis/Qdrant           |
| Healthcheck          | `/ready` endpoint check                          |

### 3. `Dockerfile` — Full Context Build

- `COPY . /app`
- `ENV PYTHONPATH=/app/faim_native:/app`
- `ENTRYPOINT ["/app/scripts/entrypoint.sh"]`
- Non-root user `faim`

### 4. `scripts/entrypoint.sh` — Startup Gating

- `FAIM_AUTO_MIGRATE=true` → runs migrations
- `FAIM_AUTO_MIGRATE=false` → runs `--require-latest`, fails if behind

### 5. `env.template` — Safe Defaults

- `FAIM_AUTO_MIGRATE=false`

### 6. `scripts/ci_postgres.sh` — Release Gate

- Starts Postgres container
- Runs migrations
- Runs full test suite
- Runs backup drill
- Cleans up

---

## Production Lifecycle

```bash
# 1. Build
docker compose build

# 2. Migrate (one-shot, operator-controlled)
docker compose run --rm migrate

# 3. Start
docker compose up -d

# 4. (Optional) With acceleration
docker compose --profile accel up -d
```

**Safety Guarantee:** If you skip step 2, the API container exits with code 1.

---

## Requirement Checklist

| Requirement                     | Status |
| ------------------------------- | ------ |
| No alembic in dev.sh            | ✅     |
| No secrets in YAML              | ✅     |
| FAIM_AUTO_MIGRATE=false default | ✅     |
| One-shot migrate service        | ✅     |
| Accel profiles                  | ✅     |
| COPY . /app in Dockerfile       | ✅     |
| Entrypoint gating               | ✅     |
| CI script                       | ✅     |
| .dockerignore allows \*.sql     | ✅     |
| CI pipeline passes              | ✅     |

---

## Files Changed

- `dev.sh` — Native migration command
- `docker-compose.yml` — Production hardening
- `Dockerfile` — Full context + entrypoint
- `env.template` — Safe defaults
- `scripts/entrypoint.sh` — NEW: Startup gating
- `scripts/ci_postgres.sh` — NEW: CI release gate
- `.dockerignore` — Allow \*.sql migrations
