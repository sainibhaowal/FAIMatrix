-- Migration 0024: Cognitive type classification and galaxy grouping for neural constellation view
-- Enables Explore tab to show colored neighborhoods by memory type and document galaxies

-- Add cognitive_type for memory classification (fact, event, procedure, prediction, contradiction, source)
ALTER TABLE nodes ADD COLUMN cognitive_type VARCHAR(16);
CREATE INDEX IF NOT EXISTS idx_nodes_cognitive_type ON nodes (tenant_id, graph_id, cognitive_type);

-- Add galaxy_id for document/source grouping (each document becomes a galaxy center)
ALTER TABLE nodes ADD COLUMN galaxy_id VARCHAR(64);
CREATE INDEX IF NOT EXISTS idx_nodes_galaxy_id ON nodes (tenant_id, graph_id, galaxy_id);

-- Create galaxy metadata table for document/galaxy centers
CREATE TABLE IF NOT EXISTS galaxies (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    galaxy_id VARCHAR(64) NOT NULL,
    raw_id VARCHAR(128),                    -- Source document/file ID
    title TEXT,                             -- Galaxy name (derived from document)
    node_count INTEGER NOT NULL DEFAULT 0,  -- Number of nodes in this galaxy
    cognitive_summary JSONB,                -- {fact: 12, event: 5, procedure: 3, ...}
    center_vector JSONB,                    -- Average position for visualization
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, graph_id, galaxy_id)
);

CREATE INDEX IF NOT EXISTS idx_galaxies_tenant_graph ON galaxies (tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_galaxies_raw_id ON galaxies (raw_id);

-- Migration complete: Neural constellation infrastructure ready
