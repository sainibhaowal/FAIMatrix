# FAIMatrix VPS Production Commands Reference (Server)

This reference guide is dedicated exclusively for **VPS Production Server Deployment & Maintenance**.

---

## 1. Environment Setup (VPS Server)

Copy the production environment secrets file:

```bash
cp deploy/env.vpsprod.example deploy/env.vpsprod
```

Set secure permissions so secrets are read-only for root:
```bash
chmod 600 deploy/env.vpsprod
```

* **Live Domain**: `https://faimatrix.com`
* **Production Configs**: `docker-compose.yml` + `docker-compose.vps.yml` + `deploy/env.vpsprod`

---

## 2. Git Pull on VPS (`--ff-only`)

When pulling new code on your VPS server, **ALWAYS use `--ff-only`** to prevent messy merge conflicts:

```bash
git pull --ff-only origin main
```

### Why `--ff-only` is Best Practice for Production:
1. **Strict Fast-Forward**: Forces the VPS branch to match GitHub commit-for-commit.
2. **Conflict Protection**: If someone manually edited files on the VPS server, Git **refuses to create a merge commit** and halts safely.

---

## 3. VPS Helper Script Commands (RECOMMENDED)

FAIMatrix includes automated helper scripts in `./scripts/`:

```bash
# 🚀 Start / Deploy Full Production Stack
./scripts/vps_up.sh

# 📊 Run Live Health & Availability Smoke Tests
./scripts/vps_smoke.sh

# 💾 Backup Production Database & State
./scripts/vps_backup.sh

# 🛑 Stop Full Production Stack
./scripts/vps_down.sh
```

---

## 4. Direct Production Compose Commands

If running manual Compose commands instead of helper scripts:

### 🚀 Production Deploy & Auto-Clean (Daily Standard)
```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml up -d --build && docker image prune -f
```

### ⚡ Zero-Downtime Hot Reload (Frontend or API Only)
```bash
# Update Frontend code without touching DB or Redis
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml up -d --build --no-deps frontend && docker image prune -f

# Update API code only
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml up -d --build --no-deps api && docker image prune -f
```

### 🛠️ Structure Update (Use ONLY when renaming/deleting services in Compose)
```bash
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml up -d --build --remove-orphans && docker image prune -f
```

---

## 5. Production Logs & Status Inspection

```bash
# View production streaming logs for API, Worker, Frontend & Caddy
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml logs -f --tail=100 api worker frontend caddy

# Inspect container health statuses
docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml ps

# Check realtime CPU & Memory usage on VPS
docker stats
```

---

## 6. Production Database Backup & Restore

```bash
# Export / Backup VPS Postgres Database
docker exec -t faim-postgres-vps pg_dump -U faim faim_native > backup_vps.sql

# Restore VPS Postgres Database
cat backup_vps.sql | docker exec -i faim-postgres-vps psql -U faim -d faim_native
```

---

## 7. VPS Prune & Maintenance Schedule

Keep your VPS disk space clean with this automated schedule:

```bash
# 🟢 DAILY (After Deploy):
docker image prune -f

# 🧹 WEEKLY (Clear Build Cache):
docker builder prune -f

# 🧼 MONTHLY (Deep System Clean):
docker system prune -f
```

---

## 8. Complete PC ➡️ VPS Deployment Flow

```bash
# -------------------------------------------------------------
# On your Local PC:
# -------------------------------------------------------------
git add .
git commit -m "feat: new production release"
git push origin main

# -------------------------------------------------------------
# On your VPS Server (via SSH):
# -------------------------------------------------------------
ssh root@your-vps-ip
cd /opt/faim/FAIM

# 1. Pull changes cleanly
git pull --ff-only origin main

# 2. Deploy stack & auto-clean
./scripts/vps_up.sh

# 3. Verify health
./scripts/vps_smoke.sh
```
