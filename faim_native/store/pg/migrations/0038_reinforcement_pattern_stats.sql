-- Migration 0038: reinforcement_pattern_stats
-- Durable learned statistics for reasoning patterns, written by the
-- ReinforcementLearner as feedback accumulates. Closes the feedback →
-- policy loop so pattern reliability survives restarts.

CREATE TABLE IF NOT EXISTS reinforcement_pattern_stats (
    pattern_hash         VARCHAR(16) NOT NULL,
    tenant_id            VARCHAR(64) NOT NULL,
    query_signature      VARCHAR(32) NOT NULL,
    total_uses           INTEGER NOT NULL DEFAULT 0,
    successful_uses      INTEGER NOT NULL DEFAULT 0,
    failed_uses          INTEGER NOT NULL DEFAULT 0,
    average_rating       DOUBLE PRECISION NOT NULL DEFAULT 0,
    correction_rate      DOUBLE PRECISION NOT NULL DEFAULT 0,
    reliability_score    DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    threshold_adjustment DOUBLE PRECISION NOT NULL DEFAULT 0,
    first_seen           TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (pattern_hash, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_reinforcement_stats_tenant
    ON reinforcement_pattern_stats (tenant_id, reliability_score DESC);

COMMENT ON TABLE reinforcement_pattern_stats IS
    'Durable learned pattern statistics from the reinforcement feedback loop.';