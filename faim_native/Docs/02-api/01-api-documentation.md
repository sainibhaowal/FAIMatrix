# FAIM-Native API documentation

This document describes the API routes mounted by the current
`faim_native/api/app.py`. The canonical API prefix is `/api/v1`.

## Authentication

Protected routes accept either the configured session/JWT mechanism or the
tenant API-key headers:

```http
X-Tenant-Id: <tenant-id>
X-Api-Key: <api-key>
```

Production mode is configured for database-primary authentication. The
legacy environment-key fallback must remain disabled for production:

```text
FAIM_AUTH_DB_PRIMARY=true
FAIM_AUTH_ENV_FALLBACK_ENABLED=false
FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED=true
```

Never put a plaintext key in a repository, issue, log, or benchmark artifact.

## Root health and metadata

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness check |
| GET | `/ready` | Readiness and migration check |
| GET | `/version` | Runtime version information, when enabled |
| GET/POST/DELETE | `/mcp` | Remote MCP transport |

## `/api/v1` route families

| Router | Representative routes |
| --- | --- |
| Auth | `/api/v1/auth/me`, `/api/v1/auth/otp/request`, `/api/v1/auth/totp/status` |
| Query | `POST /api/v1/query` |
| Ingest | `POST /api/v1/ingest`, `POST /api/v1/ingest/upload` |
| Memory | `/api/v1/memory/...` |
| Graph | `/api/v1/graph/surface`, `/api/v1/graph/neighborhood` |
| Node | `/api/v1/node/{node_id}`, `/api/v1/node/{node_id}/explain` |
| Reasoning | `/api/v1/traverse`, `/api/v1/plan`, `/api/v1/feedback`, `/api/v1/learning/state` |
| Evolution | `POST /api/v1/evolve`, `GET /api/v1/evolve/status`, `GET /api/v1/evolve/metrics` |
| Events | `/api/v1/events`, `/api/v1/events/latest`, `/api/v1/events/stream` |
| Metrics | `GET /api/v1/scorecard` |
| Storage | `/api/v1/storage/files`, `/api/v1/storage/uploads`, `/api/v1/storage/summary` |
| API keys | `/api/v1/api-keys` |
| Embedding providers | `/api/v1/embedding-providers` |
| OCR providers | `/api/v1/ocr-providers` |
| Reranker | `/api/v1/reranker/status`, `/api/v1/reranker/test` |

The exact request and response schemas are defined in the router modules and
Pydantic contracts. This document is a route-family index, not a substitute
for those source-level schemas.

## Example readiness check

```bash
curl -fsS http://localhost:8000/ready
```

For protected API calls, add both authentication headers and use the
`/api/v1` prefix. A successful readiness response does not by itself prove
that every optional provider, benchmark workload, or production deployment
configuration is ready.

## Explicit non-surfaces

The current codebase does not mount a `/api/v1/cortex` router and does not
provide an approval-queue frontend route. Older manuals describing those
surfaces are archived and should not be used as API references.
