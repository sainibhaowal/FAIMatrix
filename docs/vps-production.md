# VPS Command Book - One-Way Deploy Template

Use this runbook for a simple one-way deployment:

Local machine -> VPS -> Docker rebuild -> health check

This template avoids syncing heavy runtime files, caches, virtual environments,
and development-only folders.

## 1. Fill These Values First

| Item | Value |
| --- | --- |
| Project name | `FAIM` |
| Local project root | `/home/sephi-asi/FAIM` |
| VPS login | `root@144.91.118.196` |
| VPS app root | `/opt/faim/FAIM` |
| Compose working directory | `/opt/faim/FAIM` |
| Docker compose files | `docker-compose.yml` + `docker-compose.vps.yml` |
| VPS env file | `deploy/env.vpsprod` |
| Public domain | `https://faimatrix.com` |

Example values:

| Item | Example |
| --- | --- |
| Project name | `FAIM` |
| Local project root | `/home/sephi-asi/FAIM` |
| VPS login | `root@144.91.118.196` |
| VPS app root | `/opt/faim/FAIM` |
| Compose working directory | `/opt/faim/FAIM` |
| Docker compose files | `docker-compose.yml` + `docker-compose.vps.yml` |
| VPS env file | `deploy/env.vpsprod` |
| Public domain | `https://faimatrix.com` |

This repo is a single monorepo, so sync the repo root once. Do not split the
backend and frontend into separate deploy roots.

The VPS env file is self-describing, so direct `docker compose --env-file ...` commands work without a manual export.

## 2. One-Way Deploy Flow

Follow this exact order:

1. Sync the repo from the local machine to the VPS.
2. Copy the VPS env file to the VPS separately.
3. SSH into the VPS.
4. Validate Docker Compose config.
5. Rebuild and restart containers.
6. Check container status.
7. Check public health endpoints.
8. Check logs if something fails.

## 3. Sync Repo - Run On Local Machine

Use the repo sync helper:

```bash
./scripts/vps_sync.sh
```

Equivalent manual sync, if you need it:

```bash
rsync -av --delete \
  --exclude '.git/' \
  --exclude '.codex/' \
  --exclude '.github/' \
  --exclude '.vscode/' \
  --exclude '.ruff_cache/' \
  --exclude '__pycache__/' \
  --exclude '.venv/' \
  --exclude '.cache/' \
  --exclude '.pytest_cache/' \
  --exclude 'tests/' \
  --exclude 'docs/' \
  --exclude 'Docs/' \
  --exclude 'Runtime/' \
  --exclude 'node_modules/' \
  --exclude 'frontend/node_modules/' \
  --exclude 'frontend/.next/' \
  --exclude 'frontend/out/' \
  --exclude 'frontend/build/' \
  --exclude 'frontend/playwright-report/' \
  --exclude 'frontend/test-results/' \
  --exclude 'frontend/tsconfig.tsbuildinfo' \
  --exclude 'frontend/tests/' \
  --exclude 'frontend/e2e/' \
  --exclude 'faim_native/Docs/' \
  --exclude 'faim_native/faim-m/' \
  --exclude 'faim_native/store/raw/blobs/' \
  --exclude 'faim_native/full_test_log.txt' \
  --exclude 'scripts/pdf-generator/' \
  --exclude 'storage_prototype.html' \
  --exclude '.env' \
  --exclude '.env.localprod' \
  --exclude '.env.localprod.example' \
  --exclude 'deploy/env*.example' \
  --exclude 'deploy/env.vpsprod' \
  --exclude 'deploy/ssl/' \
  --exclude 'docs/simulation_run*.txt' \
  ./ root@144.91.118.196:/opt/faim/FAIM/
```

### Exclusions

The sync helper excludes generated and runtime-only paths:

- `.git`
- `.codex`
- `.github`
- `.vscode`
- `.ruff_cache`
- `__pycache__`
- `.venv`
- `.cache`
- `.pytest_cache`
- `tests`
- `docs`
- `Docs`
- `Runtime`
- `node_modules`
- `frontend/node_modules`
- `frontend/.next`
- `frontend/out`
- `frontend/build`
- `frontend/playwright-report`
- `frontend/test-results`
- `frontend/tsconfig.tsbuildinfo`
- `frontend/tests`
- `frontend/e2e`
- `faim_native/Docs`
- `faim_native/faim-m`
- `faim_native/store/raw/blobs`
- `faim_native/full_test_log.txt`
- `scripts/pdf-generator`
- `storage_prototype.html`
- `.env`
- `.env.localprod`
- `.env.localprod.example`
- `deploy/env*.example`
- `deploy/env.vpsprod`
- `deploy/ssl`
- `docs/simulation_run*.txt`

