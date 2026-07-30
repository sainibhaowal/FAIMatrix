-- Migration 0020: Benchmark time-series samples
-- Purpose: Store timestamped metric samples for historical benchmark charts.
-- Additive only. No existing table modifications.

CREATE TABLE IF NOT EXISTS benchmark_samples (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   VARCHAR(64) NOT NULL,
    graph_id    VARCHAR(64) NOT NULL,
    metric_name VARCHAR(64) NOT NULL,   -- 'latency_*', 'throughput', 'D_hat', etc.
    metric_value DOUBLE PRECISION NOT NULL,
    labels      JSONB DEFAULT '{}',     -- Optional: {"phase": "encode", "endpoint": "/ingest"}
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bs_tenant_graph_metric
    ON benchmark_samples(tenant_id, graph_id, metric_name, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_bs_recorded_at
    ON benchmark_samples(recorded_at DESC);
