-- Migration 0025: Enable pgvector and HNSW index for O(log N) similarity search

-- 1. Enable the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Add the vector column (256 dimensions per FAIM-Native specs)
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS v_vector vector(256);

-- 3. Backfill existing data
UPDATE nodes SET v_vector = CAST(v_native::text AS vector(256)) WHERE v_vector IS NULL;

-- 4. Create trigger to keep it synced
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

-- 5. Create HNSW index for lightning-fast similarity search
-- Note: Requires pgvector >= 0.5.0
CREATE INDEX IF NOT EXISTS idx_nodes_v_vector_hnsw ON nodes USING hnsw (v_vector vector_cosine_ops);
