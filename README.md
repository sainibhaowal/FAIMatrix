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
# Start Development Environment
./dev.sh

# Run Tests
cd faim_native
pytest
```

## Tech Stack

- **Python 3.11** (FastAPI, SQLAlchemy, Pydantic)
- **PostgreSQL 15** (Relational Data)
- **Redis 7** (Cache, Locks, Queues)
- **Qdrant** (Vector Search)
