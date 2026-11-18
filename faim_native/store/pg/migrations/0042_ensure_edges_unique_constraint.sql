-- Migration 0042: ensure uq_edges_tenant_graph_src_dst_kind exists on edges.
-- Uses ANSI SQL EXISTS deduplication so both Postgres and SQLite run cleanly.

DELETE FROM edges
WHERE EXISTS (
    SELECT 1
    FROM edges AS dup
    WHERE edges.tenant_id = dup.tenant_id
      AND edges.graph_id = dup.graph_id
      AND edges.src_node_id = dup.src_node_id
      AND edges.dst_node_id = dup.dst_node_id
      AND edges.kind = dup.kind
      AND (
          edges.created_at < dup.created_at
          OR (edges.created_at = dup.created_at AND edges.edge_id < dup.edge_id)
      )
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_edges_tenant_graph_src_dst_kind'
          AND conrelid = 'edges'::regclass
    ) THEN
        ALTER TABLE edges
            ADD CONSTRAINT uq_edges_tenant_graph_src_dst_kind
            UNIQUE (tenant_id, graph_id, src_node_id, dst_node_id, kind);
    END IF;
END $$;
