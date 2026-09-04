# Project status

FAIM-Native is an experimental, actively evolving memory graph platform. The repository contains a broad end-to-end implementation, but individual features can have different maturity levels and deployment requirements.

> **Important:** This repository should be treated as an unstable research prototype. It is not intended for personal productivity, production, business-critical, safety-critical, regulated, or irreplaceable-data workloads. Use isolated environments and disposable or backed-up data while the architecture and operational contracts continue to change.

The project is ambitious by design: it spans ingestion, evidence preservation, native encoding, graph persistence, retrieval, evolution, background jobs, APIs, security controls, and a frontend. That breadth is useful for systems research and engineering experimentation, but it also increases integration risk. A feature being present, tested, or visible in the UI does not by itself mean that it is stable or production-ready.

For the formal research framing, limits of current claims, and evaluation questions, read [`RESEARCH_POSITIONING.md`](RESEARCH_POSITIONING.md). For the current maturity interpretation and safe evaluation procedure, read [`EXPERIMENTAL_STATUS.md`](EXPERIMENTAL_STATUS.md). For planned hardening and release criteria, read [`ROADMAP.md`](ROADMAP.md).

The implementation-grounded component inventory and lifecycle diagrams are in [`docs/END_TO_END_ARCHITECTURE.md`](docs/END_TO_END_ARCHITECTURE.md). They intentionally distinguish current services from optional integrations and future infrastructure.

## Present in the repository

- FastAPI API with health, readiness, authentication, tenant auth, memory, ingest, query, graph, events, evolution, storage, Cortex, and benchmark routes;
- deterministic native encoding with a fixed 256-dimensional vector contract;
- PostgreSQL persistence, migrations, raw-file storage, event history, snapshots, and graph versions;
- Redis and Qdrant integration paths for coordination, caching, and retrieval acceleration;
- worker jobs for ingestion, maintenance, evolution, retention, and re-encryption workflows;
- Next.js dashboard, authentication surfaces, graph views, documentation, and frontend tests; and
- Python acceptance tests, frontend tests, Docker Compose environments, smoke tests, and security checks.

## Verify before calling a deployment production-ready

- run the current checkout's relevant tests rather than relying on old report counts;
- validate environment secrets, CORS, TLS, authentication, tenant isolation, rate limits, and encryption settings;
- apply and verify migrations before starting application traffic;
- test backup and restore with the actual data volume;
- measure ingest, query, worker, and storage behavior on representative data;
- review third-party dependency, container, OCR, embedding, and dataset licenses; and
- document rollback, retention, incident response, and operator access.

## Known documentation caveat

Some historical documents describe earlier paths, stage numbers, or deployment scripts. The running source code, current Compose files, current package scripts, and generated OpenAPI document should be treated as the operational source of truth.
