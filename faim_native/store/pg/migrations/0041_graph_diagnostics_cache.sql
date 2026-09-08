-- Migration 0041: versioned graph diagnostics cache.
-- Query reads this bounded row; graph writes/evolution refresh it when the
-- graph version changes.  No existing graph data is modified or removed.
CREATE TABLE IF NOT EXISTS graph_diagnostics_cache (
    tenant_id VARCHAR(64) NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    graph_version BIGINT NOT NULL DEFAULT 0,
    node_count INTEGER NOT NULL DEFAULT 0,
    edge_count INTEGER NOT NULL DEFAULT 0,
    cr DOUBLE PRECISION NOT NULL DEFAULT 0,
    redundancy DOUBLE PRECISION NOT NULL DEFAULT 0,
    d_hat DOUBLE PRECISION NOT NULL DEFAULT 0,
    h_hat DOUBLE PRECISION NOT NULL DEFAULT 0,
    lambda_hat DOUBLE PRECISION NOT NULL DEFAULT 0,
    novelty DOUBLE PRECISION NOT NULL DEFAULT 0,
    energy DOUBLE PRECISION NOT NULL DEFAULT 0,
    diagnostics_hash VARCHAR(64) NOT NULL DEFAULT '',
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, graph_id)
);
CREATE INDEX IF NOT EXISTS idx_graph_diagnostics_cache_version
    ON graph_diagnostics_cache (tenant_id, graph_id, graph_version);
