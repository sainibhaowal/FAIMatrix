# Docker deployment

This guide describes the Compose stack in the repository root. FAIM is a
preview/alpha system; a successful local deployment is not a blanket
production-readiness claim.

## Prerequisites

- Docker Engine and Compose v2
- A populated `.env` based on [`.env.example`](../../../.env.example)
- A durable secret for `POSTGRES_PASSWORD`
- A configured master key when encryption-at-rest is enabled

## Start the stack

```bash
docker compose build
docker compose run --rm migrate
docker compose up -d
curl -fsS http://localhost:8000/ready
```

The Compose services are PostgreSQL, Redis, Qdrant, `migrate`, `api`, and
`worker`. The API and worker are configured for production safeguards by
default in `docker-compose.yml`; review the `.env` values before deployment.

## Authentication configuration

For database-primary production authentication, use:

```text
FAIM_AUTH_DB_PRIMARY=true
FAIM_AUTH_ENV_FALLBACK_ENABLED=false
FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED=true
```

Use the bootstrap script described in
[`02-production-hardening.md`](../11-security/02-production-hardening.md) to create the
first tenant key. Do not rely on a committed or copied plaintext key map.

## Migration rule

Run the one-shot `migrate` service before the API and worker. Keep
`FAIM_AUTO_MIGRATE=false` for release deployments unless the operator has
explicitly chosen a controlled development workflow.

## Verification

```bash
docker compose ps
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/ready
```

Readiness confirms the configured startup dependencies and migration state. It
does not verify external provider credentials, backups, tenant isolation under
load, or benchmark competitiveness.
