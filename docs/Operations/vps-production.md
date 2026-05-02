# VPS Production

This is the production deployment path for the public FAIM server at
`https://faimatrix.com`.

The VPS stack keeps the same application code and migration flow as local
production, but it uses its own compose override, env file, and Caddy config.

## Files

- [docker-compose.vps.yml](/home/sephi-asi/FAIM/docker-compose.vps.yml)
- [deploy/Caddyfile.vps](/home/sephi-asi/FAIM/deploy/Caddyfile.vps)
- [deploy/env.vps.example](/home/sephi-asi/FAIM/deploy/env.vps.example)
- [scripts/vps_sync.sh](/home/sephi-asi/FAIM/scripts/vps_sync.sh)
- [scripts/vps_up.sh](/home/sephi-asi/FAIM/scripts/vps_up.sh)
- [scripts/vps_down.sh](/home/sephi-asi/FAIM/scripts/vps_down.sh)
- [scripts/vps_smoke.sh](/home/sephi-asi/FAIM/scripts/vps_smoke.sh)
- [scripts/vps_backup.sh](/home/sephi-asi/FAIM/scripts/vps_backup.sh)
- [scripts/vps_restore.sh](/home/sephi-asi/FAIM/scripts/vps_restore.sh)

## VPS Layout

- Caddy listens on public ports `80` and `443`.
- The API, worker, Postgres, Redis, and Qdrant are not published directly.
- Application data lives under `Runtime/vps/` on the server.
- Backups are written to `Runtime/vps/backups/`.
- Caddy uses automatic public TLS for `faimatrix.com`.

## First-Time Login

```bash
ssh root@144.91.118.196
```

If you are not root on the server, replace the user and host with your real
admin account and IP.

## Sync Options

### Recommended: Sync From Your Workstation

```bash
./scripts/vps_sync.sh
```

By default this pushes the current workspace to:

```text
root@144.91.118.196:/opt/faim/FAIM
```

### Exclusions

The sync helper excludes generated and runtime-only paths:

- `.git`
- `.env`
- `.venv`
- `node_modules`
- `frontend/node_modules`
- `frontend/.next`
- `frontend/out`
- `frontend/build`
- `frontend/playwright-report`
- `frontend/test-results`
- `frontend/tsconfig.tsbuildinfo`
- `Runtime`
- `faim_native/full_test_log.txt`
- `docs/simulation_run*.txt`

### Alternative: Pull On The Server

If the server already has the repo cloned, you can update it there instead of
syncing from your workstation:

```bash
cd /opt/faim/FAIM
git pull --ff-only
```

## Environment

```bash
cp deploy/env.vps.example .env
```

Required values:

- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `QDRANT_API_KEY`
- `NEXTAUTH_SECRET`
- `RESEND_API_KEY`
- `FAIM_ADMIN_KEY`
- `TENANT_KEYS_JSON`
- `ADMIN_KEYS_JSON`

## Build And Start

From the server shell:

```bash
npm run faim:vps:up
```

That command:

1. Creates the server runtime directories.
2. Runs migrations.
3. Builds the images.
4. Starts the stack behind Caddy.

If you want the explicit Docker commands:

```bash
docker compose -f docker-compose.yml -f docker-compose.vps.yml --profile accel run --rm --build migrate
docker compose -f docker-compose.yml -f docker-compose.vps.yml --profile accel up -d --build
```

## Smoke Test

```bash
npm run faim:vps:smoke
```

That checks:

- `/health`
- `/ready`
- `/version`
- the public frontend root

## Backup

```bash
npm run faim:vps:backup
```

Backups are stored in `Runtime/vps/backups/`:

- `backup_faim_*.sql.gz`
- `raw_*.tar.gz`

## Restore

```bash
npm run faim:vps:restore
```

The restore helper:

1. Stops the stack.
2. Restores the latest database backup unless you pass a file path.
3. Restores the latest raw archive unless you pass a file path.
4. Brings the stack back up.

## Update Flow

Use one of these two flows:

### Sync Flow

```bash
./scripts/vps_sync.sh
ssh root@144.91.118.196
cd /opt/faim/FAIM
npm run faim:vps:up
```

### Git Pull Flow

```bash
ssh root@144.91.118.196
cd /opt/faim/FAIM
git pull --ff-only
npm run faim:vps:up
```

## Safety Rules

- Do not expose the API or database ports directly on the VPS.
- Do not reuse the local-production Caddy config on the VPS.
- Do not enable wildcard CORS in production.
- Do not commit secrets into the sync path.
- Do not skip the smoke test after deploy.