## 4. Sync VPS Env File - Run On Local Machine

Copy the real VPS secret file separately. The sync helper intentionally does
not copy it.

```bash
scp deploy/env.vpsprod root@144.91.118.196:/opt/faim/FAIM/deploy/env.vpsprod
```

## 5. SSH Into VPS

Run on your local machine:

```bash
ssh root@144.91.118.196
```

## 6. Deploy On VPS

Run on the VPS:

```bash
cd /opt/faim/FAIM

chmod 600 deploy/env.vpsprod

docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel config >/dev/null && echo "Compose config OK"

docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel up -d --build --remove-orphans

docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel ps
```

### Selective Rebuilds

Use these when only one area changed. This avoids a full rebuild.

```bash
# Frontend only
./scripts/vps_up.sh frontend

# Backend API only
./scripts/vps_up.sh api

# Worker only
./scripts/vps_up.sh worker

# Schema or migration changes
./scripts/vps_up.sh migrate api worker
```

If you prefer direct compose commands on the VPS:

```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel build frontend
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel up -d --no-deps frontend

docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel build api worker
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel up -d --no-deps api worker

docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel run --rm --build migrate
```

## 7. Health Check

Run from local machine or VPS:

```bash
curl -fsS https://faimatrix.com/health && echo
curl -fsS https://faimatrix.com/ready && echo
curl -fsS https://faimatrix.com/version && echo
```

Expected result:

```txt
All commands should return a successful response without curl errors.
```

## 8. Logs If Something Fails

Run on the VPS:

```bash
cd /opt/faim/FAIM

docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel logs --tail=100 api frontend caddy
```

Follow logs live:

```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel logs -f api frontend caddy
```

## 9. Hard Restart If Needed

Use only if the normal deploy does not fix the issue.

Run on the VPS:

```bash
cd /opt/faim/FAIM

docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel down

docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel up -d --build --remove-orphans

docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel ps
```

## 10. Docker Storage Check

Run on the VPS before cleanup:

```bash
docker system df
docker system df -v
docker ps -a
docker images
docker volume ls
```

## 11. Safe Cleanup

Run on the VPS:

```bash
docker builder prune -f
docker system prune -f
```

This removes old build cache, stopped containers, unused networks, and dangling artifacts.

## 12. Strong Cleanup

Run only when disk space is low:

```bash
docker image prune -a -f
```

This removes unused Docker images not currently used by running containers.

## 13. Dangerous Cleanup

Do not run this unless you are sure your database and storage volumes are safe:

```bash
docker volume prune -f
```

This can delete persistent data volumes.

## 14. Final One-Way Command Sequence

Use this as the main deploy sequence.

### Local machine

```bash
./scripts/vps_sync.sh
scp deploy/env.vpsprod root@144.91.118.196:/opt/faim/FAIM/deploy/env.vpsprod
ssh root@144.91.118.196
```

### VPS

```bash
cd /opt/faim/FAIM

chmod 600 deploy/env.vpsprod

docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel config >/dev/null && echo "Compose config OK"

docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel up -d --build --remove-orphans

docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml --profile accel ps
```

### Health check

```bash
curl -fsS https://faimatrix.com/health && echo
curl -fsS https://faimatrix.com/ready && echo
```

## 15. Rules

- This is one-way only: local machine to VPS.
- Do not copy runtime data from local to VPS.
- Do not copy models unless explicitly required.
- Do not copy `.venv`, `node_modules`, `.next`, caches, or tests.
- Use `--delete` carefully because it makes the VPS match your local deploy folder.
- Keep `deploy/env.vpsprod` on the VPS and do not overwrite it from local sync.
- Run rsync commands locally.
- Run Docker commands on the VPS.
- Check health endpoints after every deployment.
- Do not use `git pull` on the VPS for production updates.
