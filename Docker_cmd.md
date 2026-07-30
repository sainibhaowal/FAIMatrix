# FAIMatrix Docker Commands Reference

This guide provides the official Docker commands for managing **Local Development** and **VPS Production** environments.

---

## Environment & File Architecture

| Target Environment | Compose Configuration | Environment File | Domain / Port |
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

# Run Smoke Tests on VPS
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

## 4. Testing Environment Commands

Run tests in isolated containers without affecting live data:

```bash
# Spin up test infrastructure
docker compose -f docker-compose.test.yml up -d

# Tear down test infrastructure
docker compose -f docker-compose.test.yml down -v
```

---

## 5. Docker Cleanup & Maintenance (Pruning)

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

