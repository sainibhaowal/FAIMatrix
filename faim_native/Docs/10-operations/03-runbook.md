# Operational runbook

## Migration status

Run commands from the repository root with the project import path:

```bash
PYTHONPATH=faim_native python -m store.pg.migrate status
PYTHONPATH=faim_native python -m store.pg.migrate up
```

Apply migrations through the Compose `migrate` service for a containerized
release. Do not run concurrent migration jobs.

## Health checks

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/ready
```

For a protected route, send `X-Tenant-Id` and `X-Api-Key` and use the
`/api/v1` prefix.

## Evolution metrics

The current metrics endpoint is:

```text
GET /api/v1/evolve/metrics?graph_id=<graph-id>
```

The repository includes `scripts/scrape_evolve_metrics.py` for a textfile
collector workflow. Configure credentials in the deployment environment; do
not put them in a cron file committed to Git.

## Backup and recovery

Back up PostgreSQL and the raw-store volume together. Before a release, prove
that the backup can be restored in an isolated environment. This runbook does
not claim a successful restore unless an operator records one.

## Incident sequence

1. Check `/health` and `/ready`.
2. Check recent deployment and migration state.
3. Check database, raw-store, worker, Redis, and Qdrant health separately.
4. Stop writes before attempting data repair.
5. Preserve logs, request IDs, and migration versions.
6. Re-run the smallest relevant smoke test after recovery.
