-- Stage-10: Ops Pack Additions
-- Version: v3 (Migrations, Durable Jobs, job_events)

-- -----------------------------------------------------------------------------
-- schema_migrations: Internal table for migration tracking
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    checksum TEXT NOT NULL
);

-- -----------------------------------------------------------------------------
-- job_events: Per-job progress journal
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_events (
    seq SERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    kind TEXT NOT NULL,                  -- 'step_start', 'step_progress', 'log'
    payload JSON NOT NULL DEFAULT '{}',
    
    CONSTRAINT uq_job_events_job_id_seq UNIQUE (job_id, seq)
);

CREATE INDEX IF NOT EXISTS idx_job_events_job_id_seq ON job_events(job_id, seq);
CREATE INDEX IF NOT EXISTS idx_job_events_ts ON job_events(ts ASC);

-- -----------------------------------------------------------------------------
-- Security Hardening: Ensure indexes on jobs for status polling
-- (Wait, these were already in schema.sql, but we ensure them here too if they differ)
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_jobs_tenant_status_created ON jobs(tenant_id, status, created_at);
