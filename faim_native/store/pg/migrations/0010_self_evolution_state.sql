-- =============================================================================
-- Phase S2: Self-Evolution Scheduler Durable State
-- Version: 0010
-- Description:
--   Adds durable state table for self-evolution scheduler coordination.
-- =============================================================================

CREATE TABLE IF NOT EXISTS self_evolution_state (
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    last_seen_version BIGINT NOT NULL DEFAULT 0,
    last_evolved_version BIGINT NOT NULL DEFAULT 0,
    last_evolved_at TIMESTAMPTZ,
    last_enqueued_job_id UUID,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, graph_id)
);

CREATE INDEX IF NOT EXISTS idx_self_evolution_state_updated
    ON self_evolution_state(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_self_evolution_state_due
    ON self_evolution_state(tenant_id, last_evolved_at);

COMMENT ON TABLE self_evolution_state IS
    'Durable scheduler state for self-evolution due-graph selection and enqueue dedupe';
