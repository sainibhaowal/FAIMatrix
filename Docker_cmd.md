# FAIMatrix Docker Operations Master Guide

Welcome to the **FAIMatrix Docker Reference Documentation**.

For focused environment instructions, please refer to the dedicated guides:

* 💻 **[Docker_cmd_local.md](file:///home/ravi/Projects/FAIM/Docker_cmd_local.md)** — Commands and workflows for **Local PC Development**.
* 🌐 **[Docker_cmd_vps.md](file:///home/ravi/Projects/FAIM/Docker_cmd_vps.md)** — Commands, helper scripts, and deployment for **VPS Production Server**.

---

## Quick Reference Summary

| Target Environment | Compose Configuration | Environment File | Reference Guide |
| :--- | :--- | :--- | :--- |
| **Local PC** | `docker-compose.yml` | `.env` | **[Docker_cmd_local.md](file:///home/ravi/Projects/FAIM/Docker_cmd_local.md)** |
| **VPS Production** | `docker-compose.yml` + `docker-compose.vps.yml` | `deploy/env.vpsprod` | **[Docker_cmd_vps.md](file:///home/ravi/Projects/FAIM/Docker_cmd_vps.md)** |

---

## Key Golden Rules

1. **Local PC Deploy**: `docker compose up -d --build && docker image prune -f`
2. **VPS Git Pull**: Always use `git pull --ff-only origin main` on production servers.
3. **VPS Deploy**: `./scripts/vps_up.sh` or `docker compose --env-file deploy/env.vpsprod -f docker-compose.yml -f docker-compose.vps.yml up -d --build && docker image prune -f`
4. **Use `--remove-orphans`**: ONLY when renaming or deleting services in `docker-compose.yml`.
