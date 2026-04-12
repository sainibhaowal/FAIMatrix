-- =============================================================================
-- Phase 8: Semantic Edge Typing and Weighting
-- Migration: 0011_semantic_edge_types.sql
-- Description:
--   1. Add GIN index on edges.meta for fast semantic_type lookups (Layer A)
--   2. Add partial indexes per semantic kind for efficient traversal (Layer B)
--   3. Update schema comment on edges.kind to document new semantic kinds
--
-- Notes:
--   - NO ALTER TABLE needed: kind VARCHAR(32) and meta JSONB already exist
--   - The unique constraint uq_edges_tenant_graph_src_dst_kind already partitions
--     semantic edges (kind="synonym") from inheritance edges correctly
--   - This migration is idempotent: CREATE INDEX IF NOT EXISTS
-- =============================================================================

-- GIN index on meta JSONB for fast semantic_type queries (Layer A)
CREATE INDEX IF NOT EXISTS idx_edges_meta_semantic_type
    ON edges USING GIN (meta jsonb_path_ops)
    WHERE meta IS NOT NULL;

-- Partial indexes for each semantic kind (fast kind-filtered traversal, Layer B)
CREATE INDEX IF NOT EXISTS idx_edges_semantic_synonym
    ON edges(tenant_id, graph_id, dst_node_id)
    WHERE kind = 'synonym';

CREATE INDEX IF NOT EXISTS idx_edges_semantic_hypernym
    ON edges(tenant_id, graph_id, dst_node_id)
    WHERE kind = 'hypernym';

CREATE INDEX IF NOT EXISTS idx_edges_semantic_hyponym
    ON edges(tenant_id, graph_id, dst_node_id)
    WHERE kind = 'hyponym';

CREATE INDEX IF NOT EXISTS idx_edges_semantic_related
    ON edges(tenant_id, graph_id, dst_node_id)
    WHERE kind = 'related';

-- Partial index on inheritance edges with semantic meta (for explain queries)
CREATE INDEX IF NOT EXISTS idx_edges_inheritance_has_meta
    ON edges(tenant_id, graph_id, dst_node_id, weight)
    WHERE kind = 'inheritance' AND meta IS NOT NULL;

-- Update schema comments
COMMENT ON COLUMN edges.kind IS
    'Edge type: inheritance (parent-child), opposition (contradiction), or semantic (synonym, hypernym, hyponym, related)';
COMMENT ON COLUMN edges.meta IS
    'Semantic metadata: {"semantic_type": str, "semantic_weight": float} for inheritance edges (Layer A); NULL for opposition and semantic edges';
