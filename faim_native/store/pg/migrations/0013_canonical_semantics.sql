-- 0013_canonical_semantics.sql
--
-- Graph-scoped canonical semantics statistics and lexicon storage.

CREATE TABLE IF NOT EXISTS graph_term_stats (
    tenant_id TEXT NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    channel VARCHAR(32) NOT NULL,
    term TEXT NOT NULL,
    df INTEGER NOT NULL DEFAULT 0,
    cf INTEGER NOT NULL DEFAULT 0,
    doc_count INTEGER NOT NULL DEFAULT 0,
    context_terms JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, graph_id, channel, term)
);

CREATE INDEX IF NOT EXISTS idx_graph_term_stats_tenant_graph
    ON graph_term_stats(tenant_id, graph_id);

CREATE INDEX IF NOT EXISTS idx_graph_term_stats_channel
    ON graph_term_stats(tenant_id, graph_id, channel);

CREATE TABLE IF NOT EXISTS graph_canonical_lexicon (
    tenant_id TEXT NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    surface_form TEXT NOT NULL,
    canonical_form TEXT NOT NULL,
    kind VARCHAR(32) NOT NULL,
    support_count INTEGER NOT NULL DEFAULT 0,
    score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    meta JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, graph_id, surface_form, canonical_form, kind)
);

CREATE INDEX IF NOT EXISTS idx_graph_canonical_lexicon_tenant_graph
    ON graph_canonical_lexicon(tenant_id, graph_id);

CREATE INDEX IF NOT EXISTS idx_graph_canonical_lexicon_surface
    ON graph_canonical_lexicon(tenant_id, graph_id, surface_form);

CREATE INDEX IF NOT EXISTS idx_graph_canonical_lexicon_kind
    ON graph_canonical_lexicon(tenant_id, graph_id, kind);

CREATE INDEX IF NOT EXISTS idx_edges_semantic_distributional_synonym
    ON edges(tenant_id, graph_id, dst_node_id)
    WHERE kind = 'distributional_synonym';

CREATE INDEX IF NOT EXISTS idx_edges_semantic_paraphrase
    ON edges(tenant_id, graph_id, dst_node_id)
    WHERE kind = 'paraphrase';

COMMENT ON TABLE graph_term_stats IS
    'Graph-scoped canonical term statistics and bounded context co-occurrence maps';

COMMENT ON TABLE graph_canonical_lexicon IS
    'Graph-scoped canonical lexical mappings mined from aliases, phrase patterns, and corpus statistics';
