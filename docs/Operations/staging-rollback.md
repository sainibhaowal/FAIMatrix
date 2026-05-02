# Staging And Rollback

This document defines the minimum staging process for FAIM and the rollback
steps used to prove recoverability before production promotion.

## Staging Goals

- Match production as closely as practical.
- Exercise the same migration and startup gating path.
- Reuse the same image build process as production.
- Keep acceleration features enabled only when explicitly validated.

## Staging Baseline

Use [deploy/env.staging.example](/home/sephi-asi/FAIM/deploy/env.staging.example)
as the starting point.

Required behavior:

- `FAIM_AUTO_MIGRATE=false`
- `FAIM_ENCRYPTION_AT_REST=true`
- `FAIM_ENCRYPTION_FAIL_CLOSED=true`
- `FAIM_AUTH_DB_PRIMARY=true`
- `FAIM_AUTH_ENV_FALLBACK_ENABLED=false`
- `FAIM_AUTH_SCOPE_ENFORCEMENT_ENABLED=true`
- Explicit CORS origin allowlist

## Rollback Drill

Run a rollback drill after every significant backend, migration, or auth change.

1. Deploy a new candidate to staging.
2. Confirm health endpoints and a basic smoke test pass.
3. Record the exact image digests and database migration version.
4. Roll back to the previous known-good image digest.
5. Re-run the same smoke test.
6. Verify the system returns to the previous graph state and remains ready.

## Recovery Checks

Minimum checks after rollback:

- `/health` returns success.
- `/ready` returns success.
- Backend auth works with the expected tenant key or session token.
- Backend migrations are at the expected version.
- Frontend can load the dashboard and graph view.

## Operational Rule

Never treat a rollback as complete until the same smoke path has passed on the
restored version.
