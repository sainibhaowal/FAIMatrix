-- 0012_representation_v2.sql
--
-- Additive lexical-semantic sidecar storage for Representation V2.
-- Keeps the canonical 256-d v_native contract unchanged.

CREATE TABLE IF NOT EXISTS node_repr_v2 (
    node_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    repr_hash VARCHAR(64) NOT NULL,
    word_counts JSONB NOT NULL DEFAULT '{}',
    phrase_counts JSONB NOT NULL DEFAULT '{}',
    skip_counts JSONB NOT NULL DEFAULT '{}',
    entity_tokens JSONB NOT NULL DEFAULT '[]',
    time_tokens JSONB NOT NULL DEFAULT '[]',
    layout_tokens JSONB NOT NULL DEFAULT '[]',
    channel_lengths JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_node_repr_v2_tenant_graph
    ON node_repr_v2(tenant_id, graph_id);

CREATE INDEX IF NOT EXISTS idx_node_repr_v2_repr_hash
    ON node_repr_v2(tenant_id, graph_id, repr_hash);

CREATE TABLE IF NOT EXISTS graph_repr_v2_stats (
    tenant_id TEXT NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    channel VARCHAR(32) NOT NULL,
    doc_count INTEGER NOT NULL DEFAULT 0,
    avg_len DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    df_map JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, graph_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_graph_repr_v2_stats_tenant_graph
    ON graph_repr_v2_stats(tenant_id, graph_id);

COMMENT ON TABLE node_repr_v2 IS
    'Additive Representation V2 lexical-semantic sidecar keyed by node_id';

COMMENT ON TABLE graph_repr_v2_stats IS
    'Graph-scoped document-frequency and length statistics for Representation V2 channels';
