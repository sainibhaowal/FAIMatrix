-- =============================================================================
-- Stage-J: Self-Invention Runtime State
-- Version: 0007
-- Description:
--   Adds durable state table for incremental self-invention processing.
-- =============================================================================

CREATE TABLE IF NOT EXISTS self_invention_state (
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    last_event_seq BIGINT NOT NULL DEFAULT 0,
    signature_counts JSON NOT NULL DEFAULT '{}',
    last_cycle_macros INTEGER NOT NULL DEFAULT 0,
    last_cycle_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tenant_id, graph_id)
);

CREATE INDEX IF NOT EXISTS idx_self_invention_state_updated
    ON self_invention_state(updated_at DESC);

COMMENT ON TABLE self_invention_state IS
    'Durable state cursor and coactivation counters for self-invention runtime';
