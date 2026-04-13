CREATE TABLE IF NOT EXISTS graph_multilingual_lexicon (
    tenant_id VARCHAR(64) NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    language VARCHAR(8) NOT NULL,
    surface_form TEXT NOT NULL,
    canonical_form TEXT NOT NULL,
    concept_key TEXT NOT NULL,
    score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, graph_id, language, surface_form, canonical_form)
);

CREATE INDEX IF NOT EXISTS idx_graph_multilingual_lexicon_graph
    ON graph_multilingual_lexicon(tenant_id, graph_id, language);

CREATE INDEX IF NOT EXISTS idx_edges_semantic_concept_surface
    ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'concept_surface';

CREATE INDEX IF NOT EXISTS idx_edges_semantic_translation
    ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'translation';
