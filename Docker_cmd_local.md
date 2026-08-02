# FAIMatrix Local Development Commands Reference (PC)

This reference guide is dedicated exclusively for **Local Development on your PC**.

---

## 1. Environment Setup (Local PC)

Create your local `.env` configuration from template:

```bash
cp env.template .env
```

* **Local Base URL**: `http://localhost:8010`
* **Local API URL**: `http://localhost:8000`

---

## 2. Daily Development Commands

### 🟢 Start Local Environment
```bash
docker compose up -d
```

### ⚡ Build, Deploy & Clean (Daily Recommended Command)
Rebuilds updated code and automatically removes dangling image layers (`<none>:<none>`):
```bash
docker compose up -d --build && docker image prune -f
```

### 🔥 Hot Code Reload (Without Restarting Postgres or Redis)
```bash
docker compose up -d --build --no-deps api frontend worker && docker image prune -f
```

### 🛠️ Structure Update (Use ONLY when renaming/deleting services in docker-compose.yml)
```bash
docker compose up -d --build --remove-orphans && docker image prune -f
```

---

## 3. Pre-Push Quality Checks

Run these commands locally on your PC before committing and pushing to GitHub:

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

## 4. Git Commit & Push Workflow (PC ➡️ GitHub)

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat(ui): update dashboard layout and styling"

# Push to GitHub main branch
git push origin main
```

---

## 5. Local Database Backup & Restore

```bash
# Export / Backup Local Postgres Database
docker exec -t faim-postgres pg_dump -U faim faim_native > backup_local.sql

# Restore Local Postgres Database
cat backup_local.sql | docker exec -i faim-postgres psql -U faim -d faim_native
```

---

## 6. Logs & Container Inspection

```bash
# View live streaming logs for all containers
docker compose logs -f

# View live streaming logs for API & Frontend
docker compose logs -f --tail=100 api frontend

# Open interactive shell in API container
docker exec -it faim-api bash

# Open interactive shell in Postgres container
docker exec -it faim-postgres psql -U faim -d faim_native

# Check realtime CPU & Memory usage
docker stats
```

---

## 7. Prune Flags Reference (`-f` vs `-a`)

| Flag | Meaning | What it does |
| :--- | :--- | :--- |
| **`-f`** | **Force** | Runs without asking for interactive `[y/N]` confirmation. |
| **`-a`** | **All** | Deletes **all** unused images/caches, not just untagged dangling ones. |

### Local Prune Maintenance Schedule

```bash
# 🟢 DAILY (Combined with Deploy):
docker compose up -d --build && docker image prune -f

# 🧹 WEEKLY (Build Cache Clean):
docker builder prune -f

# 🧼 MONTHLY (System Scrub):
docker system prune -f
```
