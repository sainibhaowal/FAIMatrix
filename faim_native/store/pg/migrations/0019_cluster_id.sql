-- Migration 0019: Cluster assignment for graph nodes + cluster centers table
-- Enables deterministic k-means topic clustering on v_native vectors.

ALTER TABLE nodes ADD COLUMN cluster_id INTEGER;

CREATE TABLE IF NOT EXISTS graph_clusters (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    cluster_id INTEGER NOT NULL,
    center JSONB NOT NULL,
    node_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, graph_id, cluster_id)
);

CREATE INDEX IF NOT EXISTS idx_graph_clusters_graph ON graph_clusters (tenant_id, graph_id);
