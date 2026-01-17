# FAIM-Native – Fractal Antisymmetric Inheritance Memory

**FAIM-Native** is a high-performance memory graph engine built on pure Python, PostgreSQL, Redis, and Qdrant.

## Architecture

- **`faim_native/`** – Core engine source code.
  - `api/` – FastAPI application.
  - `core/` – Graph engine logic.
  - `store/` – PostgreSQL & Redis storage layers.
- **Docker** – Production-ready containerization.

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
