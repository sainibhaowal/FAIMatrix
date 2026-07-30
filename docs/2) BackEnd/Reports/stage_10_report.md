# Stage-10 Report: Operational Hardening

## Overview

Stage-10 focuses on making FAIM-Native production-ready through robust migrations, durable background jobs, and operational procedures.

## Verification Results

- **Total Tests**: 416 passed, 1 skipped
- **Exit Code**: 0 (Success)

## Implementation Summary

### 1. Migration System

| File                                            | Purpose                             |
| ----------------------------------------------- | ----------------------------------- |
| `store/pg/migrations/0001_initial.sql`          | Baseline schema                     |
| `store/pg/migrations/0002_stage10_ops_pack.sql` | Jobs, events, migrations tables     |
| `store/pg/migrate.py`                           | Checksum-protected migration engine |

**Key Features**:

- SHA256 checksums prevent tampering
- Idempotent application (safe to run multiple times)
- `/ready` endpoint enforces migration status

### 2. Durable Jobs

| File                              | Purpose                            |
| --------------------------------- | ---------------------------------- |
| `orchestration/jobs/job_store.py` | Transactional job queue            |
| `orchestration/jobs/worker.py`    | Background worker with retry logic |

**Key Features**:

- FIFO ordering guaranteed
- Automatic stale job reclamation
- Lock integration for single-writer operations

### 3. Operational Procedures

| File                              | Purpose                    |
| --------------------------------- | -------------------------- |
| `scripts/drill_backup_restore.sh` | Automated recovery drill   |
| `docs/SECURITY.md`                | Threat model and hardening |
| `docs/RUNBOOK.md`                 | Day-to-day operations      |
| `docs/DEPLOYMENT.md`              | Production setup           |

## Architecture

### Migration Flow

```
API Start → run_up() → Hash local files → Compare to DB → Apply pending → /ready returns 200
```

### Job Lifecycle

```
Enqueue → Claim (atomic) → Execute → Heartbeat → Complete/Fail → Audit log
```

## New Tables

```sql
schema_migrations (version, checksum, applied_at)
jobs (job_id, tenant_id, graph_id, kind, status, payload, created_at, updated_at)
job_events (id, job_id, kind, payload, ts)
```

## API Changes

- **Version**: Bumped to `0.10.0`
- **`/ready`**: Now checks migrations, tables, and DB connection
- **Auth**: `/ready` exempted from tenant authentication

## Production Hardening (Yellow Triangle Killers)

The following measures ensure safe operations in multi-instance production environments:

### 1. Controlled Auto-Migrations

- **`FAIM_AUTO_MIGRATE`**: Set to `false` by default. Application instances will not attempt to mutate the schema unless explicitly configured.
- **Advisory Locking**: In Postgres, a global advisory lock (`0xFA141`) is acquired before migrations start. This prevents race conditions where multiple replicas attempt to apply the same migration simultaneously.
- **Fail-Safe**: If a migration fails or a checksum mismatch is detected, the process aborts immediately to protect data integrity.

### 2. Readiness Probe Security

- **Privacy First**: The `/ready` endpoint is exempted from tenant authentication but strips all sensitive data.
- **Output**: Returns only high-level status flags (`db_connected`, `tables_ok`, `migrations_ok`) and version counters. No schema details, error messages, or tenant-specific data are exposed.

### 3. Backup & Restore Mandate

- **Postgres-First**: Backup drills use `pg_dump` and are mandatory for production releases.
- **SQLite Role**: Used primarily for "logic-only" verification in CI/Development environments. Tests explicitly skip the backup drill on SQLite with a reminder of its production importance.

## Acceptance Tests

- `test_AT_S10_migration_readiness.py`: Migration idempotency and `/ready` enforcement
- `test_AT_S10_job_durability.py`: Job claiming, stale recovery, locking
- `test_AT_S10_backup_drill.py`: Backup/restore verification (Postgres only; skipped on SQLite)
