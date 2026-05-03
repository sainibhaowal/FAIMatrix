# Docker Commands (Production)

This file matches the production deployment model used by FAIM:

- Local production uses `docker-compose.yml` + `docker-compose.localprod.yml`
- VPS production uses `docker-compose.yml` + `docker-compose.vps.yml`
- Each target uses one real env file:
  - local prod: `.env.localprod`
  - VPS prod: `deploy/env.vpsprod`

Run all commands from repo root:

```bash
cd /home/sephi-asi/FAIM
```

## 1) Prepare Env Files

Create the real env file for the target you are running:

```bash
cp .env.localprod.example .env.localprod
cp deploy/env.vpsprod.example deploy/env.vpsprod
```

## 2) Pull Base Infra Images

Use this when you want the latest Postgres, Redis, and Qdrant images.

### Local production

```bash
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel pull postgres redis qdrant
```

### VPS production

```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel pull postgres redis qdrant
```

## 3) Full Build

Use this after larger backend, frontend, or worker changes.

Use a full build only when Dockerfiles, package manifests, compose files, or base dependencies change.

### Local production

```bash
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel build --pull api worker frontend migrate
```

### VPS production

```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel build --pull api worker frontend migrate
```

## 4) Build Only What Changed

### Backend API only

```bash
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel build api
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel up -d --no-deps api
```

### Frontend only

```bash
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel build frontend
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel up -d --no-deps frontend
```

### Worker only

```bash
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel build worker
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel up -d --no-deps worker
```

### Migration service only

```bash
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel build migrate
```

### VPS production

The VPS helper accepts service names, so you can rebuild only what changed.

```bash
./scripts/vps_up.sh frontend
./scripts/vps_up.sh api
./scripts/vps_up.sh worker
./scripts/vps_up.sh migrate api worker
```

Equivalent direct compose commands:

```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel build frontend
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel up -d --no-deps frontend

docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel build api worker
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel up -d --no-deps api worker

docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel run --rm --build migrate
```

## 5) Run Migrations

Run this after DB model or migration changes.

```bash
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel run --rm -e FAIM_AUTO_MIGRATE=true migrate
```

## 6) Start All Servers

### Local production

```bash
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel up -d
```

### VPS production

```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel up -d --build --remove-orphans
```

## 7) Stop All Servers

### Local production

```bash
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel down
```

### VPS production

```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel down
```

## 8) Quick Checks

### Local production

```bash
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel ps
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel logs -f api worker frontend
```

### VPS production

```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel ps
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel logs -f api worker frontend caddy
```

## 9) Hard Reset

Use only when you want to delete containers and start fresh.

### Local production

```bash
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel down -v
docker compose --env-file .env.localprod -f docker-compose.yml -f docker-compose.localprod.yml --profile accel up -d
```

### VPS production

```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel down -v
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel up -d --build --remove-orphans
```

## 10) Source of Truth

For VPS deployments, use [`docs/vps-production.md`](/home/sephi-asi/FAIM/docs/vps-production.md) as the authoritative one-way deploy runbook.
This file is the command reference that matches that flow.
