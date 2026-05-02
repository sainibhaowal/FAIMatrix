# FAIM-Native Production Deployment Guide

> Stage-10.1: Production Deployment Pack

This guide explains how to deploy FAIM-Native in a production environment using Docker Compose.

## Prerequisites

- Docker 24.0+
- Docker Compose v2.20+
- A `.env` file with required secrets (see [Configuration](#configuration))

## Quick Start

```bash
# 1. Copy and configure environment
cp env.template .env
# Edit .env with your secrets

# 2. Build the image
docker compose build

# 3. Run migrations (one-shot, operator-controlled)
docker compose run --rm migrate

# 4. Start services
docker compose up -d

# 5. Verify
curl http://localhost:8000/ready
```

## Local Production

Local production currently uses the `:8443` HTTPS edge on this host because
port `443` is already allocated by another service.

`deploy/env.localprod.example` is a template only. It is not read directly at
runtime. Copy it to the root `.env` on the local-prod machine, then replace all
placeholder values with real local-production secrets.

Local production uses the same containers and app behavior, but routes traffic
through Caddy on `https://faimatrix.localhost:8443`.

```bash
# 1. Configure local-production env values
cp deploy/env.localprod.example .env

# 2. Start the local production stack
npm run faim:localprod:up

# 3. Smoke test the edge and readiness path
npm run faim:localprod:smoke
```

Local production files:

- [docker-compose.localprod.yml](/home/sephi-asi/FAIM/docker-compose.localprod.yml)
- [deploy/Caddyfile.localprod](/home/sephi-asi/FAIM/deploy/Caddyfile.localprod)
- [deploy/env.localprod.example](/home/sephi-asi/FAIM/deploy/env.localprod.example)
- [docs/Operations/github-branch-protection.md](/home/sephi-asi/FAIM/docs/Operations/github-branch-protection.md)

## VPS Production

`deploy/env.vps.example` is a template only. It is not read directly at
runtime. Copy it to the root `.env` on the VPS, then replace all placeholder
values with real VPS-production secrets.

The VPS path uses the public production domain `https://faimatrix.com` and its
own compose/Caddy/env set. See the dedicated runbook:

- [docs/Operations/vps-production.md](/home/sephi-asi/FAIM/docs/Operations/vps-production.md)
- [docker-compose.vps.yml](/home/sephi-asi/FAIM/docker-compose.vps.yml)
- [deploy/Caddyfile.vps](/home/sephi-asi/FAIM/deploy/Caddyfile.vps)
- [deploy/env.vps.example](/home/sephi-asi/FAIM/deploy/env.vps.example)

## Configuration

Copy `env.template` to `.env` and set the following required values:

| Variable            | Description       | Example                         |
| ------------------- | ----------------- | ------------------------------- |
| `POSTGRES_PASSWORD` | Database password | `secure_random_password`        |
| `TENANT_KEYS_JSON`  | Tenant API keys   | `{"tenant1": ["key1", "key2"]}` |
| `ADMIN_KEYS_JSON`   | Admin API keys    | `{"admin": "admin_key"}`        |
| `FAIM_ADMIN_KEY`    | Backend admin key  | `secure_admin_key`              |
| `FAIM_ADMIN_EMAILS_JSON` | Admin UI allowlist | `["admin@example.com"]` |
| `RESEND_API_KEY` | OTP + admin alert email delivery | `re_...` |

### Optional (Acceleration Profile)

| Variable         | Description                         |
| ---------------- | ----------------------------------- |
| `REDIS_PASSWORD` | Redis password (required for accel) |
| `QDRANT_API_KEY` | Qdrant API key (required for accel) |

### Migration Behavior

| Variable            | Default | Behavior                                                                                                 |
| ------------------- | ------- | -------------------------------------------------------------------------------------------------------- |
| `FAIM_AUTO_MIGRATE` | `false` | If `true`, API applies migrations on startup. If `false`, API refuses to start unless schema is current. |

## Services

### Default Services (always start)

```bash
docker compose up -d
```

- **postgres**: PostgreSQL 15 database
- **api**: FAIM-Native API server
- **worker**: Background job processor

### Optional Acceleration Services

```bash
docker compose --profile accel up -d
```

- **redis**: Redis cache (for query caching)
- **qdrant**: Vector database (for semantic indexing)

## Migration Strategy

### Production (Recommended)

```bash
# Explicit operator-controlled migration
docker compose run --rm migrate
docker compose up -d
```

The API will **refuse to start** if migrations are pending. This prevents schema drift in multi-instance deployments.

### Development (Convenience)

```bash
# Set in .env
FAIM_AUTO_MIGRATE=true
docker compose up -d
```

The API will automatically apply migrations on startup.

## Health Checks

The API exposes a `/ready` endpoint for health checks:

```bash
curl http://localhost:8000/ready
```

Response:

```json
{
  "status": "ready",
  "db_connected": true,
  "tables_ok": true,
  "migrations_ok": true
}
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   API :8000 │────▶│  Postgres   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              ┌─────────┐   ┌─────────┐
              │  Redis  │   │ Qdrant  │
              │ (accel) │   │ (accel) │
              └─────────┘   └─────────┘
```

## Security

- **No secrets in YAML**: All sensitive values come from `.env`
- **Non-root user**: Containers run as `faim` user (UID 1000)
- **Migration gating**: API refuses to start with stale schema
- **Advisory locks**: Only one migration can run at a time

## Troubleshooting

### API exits immediately

The schema is behind. Run migrations:

```bash
docker compose run --rm migrate
```

### Cannot connect to database

Check Postgres is healthy:

```bash
docker compose ps postgres
docker compose logs postgres
```

### Migrations fail

Check migration logs:

```bash
docker compose logs migrate
```

## Staging And Rollback

See [staging-rollback.md](/home/sephi-asi/FAIM/docs/Operations/staging-rollback.md)
for the staging baseline and rollback drill.

## SLO And Security

See [slo-runbook.md](/home/sephi-asi/FAIM/docs/Operations/slo-runbook.md) and
[security-hardening.md](/home/sephi-asi/FAIM/docs/Operations/security-hardening.md)
for production operating expectations.

## CI/CD Integration

Use `scripts/ci_postgres.sh` for release validation:

```bash
./scripts/ci_postgres.sh
```

This script:

1. Starts a fresh Postgres container
2. Runs migrations
3. Runs the full test suite
4. Runs a backup/restore drill
5. Cleans up

## Backup And Restore

Local production backup and restore helpers:

```bash
npm run faim:localprod:backup
npm run faim:localprod:restore
```

The local production backup flow stores:

- PostgreSQL dumps in `Runtime/localprod/backups`
- Raw blob archives in `Runtime/localprod/backups`

## File Reference

| File                     | Purpose                        |
| ------------------------ | ------------------------------ |
| `docker-compose.yml`     | Production service definitions |
| `docker-compose.dev.yml` | Development overrides          |
| `Dockerfile`             | Container image build          |
| `scripts/entrypoint.sh`  | Startup gating script          |
| `scripts/ci_postgres.sh` | CI release gate                |
| `env.template`           | Environment variable template  |
