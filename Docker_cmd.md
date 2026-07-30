# FAIMatrix Docker Commands & Operations Reference

This guide provides the complete DevOps reference and command sheet for **Local Development**, **Testing**, and **VPS Production** environments.

---

## Environment & File Architecture

| Target Environment | Compose Configuration | Environment File | Access / Domain |
| :--- | :--- | :--- | :--- |
| **Local Development** | `docker-compose.yml` | `.env` (from `env.template`) | `http://localhost:8010` |
| **VPS Production** | `docker-compose.yml` + `docker-compose.vps.yml` | `deploy/env.vpsprod` | `https://faimatrix.com` |
| **Automated Testing** | `docker-compose.test.yml` | `.env` | Isolated test ports |

---

## 1. Environment File Setup

Before launching, copy the template files to create your active environment files:

### Local Development
```bash
cp env.template .env
```

### VPS Production
```bash
cp deploy/env.vpsprod.example deploy/env.vpsprod
```

---

## 2. Local Development Commands

Commands use the standard `docker-compose.yml` file and `.env` config.

### Start All Local Services
```bash
docker compose up -d --remove-orphans
```

### Build & Start (After code changes)
```bash
docker compose up -d --build --remove-orphans
```

### View Live Logs
```bash
docker compose logs -f
```

### Restart a Specific Container (e.g. API or Frontend)
```bash
docker compose restart api
docker compose restart frontend
```

### Stop All Services
```bash
docker compose down
```

### Run Migrations
```bash
docker compose run --rm -e FAIM_AUTO_MIGRATE=true migrate
```

---

## 3. VPS Production Commands

VPS commands combine `docker-compose.yml` and `docker-compose.vps.yml` with `deploy/env.vpsprod`.

### Convenient Helper Scripts (Recommended on VPS)

```bash
# Deploy / Start VPS Stack
./scripts/vps_up.sh

# Stop VPS Stack
./scripts/vps_down.sh

# Run Health & Smoke Tests on VPS
./scripts/vps_smoke.sh

# Backup VPS Database & State
./scripts/vps_backup.sh
```

### Direct Compose Commands for VPS

#### Start VPS Production
```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml up -d --build --remove-orphans
```

#### Rebuild Only Changed Services (e.g. Frontend or API)
```bash
# Rebuild Frontend only
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml build frontend
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml up -d --no-deps frontend

# Rebuild API only
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml build api
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml up -d --no-deps api
```

#### View Production Logs
```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml logs -f api worker frontend caddy
```

#### Stop VPS Production
```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml down
```

---

## 4. Pre-Deployment Quality Checks (Run Locally First)

Before pushing code to GitHub or deploying to VPS, run these local verification checks:

```bash
# 1. Typecheck TypeScript / Next.js
npm run tsc

# 2. Lint Frontend Code
npm run eslint

# 3. Spin up test stack & run tests
docker compose -f docker-compose.test.yml up -d
pytest tests/
docker compose -f docker-compose.test.yml down -v
```

---

## 5. Database Backup & Restore Operations

### Local Database Operations

```bash
# Export / Backup Local Postgres Database
docker exec -t faim-postgres pg_dump -U faim faim_native > backup_local.sql

# Restore Local Postgres Database
cat backup_local.sql | docker exec -i faim-postgres psql -U faim -d faim_native
```

### VPS Database Operations

```bash
# Export / Backup VPS Postgres Database
docker exec -t faim-postgres-vps pg_dump -U faim faim_native > backup_vps.sql

# Restore VPS Postgres Database
cat backup_vps.sql | docker exec -i faim-postgres-vps psql -U faim -d faim_native
```

---

## 6. End-to-End Deployment Workflow (Local -> VPS)

To deploy new code changes from your PC to your VPS:

```bash
# Step 1: Commit and push changes locally
git add .
git commit -m "feat: new feature update"
git push origin main

# Step 2: SSH into VPS server and update stack
ssh root@your-vps-ip
cd /opt/faim/FAIM
git pull origin main
./scripts/vps_up.sh
./scripts/vps_smoke.sh
```

---

## 7. Container Shell & Resource Inspection

```bash
# Open interactive shell inside API container
docker exec -it faim-api bash

# Open interactive shell inside Postgres container
docker exec -it faim-postgres psql -U faim -d faim_native

# Check realtime CPU & Memory usage of containers
docker stats
```

---

## 8. Docker Cleanup & Maintenance (Pruning)

Use these commands to free up disk space by removing unused containers, images, build caches, and volumes:

### Quick Cleanup (Safe)
Removes stopped containers, dangling images, and unused networks without deleting data volumes:
```bash
docker system prune -f
```

### Clear Build Cache
Clears cached layer data from Docker builds:
```bash
# Remove unused build cache
docker builder prune -f

# Remove ALL build cache (deep clean)
docker builder prune -a -f
```

### Remove Unused Images
```bash
# Remove dangling (un-tagged) images
docker image prune -f

# Remove ALL unused images (not just dangling ones)
docker image prune -a -f
```

### Remove Unused Volumes
⚠️ **Caution:** This will delete any Docker volumes not currently attached to a running container.
```bash
docker volume prune -f
```

### Complete Deep Clean (All-in-One)
⚠️ **Warning:** Deletes all stopped containers, unused networks, all unused images, and unused volumes.
```bash
docker system prune -af --volumes
```
