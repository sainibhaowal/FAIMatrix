# FAIM-Native Operational Runbook

## Database Migrations

FAIM uses a custom migration system in `store/pg/migrate.py`.

### Checking Status

```bash
python3 -m store.pg.migrate status
```

### Applying Migrations

```bash
python3 -m store.pg.migrate up
```

> [!IMPORTANT]
> When running against Postgres, the engine uses advisory locks to prevent concurrent application.

## Backup and Recovery

### Routine Exercise

Run the drill script to verify backup/restore path (Mandatory for production releases on Postgres):

```bash
./scripts/drill_backup_restore.sh
```

### Manual Backup

```bash
pg_dump -h localhost -U faim_admin faim_main > backup_$(date +%Y%m%d).sql
```

## Background Jobs

Jobs are processed by `orchestration/jobs/worker.py`.

### Health Check

Monitor the `jobs` and `job_events` tables for stalled jobs (status = 'running' for > 15 mins).
Stalled jobs are automatically reclaimed by workers based on `updated_at` threshold.
