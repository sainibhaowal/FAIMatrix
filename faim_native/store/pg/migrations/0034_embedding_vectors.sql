-- Migration 0034: Add embedding vectors column to nodes table
-- Adds v_embedding column for semantic embeddings (e.g., bge-m3 1024-dim)
-- Does NOT modify existing v_native (256-dim) or v_vector (pgvector trigger) columns

-- Add v_embedding column for semantic embeddings (nullable, 1024-dim typical)
ALTER TABLE nodes 
ADD COLUMN IF NOT EXISTS v_embedding JSONB;

-- Add pgvector column for embedding vectors (nullable, dimension depends on provider)
-- For bge-m3 this is 1024, but we make it generic
ALTER TABLE nodes 
ADD COLUMN IF NOT EXISTS v_embedding_vector vector(1024);

-- Index for embedding vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;
CREATE INDEX IF NOT EXISTS idx_nodes_v_embedding_vector_hnsw 
ON nodes USING hnsw (v_embedding_vector vector_cosine_ops)
WHERE v_embedding_vector IS NOT NULL;

-- Trigger to sync v_embedding_vector from v_embedding (when embedding provider is active)
CREATE OR REPLACE FUNCTION sync_v_embedding_vector() RETURNS trigger AS $$
BEGIN
    IF NEW.v_embedding IS NOT NULL AND NEW.v_embedding::text != 'null' AND NEW.v_embedding::text LIKE '[%' THEN
        BEGIN
            NEW.v_embedding_vector = CAST(NEW.v_embedding::text AS vector(1024));
        EXCEPTION WHEN OTHERS THEN
            NEW.v_embedding_vector = NULL;
        END;
    ELSE
        NEW.v_embedding_vector = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS trg_sync_v_embedding_vector ON nodes;
CREATE TRIGGER trg_sync_v_embedding_vector 
    BEFORE INSERT OR UPDATE OF v_embedding ON nodes
    FOR EACH ROW EXECUTE FUNCTION sync_v_embedding_vector();

-- Comment for documentation
COMMENT ON COLUMN nodes.v_embedding IS 'Semantic embedding vector (e.g., bge-m3 1024-dim). Nullable - only populated when embedding provider is active.';
COMMENT ON COLUMN nodes.v_embedding_vector IS 'pgvector representation of v_embedding for HNSW similarity search (1024-dim for bge-m3).';