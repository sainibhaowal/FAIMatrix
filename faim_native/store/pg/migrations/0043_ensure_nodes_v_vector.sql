-- Migration 0043: ensure pgvector v_vector column, trigger, and HNSW index exist on nodes.
-- Repairs environments where 0025 was stamped before nodes.v_vector existed.

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE nodes ADD COLUMN IF NOT EXISTS v_vector vector(256);

UPDATE nodes
SET v_vector = CAST(v_native::text AS vector(256))
WHERE v_vector IS NULL;

CREATE OR REPLACE FUNCTION sync_v_vector() RETURNS trigger AS $$
BEGIN
    NEW.v_vector = CAST(NEW.v_native::text AS vector(256));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_v_vector ON nodes;
CREATE TRIGGER trg_sync_v_vector
    BEFORE INSERT OR UPDATE OF v_native ON nodes
    FOR EACH ROW EXECUTE FUNCTION sync_v_vector();

CREATE INDEX IF NOT EXISTS idx_nodes_v_vector_hnsw
    ON nodes USING hnsw (v_vector vector_cosine_ops);
