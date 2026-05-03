# FAIM-Native – Fractal Antisymmetric Inheritance Memory

**FAIM-Native** is a high-performance memory graph engine built on pure Python, PostgreSQL, Redis, and Qdrant.

## Architecture

- **`faim_native/`** – Core engine source code.
  - `api/` – FastAPI application.
  - `core/` – Graph engine logic.
  - `store/` – PostgreSQL & Redis storage layers.
- **Docker** – Production-ready containerization.

## Infrastructure Standard (Port Alignment)

All services are aligned to the `80x0` port range for consistency and to avoid collisions:

| Service | Host Port | Internal Port | Description |
| :--- | :--- | :--- | :--- |
| **API** | `8000` | `8000` | FastAPI Engine |
| **Frontend** | `8010` | `8010` | Next.js Dashboard |
| **Postgres** | `8020` | `8020` | Database |
| **Redis** | `8030` | `8030` | Cache/Locks |
| **Qdrant** | `8040` / `8050` | `8040` / `8050` | Vector Database (HTTP/gRPC) |

## Quick Start

```bash
# Start the local production mirror
npm run faim:localprod:up

# Smoke test the local production stack
npm run faim:localprod:smoke

# Rebuild only the service that changed
npm run faim:localprod:up frontend
npm run faim:localprod:up api
npm run faim:localprod:up worker
npm run faim:localprod:up migrate api worker

# Run Tests
cd faim_native
pytest
```

The public docs portal lives at `/docs` and includes the current system map,
FAIM Cortex, deployment, and benchmark references.

## Release Hygiene

- Pull requests are expected to pass CI before merge.
- Keep `main` protected; do not push directly to it.

## Local Production

```bash
# Create the single local-prod env file used by API + worker + frontend
cp .env.localprod.example .env.localprod

# Bring up the local production stack
npm run faim:localprod:up

# Smoke test the edge, health, and readiness endpoints
npm run faim:localprod:smoke

# Capture DB + raw-data backups
npm run faim:localprod:backup
```

The restricted admin section is available at `/dashboard/admin` for
allowlisted admin emails only.

## VPS Production

```bash
# Create the single VPS env file used by API + worker + frontend
cp deploy/env.vpsprod.example deploy/env.vpsprod

# Sync the repo to the VPS
npm run faim:vps:sync

# Copy the real VPS env file separately
scp deploy/env.vpsprod root@144.91.118.196:/opt/faim/FAIM/deploy/env.vpsprod

# Bring up the VPS production stack
npm run faim:vps:up

# Smoke test the public domain
npm run faim:vps:smoke
```

## Tech Stack

- **Python 3.11** (FastAPI, SQLAlchemy, Pydantic)
- **PostgreSQL 15** (Relational Data)
- **Redis 7** (Cache, Locks, Queues)
- **Qdrant** (Vector Search)
