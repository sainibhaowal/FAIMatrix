-- Migration 0040: additive validity interval for evidence nodes.
-- NULL endpoints preserve legacy timeless evidence.  No existing evidence is
-- reinterpreted or deleted by this migration.
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS valid_from TIMESTAMPTZ NULL;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS valid_to TIMESTAMPTZ NULL;
CREATE INDEX IF NOT EXISTS idx_nodes_tenant_graph_validity
    ON nodes (tenant_id, graph_id, valid_from, valid_to);
