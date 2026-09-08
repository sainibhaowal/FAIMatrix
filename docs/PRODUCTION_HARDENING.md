# Production hardening contract

This document records the additive safeguards implemented for the FAIM-native
pipeline. Existing API routes and canonical graph/storage data remain the
source of truth.

## Authentication

`FAIM_ALLOW_DEV_AUTH_BYPASS` is a local-only compatibility switch. When
`FAIM_MODE=production` or `FAIM_ENV=production`, `authenticate_tenant_key`
always rejects the `default`/`test-key`/`admin` path and verifies a real
database key. Production examples set the switch to `false` explicitly.

Production authentication is DB-primary and does not require a long-lived
plaintext `TENANT_KEYS_JSON` map. Set that legacy compatibility variable to
`{}` when `FAIM_AUTH_DB_PRIMARY=true` and
`FAIM_AUTH_ENV_FALLBACK_ENABLED=false`. If both `FAIM_MODE` and `FAIM_ENV` are
present, either one selecting production enables the production safeguards.

### One-time tenant-key bootstrap

Before the first database-only deployment, an operator may provide a temporary
`FAIM_TENANT_KEY_BOOTSTRAP_JSON` value in the canonical shape:

```json
{"tenant_id":["a-new-high-entropy-api-key"]}
```

Run the local, explicit script without `--apply` first to verify the plan, then
run it once with `--apply` against the intended `DATABASE_URL`:

```bash
PYTHONPATH=faim_native python scripts/bootstrap_tenant_api_keys.py
PYTHONPATH=faim_native python scripts/bootstrap_tenant_api_keys.py --apply
```

The script reads only `FAIM_TENANT_KEY_BOOTSTRAP_JSON`, not
`TENANT_KEYS_JSON`; validates tenants and keys; stores only Argon2id hashes;
does not print plaintext keys; and imports only keys that are absent for that
tenant. A repeated run is idempotent. Matching revoked or expired keys count as
already present and are never silently reactivated. The imported bootstrap key
has the current tenant-management and memory scopes so an operator can create
narrower replacement keys; rotate/revoke that high-privilege bootstrap key
afterward through `/api/v1/api-keys`.

Do not place `FAIM_TENANT_KEY_BOOTSTRAP_JSON` in a long-running API/worker
environment, source control, or a persistent dotenv file. Production runtime
configuration and the container entrypoint reject it. For the automated VPS
deploy helper only, a temporary line in `deploy/env.vpsprod` is consumed after
migrations and removed only after the DB transaction succeeds; on failure, the
line remains for an operator to correct and retry.

## Diagnostics

Migration `0041_graph_diagnostics_cache.sql` adds one tenant/graph row keyed by
graph version. Ingest and evolution refresh it after canonical writes. Query
and scorecard reads use the bounded row and expose `diagnostics_graph_version`,
`diagnostics_computed_at`, and `diagnostics_cached`; a one-time compatibility
backfill is permitted for graphs created before migration 0041.

## Indexing and recovery

The network E2E profile starts PostgreSQL, Redis, and Qdrant. Qdrant is an
acceleration layer only; canonical Postgres retrieval remains valid when the
service is unavailable. The client retries an outage after
`FAIM_QDRANT_RETRY_SECONDS` (default 15 seconds), and
`reset_qdrant_connection()` is available for controlled operational probes.

## Domain Studio and advanced jobs

Ordinary JSON/multipart ingest now triggers the real domain profile rebuild:
durable `domain_autonomy` jobs when workers are enabled, or a synchronous
rebuild in single-process mode. Rebuild errors are returned in `errors`, emit
`DOMAIN_PROFILE_REBUILD_FAILED`, and fail the durable job instead of becoming a
silent empty result. Evolution responses similarly expose
`advanced_warnings` and `EVOLUTION_COMPONENT_DEGRADED` events.

## OCR

OCR retains bounded image pixels, PDF DPI, and provider timeouts. Set
`FAIM_OCR_PREWARM=true` in production to load the configured provider during
startup; `FAIM_OCR_PREWARM_REQUIRED=true` makes readiness fail if the model
cannot be initialized within `FAIM_OCR_PREWARM_TIMEOUT_SECONDS`.

## Verification

- `tests/unit/test_query_hardening.py` covers temporal filtering, diagnostics
  cache reuse, and bounded domain node identities.
- `tests/unit/test_phase_k3_auth_enforcement.py` proves production bypass
  rejection, including conflicting `FAIM_MODE`/`FAIM_ENV` values.
- `tests/unit/test_api_key_bootstrap.py` proves Argon2id-only import,
  idempotence, validation, dry-run behavior, and DB-only production config.
- `.github/workflows/ci.yml` includes a real Postgres/Redis/Qdrant ingest and
  indexed-query job.
- `scripts/load_test_ingest.py` runs bounded concurrent uploads against a real
  API using caller-supplied documents and reports p50/p95 latency.

## VPS deployment safety

`scripts/vps_deploy_ci.sh` refuses an env file containing `CHANGE_ME_`
placeholders and never runs global Docker prune commands. The GitHub deploy
workflow fails early when SSH/GHCR secrets are missing, then pulls the exact
immutable image tag and runs the public health smoke checks.

The VPS Compose override publishes no FAIM host ports. FAIM's internal Caddy
only joins the dedicated FAIM network and the existing `aurelinx_default`
gateway network. Deployment does not edit, reload, or restart the independent
gateway at `/opt/gateway/Caddyfile`; the public gateway route is a separately
reviewed operator change.

It additionally requires `TENANT_KEYS_JSON={}` for DB-only production auth.
If an operator temporarily adds `FAIM_TENANT_KEY_BOOTSTRAP_JSON`, it runs the
backend-image bootstrap script after migrations and atomically removes only
that line after a successful import. It never echoes the payload.
