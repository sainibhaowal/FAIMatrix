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

## Evolution Monitoring

The self-evolution system exposes a scrapeable health snapshot at `GET /api/v1/evolve/metrics?graph_id=...`
(auth: `X-Tenant-Id` + `X-Api-Key`).

### Scrape to Prometheus (node_exporter textfile)

```bash
./scripts/scrape_evolve_metrics.py -t <tenant-id> -g <graph-id> -k <api-key> \
  -u http://localhost:8000 \
  --out /var/lib/node_exporter/textfile_collector/evolve.prom \
  --deadman /var/lib/node_exporter/textfile_collector/evolve_deadman.prom
```

Writes `faim_evolve_*` gauge families plus a deadman marker
(`faim_evolve_updated_timestamp_seconds`, `faim_evolve_scrape_failure_age_seconds`).

### Cron + alert on critical

```bash
1-59/5 * * * * /home/ravi/Projects/FAIM/scripts/scrape_evolve_metrics.py \
  -t <tenant-id> -g <graph-id> -k <api-key> \
  --out /var/lib/node_exporter/textfile_collector/evolve.prom \
  >> /var/log/evolve_scrape.log 2>&1 || \
  curl -fsS -X POST <pagerduty-webhook> -d "$(cat /var/log/evolve_scrape.log)"
```

**Exit codes:** `0` OK / no criticals, `2` critical active (page), `3` endpoint
unreachable or auth failed.

### Alert severities

| Level | Code | Meaning |
|-------|------|---------|
| critical | `backup_coverage_gap` | Nodes pruned without a pre-action backup — possible data loss |
| warning | `learning_cold_start` | Learning active but below the 20-outcome trust threshold |
| info | `no_cycles_recorded` / `learning_waiting` / `learning_disabled` | Expected cold-start notices |

### Performance sanity

If cycles remain slow with large graphs, re-run the benchmark to confirm the
vectorized similarity passes hold up:

```bash
python3 scripts/bench_evolve_similarity.py
```

Expected: ~30-36x faster than the pre-vectorization python loops
(e.g. n=2000: ~42s -> ~1.2s).

## Background Jobs

Jobs are processed by `orchestration/jobs/worker.py`.

### Health Check

Monitor the `jobs` and `job_events` tables for stalled jobs (status = 'running' for > 15 mins).
Stalled jobs are automatically reclaimed by workers based on `updated_at` threshold.
