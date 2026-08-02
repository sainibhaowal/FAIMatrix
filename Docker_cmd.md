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

Before launching services, prepare your environment configuration files:

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

Commands use `docker-compose.yml` and `.env`.

### 🟢 Start Local Stack
```bash
docker compose up -d
```

### ⚡ Rebuild & Auto-Clean (Daily Development Command)
Rebuilds updated code and immediately cleans leftover untagged image layers:
```bash
docker compose up -d --build && docker image prune -f
```

### 🔥 Hot Code Reload (No Database Restart)
Rebuilds only application code containers without restarting PostgreSQL or Redis connections:
```bash
docker compose up -d --build --no-deps api frontend worker && docker image prune -f
```

### 🔍 View Streaming Logs
```bash
# All containers
docker compose logs -f

# Specific containers (e.g. API and Frontend)
docker compose logs -f --tail=100 api frontend
```

### 🔄 Restart a Container
```bash
docker compose restart api
docker compose restart frontend
```

### 🛑 Stop All Local Services
```bash
docker compose down
```

### 🔄 Run Database Migrations
```bash
docker compose run --rm -e FAIM_AUTO_MIGRATE=true migrate
```

---

## 3. VPS Production Commands

VPS commands combine `docker-compose.yml` and `docker-compose.vps.yml` with `deploy/env.vpsprod`.

### Helper Scripts (Recommended on VPS)
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

#### 🚀 Production Deploy & Auto-Clean (Daily Standard)
```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml up -d --build && docker image prune -f
```

#### 🛠️ Structure Update Deploy (When Renaming/Deleting Services in Compose)
Use `--remove-orphans` **only** when modifying `docker-compose.yml` service definitions:
```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml up -d --build --remove-orphans && docker image prune -f
```

#### ⚡ Zero-Downtime Hot Reload (Frontend or API Only)
```bash
# Rebuild Frontend only without touching DB or Redis
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml up -d --build --no-deps frontend && docker image prune -f

# Rebuild API only
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml up -d --build --no-deps api && docker image prune -f
```

#### 📊 View Production Logs
```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml logs -f --tail=100 api worker frontend caddy
```

#### 🛑 Stop VPS Production
```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml down
```

---

## 4. Pre-Deployment Quality Checks (Run Locally First)

Before pushing code to GitHub or deploying to VPS:

```bash
# 1. Typecheck TypeScript / Next.js
npm --prefix frontend run typecheck

# 2. Lint Frontend Code
npm --prefix frontend run lint

# 3. Spin up test stack & run Pytest suite
docker compose -f docker-compose.test.yml up -d
pytest tests/
docker compose -f docker-compose.test.yml down -v
```

---

## 5. BuildKit Caching Optimization (`# syntax=docker/dockerfile:1.7`)

Both project Dockerfiles use modern BuildKit cache mounts (`--mount=type=cache`) to ensure incremental builds re-download **only updated packages**:

* **Python Dockerfile (`Dockerfile`)**:
  ```dockerfile
  # syntax=docker/dockerfile:1.7
  RUN --mount=type=cache,target=/root/.cache/pip \
      pip install --default-timeout=100 -r requirements.txt ...
  ```
* **Frontend Dockerfile (`frontend/Dockerfile`)**:
  ```dockerfile
  # syntax=docker/dockerfile:1.7
  RUN --mount=type=cache,target=/root/.npm \
      npm install --legacy-peer-deps
  ```

---

## 6. Production Maintenance & Pruning Calendar

Maintain disk space and prevent buildup of old image layers with this routine:

| Frequency | Routine Task | Command |
| :--- | :--- | :--- |
| **Daily** | Auto-clean dangling build layers after deploy | `docker image prune -f` |
| **Weekly** | Clear BuildKit intermediate build cache | `docker builder prune -f` |
| **Monthly** | Perform full system scrub (unused networks/containers) | `docker system prune -f` |

```bash
# 🟢 DAILY (Combined with Deploy):
docker compose up -d --build && docker image prune -f

# 🧹 WEEKLY (Build Cache Clean):
docker builder prune -f

# 🧼 MONTHLY (System Scrub):
docker system prune -f
```

---

## 7. Database Backup & Restore Operations

### Local Database
```bash
# Export / Backup Local Postgres Database
docker exec -t faim-postgres pg_dump -U faim faim_native > backup_local.sql

# Restore Local Postgres Database
cat backup_local.sql | docker exec -i faim-postgres psql -U faim -d faim_native
```

### VPS Database
```bash
# Export / Backup VPS Postgres Database
docker exec -t faim-postgres-vps pg_dump -U faim faim_native > backup_vps.sql

# Restore VPS Postgres Database
cat backup_vps.sql | docker exec -i faim-postgres-vps psql -U faim -d faim_native
```

---

## 8. Shell & Resource Inspection

```bash
# Interactive shell inside API container
docker exec -it faim-api bash

# Interactive shell inside Postgres container
docker exec -it faim-postgres psql -U faim -d faim_native

# Realtime CPU, Memory & Network stats of all containers
docker stats
```

---

## 9. End-to-End Deployment Flow (PC ➡️ VPS)

```bash
# Step 1: Run local checks, commit and push to GitHub
git add .
git commit -m "feat(ui): update production dashboard layout"
git push origin main

# Step 2: SSH into VPS server and update live stack (using --ff-only for zero merge conflicts)
ssh root@your-vps-ip
cd /opt/faim/FAIM
git pull --ff-only origin main
./scripts/vps_up.sh
./scripts/vps_smoke.sh
```
