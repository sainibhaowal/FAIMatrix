-- Migration 0021: Benchmark baselines for regression detection
-- Purpose: Store benchmark snapshots as baselines for comparison.

CREATE TABLE IF NOT EXISTS benchmark_baselines (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   VARCHAR(64) NOT NULL,
    graph_id    VARCHAR(64) NOT NULL,
    label       VARCHAR(128) NOT NULL,     -- 'auto_2026-04-19_12:30', 'v1.0_release'
    snapshot    JSONB NOT NULL,            -- Full BenchmarkSnapshot JSON
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bb_tenant_graph
    ON benchmark_baselines(tenant_id, graph_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_bb_created_at
    ON benchmark_baselines(created_at DESC);
