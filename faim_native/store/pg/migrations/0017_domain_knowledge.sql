CREATE TABLE IF NOT EXISTS graph_domain_lexicon (
    tenant_id VARCHAR(64) NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    surface_form TEXT NOT NULL,
    canonical_form TEXT NOT NULL,
    kind VARCHAR(32) NOT NULL,
    domain_pack VARCHAR(64),
    support_count INTEGER NOT NULL DEFAULT 0,
    score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, graph_id, surface_form, canonical_form, kind)
);

CREATE INDEX IF NOT EXISTS idx_graph_domain_lexicon_graph
    ON graph_domain_lexicon(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_graph_domain_lexicon_surface
    ON graph_domain_lexicon(tenant_id, graph_id, surface_form);
CREATE INDEX IF NOT EXISTS idx_graph_domain_lexicon_kind
    ON graph_domain_lexicon(tenant_id, graph_id, kind);

CREATE TABLE IF NOT EXISTS graph_kb_sources (
    tenant_id VARCHAR(64) NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    source_id VARCHAR(128) NOT NULL,
    source_kind VARCHAR(32) NOT NULL,
    source_hash VARCHAR(64) NOT NULL,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, graph_id, source_id)
);

CREATE INDEX IF NOT EXISTS idx_graph_kb_sources_graph
    ON graph_kb_sources(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_graph_kb_sources_hash
    ON graph_kb_sources(tenant_id, graph_id, source_hash);

CREATE INDEX IF NOT EXISTS idx_edges_semantic_entity_alias
    ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'entity_alias';
CREATE INDEX IF NOT EXISTS idx_edges_semantic_entity_relation
    ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'entity_relation';
CREATE INDEX IF NOT EXISTS idx_edges_semantic_fact_value
    ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'fact_value';
CREATE INDEX IF NOT EXISTS idx_edges_semantic_fact_time
    ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'fact_time';
CREATE INDEX IF NOT EXISTS idx_edges_semantic_domain_term
    ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'domain_term';
CREATE INDEX IF NOT EXISTS idx_edges_semantic_kb_source
    ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'kb_source';

COMMENT ON TABLE graph_domain_lexicon IS
    'Graph-scoped domain lexical mappings mined from KB imports, term induction, and domain packs';
COMMENT ON TABLE graph_kb_sources IS
    'Graph-scoped offline KB import source registry with deterministic source hashes';
