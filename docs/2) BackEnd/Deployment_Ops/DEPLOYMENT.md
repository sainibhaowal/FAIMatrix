# FAIM-Native Deployment Guide

> Updated for Stage-10.1 Production Deployment Pack

## Quick Start (Docker Compose)

```bash
# 1. Configure environment
cp env.template .env
# Edit .env with your secrets

# 2. Build
docker compose build

# 3. Migrate (one-shot, operator-controlled)
docker compose run --rm migrate

# 4. Start
docker compose up -d

# 5. Verify
curl http://localhost:8000/ready
```

## Production Environment Requirements

- **Docker 24.0+** and **Docker Compose v2.20+**
- **PostgreSQL 15**: Primary transactional store (included in compose)
- **Redis 7+**: Optional acceleration cache (`--profile accel`)
- **Qdrant**: Optional vector database (`--profile accel`)

## Configuration

Copy `env.template` to `.env` and set:

| Variable            | Required   | Description       |
| ------------------- | ---------- | ----------------- |
| `POSTGRES_PASSWORD` | Yes        | Database password |
| `TENANT_KEYS_JSON`  | Yes        | Tenant API keys   |
| `ADMIN_KEYS_JSON`   | Yes        | Admin API keys    |
| `REDIS_PASSWORD`    | Accel only | Redis password    |
| `QDRANT_API_KEY`    | Accel only | Qdrant API key    |

## Migration Strategy

| Variable            | Default | Behavior                                                                                                 |
| ------------------- | ------- | -------------------------------------------------------------------------------------------------------- |
| `FAIM_AUTO_MIGRATE` | `false` | If `true`, API applies migrations on startup. If `false`, API refuses to start unless schema is current. |

**Production (Recommended):**

```bash
docker compose run --rm migrate
docker compose up -d
```

**Development:**

```bash
FAIM_AUTO_MIGRATE=true docker compose up -d
```

## Services

### Default (always start)

- `postgres`: PostgreSQL 15 database
- `api`: FAIM-Native API server
- `worker`: Background job processor

### Optional (`--profile accel`)

- `redis`: Redis cache
- `qdrant`: Vector database

## Hardening Checklist

- [x] `FAIM_AUTO_MIGRATE=false` by default
- [x] No secrets in `docker-compose.yml`
- [x] Entrypoint gating (refuses start if schema behind)
- [x] Non-root container user
- [ ] Rotate `TENANT_KEYS_JSON` and `ADMIN_KEYS_JSON` periodically
- [ ] Enable firewall for internal components
- [ ] Configure volume backups

## Health Check

```bash
curl http://localhost:8000/ready
```

Response:

```json
{ "status": "ready", "db_connected": true, "migrations_ok": true }
```

## CI/CD Integration

Use `scripts/ci_postgres.sh` for release validation:

```bash
./scripts/ci_postgres.sh
```

## Manual Deployment (No Docker)

1. Set environment variables from `env.template`
2. Apply migrations: `python3 -m store.pg.migrate up`
3. Start API: `uvicorn api.app:app --host 0.0.0.0 --port 8000`
4. Start Worker: `python3 -m orchestration.jobs.worker`
