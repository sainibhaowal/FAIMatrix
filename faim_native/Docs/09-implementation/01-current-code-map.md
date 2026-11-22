# Current implementation map

This map is intentionally short and is generated from the current repository
layout rather than from historical phase reports.

## Runtime packages

| Area | Current path | Responsibility |
| --- | --- | --- |
| API application | `faim_native/api` | FastAPI app, middleware, contracts, services, and routers |
| Core graph and reasoning | `faim_native/core` | Graph, query, temporal, reasoning, learning, and metrics logic |
| Domain models | `faim_native/domain` | Domain-level contracts and policies |
| Perception | `faim_native/perception` | Ingest extraction and evidence handling |
| Encoding | `faim_native/encoding` | Native representations, OCR, layout, and adapters |
| Storage | `faim_native/store` | PostgreSQL, raw blobs, journal, crypto, and persistence |
| Indexing | `faim_native/index` and `faim_native/lexical` | Optional acceleration and lexical retrieval |
| Jobs | `faim_native/orchestration/jobs` | Worker and durable background work |
| Runtime configuration | `faim_native/runtime` | Configuration, feature flags, secrets, and bootstrap |

## API surface

The routers mounted by `faim_native/api/app.py` use the `/api/v1` prefix unless
noted otherwise. Health routes are also exposed at the root for deployment
checks. MCP routes are exposed at `/mcp`; OAuth metadata is exposed by the
OAuth router.

The current mounted router modules are:

`auth`, `embedding_providers`, `events`, `ingest`, `ocr_providers`, `query`,
`reasoning`, `reranker`, `memory`, `node`, `evolve`, `graph`, `metrics`,
`api_keys`, `storage`, and `health`.

There is no current `cortex` router and no current approval-queue frontend
page. Documentation must not advertise those as available product surfaces.

## Frontend dashboard routes

The current Next.js dashboard pages are:

`/dashboard`, `/dashboard/api-keys`, `/dashboard/billing`,
`/dashboard/embedding-providers`, `/dashboard/evolution`,
`/dashboard/graph`, `/dashboard/journal`, `/dashboard/mcp`,
`/dashboard/profile`, `/dashboard/providers`, and `/dashboard/storage`.

## Deployment services

`docker-compose.yml` defines PostgreSQL, Redis, Qdrant, the migration job, the
API, and the worker. Redis and Qdrant are acceleration services; PostgreSQL
and the raw store remain the durable source-of-truth path.
