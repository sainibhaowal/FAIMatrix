-- FAIM-Native Store Layer Schema
-- Version: v2 (Stage-7.1 - Multi-tenant enforcement)
-- 
-- Tables:
--   raw_refs       - Immutable references to raw blobs
--   events         - Append-only event journal
--   snapshots      - Graph snapshot metadata
--   graph_version  - Version tracking for cache invalidation
--   nodes          - FIG graph nodes
--   edges          - FIG graph edges

-- Enable UUID extension if not available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------------
-- raw_refs: Immutable references to raw blobs
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw_refs (
    id UUID PRIMARY KEY,                    -- UUID7 deterministic
    tenant_id TEXT NOT NULL,                -- Stage-7.1: Multi-tenant (required)
    sha256 VARCHAR(64) NOT NULL,            -- SHA256 hex digest
    uri TEXT NOT NULL,                      -- file://path or s3://bucket/key
    mime_type VARCHAR(128) DEFAULT 'application/octet-stream',
    size_bytes BIGINT NOT NULL,
    graph_id VARCHAR(64),                   -- Optional graph scope
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uq_raw_refs_tenant_sha256 UNIQUE (tenant_id, sha256)
);

CREATE INDEX IF NOT EXISTS idx_raw_refs_tenant_graph ON raw_refs(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_raw_refs_created ON raw_refs(created_at DESC);

-- -----------------------------------------------------------------------------
-- events: Append-only event journal
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    seq BIGSERIAL PRIMARY KEY,              -- Strict ordering (auto-increment)
    id UUID NOT NULL,                       -- UUID7 deterministic
    tenant_id TEXT NOT NULL,                -- Stage-7.1: Multi-tenant (required)
    ts TIMESTAMPTZ NOT NULL,                -- Event timestamp
    graph_id VARCHAR(64) NOT NULL,          -- Graph scope
    kind VARCHAR(64) NOT NULL,              -- Event type
    payload JSONB NOT NULL DEFAULT '{}',    -- Event data
    checksum VARCHAR(64) NOT NULL,          -- SHA256(ts||graph_id||kind||payload)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uq_events_id UNIQUE (id)
);

-- Stage-7.1: Composite index for efficient tenant+graph+seq paging
CREATE INDEX IF NOT EXISTS idx_events_tenant_graph_seq ON events(tenant_id, graph_id, seq);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);

-- -----------------------------------------------------------------------------
-- snapshots: Graph snapshot metadata
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS snapshots (
    id UUID PRIMARY KEY,                    -- UUID7 deterministic
    tenant_id TEXT NOT NULL,                -- Stage-7.1: Multi-tenant (required)
    graph_id VARCHAR(64) NOT NULL,          -- Graph scope
    graph_version BIGINT NOT NULL,          -- Graph version at snapshot time
    graph_hash VARCHAR(64) NOT NULL,        -- Integrity receipt hash
    node_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB,                         -- Optional metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Stage-7.1: Composite index for tenant+graph+created
CREATE INDEX IF NOT EXISTS idx_snapshots_tenant_graph ON snapshots(tenant_id, graph_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_snapshots_version ON snapshots(graph_version);

-- -----------------------------------------------------------------------------
-- graph_version: Version tracking for cache invalidation
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS graph_version (
    tenant_id TEXT NOT NULL,                -- Stage-7.1: Multi-tenant (required)
    graph_id VARCHAR(64) NOT NULL,          -- Graph identifier
    version BIGINT NOT NULL DEFAULT 0,      -- Monotonically increasing version
    reason TEXT,                            -- Reason for last bump
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Stage-7.1: Composite primary key
    PRIMARY KEY (tenant_id, graph_id)
);

-- -----------------------------------------------------------------------------
-- nodes: FIG graph nodes (atoms and macros)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nodes (
    node_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,                -- Stage-7.1: Multi-tenant (required)
    graph_id VARCHAR(64) NOT NULL,
    kind VARCHAR(16) NOT NULL DEFAULT 'atom',  -- "atom" or "macro"
    vector_hash VARCHAR(64) NOT NULL,
    raw_id TEXT,
    block_id TEXT,
    anchor_json JSONB,
    v_native JSONB NOT NULL,                   -- array of floats
    v_vector vector(256),                      -- Stage-11: pgvector representation for HNSW indexing
    opp_signature JSONB,
    residual DOUBLE PRECISION DEFAULT 0.0,
    level INTEGER DEFAULT 0,
    touch_count INTEGER DEFAULT 0,
    last_access TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Stage-7.1: Unique vector_hash per tenant+graph
    CONSTRAINT uq_nodes_tenant_graph_hash UNIQUE (tenant_id, graph_id, vector_hash)
);

-- Stage-7.1: Composite indexes
CREATE INDEX IF NOT EXISTS idx_nodes_tenant_graph ON nodes(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_nodes_created ON nodes(tenant_id, graph_id, created_at, node_id);
CREATE INDEX IF NOT EXISTS idx_nodes_level ON nodes(tenant_id, graph_id, level);

-- Stage-11: pgvector HNSW index
CREATE EXTENSION IF NOT EXISTS vector;
CREATE INDEX IF NOT EXISTS idx_nodes_v_vector_hnsw ON nodes USING hnsw (v_vector vector_cosine_ops);

-- Stage-11: pgvector trigger
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


-- -----------------------------------------------------------------------------
-- node_repr_v2: additive Representation V2 sidecar per node
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS node_repr_v2 (
    node_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    repr_hash VARCHAR(64) NOT NULL,
    normalized_text TEXT NOT NULL DEFAULT '',
    word_counts JSONB NOT NULL DEFAULT '{}',
    phrase_counts JSONB NOT NULL DEFAULT '{}',
    skip_counts JSONB NOT NULL DEFAULT '{}',
    entity_tokens JSONB NOT NULL DEFAULT '[]',
    time_tokens JSONB NOT NULL DEFAULT '[]',
    layout_tokens JSONB NOT NULL DEFAULT '[]',
    semantic_phrase_counts JSONB NOT NULL DEFAULT '{}',
    concept_counts JSONB NOT NULL DEFAULT '{}',
    morphology_counts JSONB NOT NULL DEFAULT '{}',
    alias_families JSONB NOT NULL DEFAULT '[]',
    transliterated_tokens JSONB NOT NULL DEFAULT '[]',
    stem_families JSONB NOT NULL DEFAULT '[]',
    relation_cues JSONB NOT NULL DEFAULT '[]',
    value_cues JSONB NOT NULL DEFAULT '[]',
    temporal_cues JSONB NOT NULL DEFAULT '[]',
    channel_lengths JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_node_repr_v2_tenant_graph ON node_repr_v2(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_node_repr_v2_repr_hash ON node_repr_v2(tenant_id, graph_id, repr_hash);

-- -----------------------------------------------------------------------------
-- node_modality_v1: additive multimodal sidecar per node
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS node_modality_v1 (
    node_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    modality_hash VARCHAR(64) NOT NULL,
    ocr_text TEXT NOT NULL DEFAULT '',
    table_text TEXT NOT NULL DEFAULT '',
    layout_tokens JSONB NOT NULL DEFAULT '[]',
    image_phash VARCHAR(16) NOT NULL DEFAULT '',
    filename_tokens JSONB NOT NULL DEFAULT '[]',
    caption_tokens JSONB NOT NULL DEFAULT '[]',
    metadata_tokens JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_node_modality_v1_tenant_graph ON node_modality_v1(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_node_modality_v1_hash ON node_modality_v1(tenant_id, graph_id, modality_hash);

-- -----------------------------------------------------------------------------
-- graph_repr_v2_stats: graph-scoped BM25/DF statistics by channel
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS graph_repr_v2_stats (
    tenant_id TEXT NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    channel VARCHAR(32) NOT NULL,
    doc_count INTEGER NOT NULL DEFAULT 0,
    avg_len DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    df_map JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, graph_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_graph_repr_v2_stats_tenant_graph ON graph_repr_v2_stats(tenant_id, graph_id);

-- -----------------------------------------------------------------------------
-- graph_term_stats: graph-scoped canonical term statistics
-- -----------------------------------------------------------------------------
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

CREATE INDEX IF NOT EXISTS idx_graph_term_stats_tenant_graph ON graph_term_stats(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_graph_term_stats_channel ON graph_term_stats(tenant_id, graph_id, channel);

-- -----------------------------------------------------------------------------
-- graph_canonical_lexicon: graph-scoped canonical lexical mappings
-- -----------------------------------------------------------------------------
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

CREATE INDEX IF NOT EXISTS idx_graph_canonical_lexicon_tenant_graph ON graph_canonical_lexicon(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_graph_canonical_lexicon_surface ON graph_canonical_lexicon(tenant_id, graph_id, surface_form);
CREATE INDEX IF NOT EXISTS idx_graph_canonical_lexicon_kind ON graph_canonical_lexicon(tenant_id, graph_id, kind);

-- -----------------------------------------------------------------------------
-- graph_multilingual_lexicon: graph-scoped multilingual EN/DE mappings
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS graph_multilingual_lexicon (
    tenant_id TEXT NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    language VARCHAR(8) NOT NULL,
    surface_form TEXT NOT NULL,
    canonical_form TEXT NOT NULL,
    concept_key TEXT NOT NULL,
    score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    meta JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, graph_id, language, surface_form, canonical_form)
);

CREATE INDEX IF NOT EXISTS idx_graph_multilingual_lexicon_graph ON graph_multilingual_lexicon(tenant_id, graph_id, language);

CREATE TABLE IF NOT EXISTS graph_domain_lexicon (
    tenant_id VARCHAR(64) NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    surface_form TEXT NOT NULL,
    canonical_form TEXT NOT NULL,
    kind VARCHAR(32) NOT NULL,
    domain_pack VARCHAR(64),
    support_count INTEGER NOT NULL DEFAULT 0,
    score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    meta JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, graph_id, surface_form, canonical_form, kind)
);
CREATE INDEX IF NOT EXISTS idx_graph_domain_lexicon_graph ON graph_domain_lexicon(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_graph_domain_lexicon_surface ON graph_domain_lexicon(tenant_id, graph_id, surface_form);
CREATE INDEX IF NOT EXISTS idx_graph_domain_lexicon_kind ON graph_domain_lexicon(tenant_id, graph_id, kind);

CREATE TABLE IF NOT EXISTS graph_kb_sources (
    tenant_id VARCHAR(64) NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    source_id VARCHAR(128) NOT NULL,
    source_kind VARCHAR(32) NOT NULL,
    source_hash VARCHAR(64) NOT NULL,
    meta JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, graph_id, source_id)
);
CREATE INDEX IF NOT EXISTS idx_graph_kb_sources_graph ON graph_kb_sources(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_graph_kb_sources_hash ON graph_kb_sources(tenant_id, graph_id, source_hash);

-- -----------------------------------------------------------------------------
-- edges: inheritance and opposition edges
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS edges (
    edge_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,                   -- Stage-7.1: Multi-tenant (required)
    graph_id VARCHAR(64) NOT NULL,
    src_node_id UUID NOT NULL,                 -- parent (inheritance) or node A (opposition)
    dst_node_id UUID NOT NULL,                 -- child (inheritance) or node B (opposition)
    kind VARCHAR(32) NOT NULL,                 -- Edge type: inheritance, opposition, semantic (incl. canonical)
    weight DOUBLE PRECISION DEFAULT 0.0,       -- fraction or magnitude
    meta JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uq_edges_tenant_graph_src_dst_kind UNIQUE (tenant_id, graph_id, src_node_id, dst_node_id, kind)
);

-- Stage-7.1: Composite indexes
CREATE INDEX IF NOT EXISTS idx_edges_tenant_graph ON edges(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_edges_child ON edges(tenant_id, graph_id, dst_node_id, kind);
CREATE INDEX IF NOT EXISTS idx_edges_parent ON edges(tenant_id, graph_id, src_node_id, kind);
CREATE INDEX IF NOT EXISTS idx_edges_semantic_distributional_synonym ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'distributional_synonym';
CREATE INDEX IF NOT EXISTS idx_edges_semantic_paraphrase ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'paraphrase';
CREATE INDEX IF NOT EXISTS idx_edges_semantic_concept_surface ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'concept_surface';
CREATE INDEX IF NOT EXISTS idx_edges_semantic_translation ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'translation';
CREATE INDEX IF NOT EXISTS idx_edges_semantic_entity_alias ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'entity_alias';
CREATE INDEX IF NOT EXISTS idx_edges_semantic_relation_alias ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'relation_alias';
CREATE INDEX IF NOT EXISTS idx_edges_semantic_entity_relation ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'entity_relation';
CREATE INDEX IF NOT EXISTS idx_edges_semantic_fact_value ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'fact_value';
CREATE INDEX IF NOT EXISTS idx_edges_semantic_fact_time ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'fact_time';
CREATE INDEX IF NOT EXISTS idx_edges_semantic_domain_term ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'domain_term';
CREATE INDEX IF NOT EXISTS idx_edges_semantic_kb_source ON edges(tenant_id, graph_id, dst_node_id) WHERE kind = 'kb_source';

-- -----------------------------------------------------------------------------
-- Trigger to enforce append-only on events table
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION prevent_event_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Events table is append-only. Updates and deletes are not allowed.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS events_no_update ON events;
CREATE TRIGGER events_no_update
    BEFORE UPDATE ON events
    FOR EACH ROW
    EXECUTE FUNCTION prevent_event_mutation();

DROP TRIGGER IF EXISTS events_no_delete ON events;
CREATE TRIGGER events_no_delete
    BEFORE DELETE ON events
    FOR EACH ROW
    EXECUTE FUNCTION prevent_event_mutation();

-- -----------------------------------------------------------------------------
-- Trigger to reject empty tenant_id
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION reject_empty_tenant()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.tenant_id IS NULL OR NEW.tenant_id = '' THEN
        RAISE EXCEPTION 'tenant_id cannot be empty';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables
DROP TRIGGER IF EXISTS raw_refs_reject_empty_tenant ON raw_refs;
CREATE TRIGGER raw_refs_reject_empty_tenant BEFORE INSERT OR UPDATE ON raw_refs FOR EACH ROW EXECUTE FUNCTION reject_empty_tenant();

DROP TRIGGER IF EXISTS events_reject_empty_tenant ON events;
CREATE TRIGGER events_reject_empty_tenant BEFORE INSERT ON events FOR EACH ROW EXECUTE FUNCTION reject_empty_tenant();

DROP TRIGGER IF EXISTS snapshots_reject_empty_tenant ON snapshots;
CREATE TRIGGER snapshots_reject_empty_tenant BEFORE INSERT OR UPDATE ON snapshots FOR EACH ROW EXECUTE FUNCTION reject_empty_tenant();

DROP TRIGGER IF EXISTS graph_version_reject_empty_tenant ON graph_version;
CREATE TRIGGER graph_version_reject_empty_tenant BEFORE INSERT OR UPDATE ON graph_version FOR EACH ROW EXECUTE FUNCTION reject_empty_tenant();

DROP TRIGGER IF EXISTS nodes_reject_empty_tenant ON nodes;
CREATE TRIGGER nodes_reject_empty_tenant BEFORE INSERT OR UPDATE ON nodes FOR EACH ROW EXECUTE FUNCTION reject_empty_tenant();

DROP TRIGGER IF EXISTS node_repr_v2_reject_empty_tenant ON node_repr_v2;
CREATE TRIGGER node_repr_v2_reject_empty_tenant BEFORE INSERT OR UPDATE ON node_repr_v2 FOR EACH ROW EXECUTE FUNCTION reject_empty_tenant();
DROP TRIGGER IF EXISTS node_modality_v1_reject_empty_tenant ON node_modality_v1;
CREATE TRIGGER node_modality_v1_reject_empty_tenant BEFORE INSERT OR UPDATE ON node_modality_v1 FOR EACH ROW EXECUTE FUNCTION reject_empty_tenant();

DROP TRIGGER IF EXISTS graph_repr_v2_stats_reject_empty_tenant ON graph_repr_v2_stats;
CREATE TRIGGER graph_repr_v2_stats_reject_empty_tenant BEFORE INSERT OR UPDATE ON graph_repr_v2_stats FOR EACH ROW EXECUTE FUNCTION reject_empty_tenant();

DROP TRIGGER IF EXISTS graph_term_stats_reject_empty_tenant ON graph_term_stats;
CREATE TRIGGER graph_term_stats_reject_empty_tenant BEFORE INSERT OR UPDATE ON graph_term_stats FOR EACH ROW EXECUTE FUNCTION reject_empty_tenant();

DROP TRIGGER IF EXISTS graph_canonical_lexicon_reject_empty_tenant ON graph_canonical_lexicon;
CREATE TRIGGER graph_canonical_lexicon_reject_empty_tenant BEFORE INSERT OR UPDATE ON graph_canonical_lexicon FOR EACH ROW EXECUTE FUNCTION reject_empty_tenant();

DROP TRIGGER IF EXISTS graph_multilingual_lexicon_reject_empty_tenant ON graph_multilingual_lexicon;
CREATE TRIGGER graph_multilingual_lexicon_reject_empty_tenant BEFORE INSERT OR UPDATE ON graph_multilingual_lexicon FOR EACH ROW EXECUTE FUNCTION reject_empty_tenant();
DROP TRIGGER IF EXISTS graph_domain_lexicon_reject_empty_tenant ON graph_domain_lexicon;
CREATE TRIGGER graph_domain_lexicon_reject_empty_tenant BEFORE INSERT OR UPDATE ON graph_domain_lexicon FOR EACH ROW EXECUTE FUNCTION reject_empty_tenant();
DROP TRIGGER IF EXISTS graph_kb_sources_reject_empty_tenant ON graph_kb_sources;
CREATE TRIGGER graph_kb_sources_reject_empty_tenant BEFORE INSERT OR UPDATE ON graph_kb_sources FOR EACH ROW EXECUTE FUNCTION reject_empty_tenant();

DROP TRIGGER IF EXISTS edges_reject_empty_tenant ON edges;
CREATE TRIGGER edges_reject_empty_tenant BEFORE INSERT OR UPDATE ON edges FOR EACH ROW EXECUTE FUNCTION reject_empty_tenant();

-- -----------------------------------------------------------------------------
-- Comments
-- -----------------------------------------------------------------------------
COMMENT ON TABLE raw_refs IS 'Immutable references to raw blobs in blob store';
COMMENT ON TABLE events IS 'Append-only event journal for audit and replay';
COMMENT ON TABLE snapshots IS 'Graph snapshot metadata with integrity receipts';
COMMENT ON TABLE graph_version IS 'Version tracking for cache invalidation';
COMMENT ON TABLE nodes IS 'FIG graph nodes (atoms and macros) with vectors';
COMMENT ON TABLE node_repr_v2 IS 'Additive Representation V2 lexical-semantic sidecar keyed by node_id';
COMMENT ON TABLE node_modality_v1 IS 'Additive multimodal sidecar keyed by node_id';
COMMENT ON TABLE graph_repr_v2_stats IS 'Graph-scoped document-frequency and length statistics for Representation V2 channels';
COMMENT ON TABLE graph_term_stats IS 'Graph-scoped canonical term statistics and bounded context co-occurrence maps';
COMMENT ON TABLE graph_canonical_lexicon IS 'Graph-scoped canonical lexical mappings mined from aliases, phrase patterns, and corpus statistics';
COMMENT ON TABLE graph_multilingual_lexicon IS 'Graph-scoped multilingual EN/DE lexical mappings to shared concept keys';
COMMENT ON TABLE graph_domain_lexicon IS 'Graph-scoped domain lexical mappings mined from KB imports, term induction, and domain packs';
COMMENT ON TABLE graph_kb_sources IS 'Graph-scoped offline KB import source registry with deterministic source hashes';
COMMENT ON TABLE edges IS 'FIG graph edges (inheritance, opposition, and semantic types)';

COMMENT ON COLUMN events.seq IS 'Auto-assigned sequence for strict ordering';
COMMENT ON COLUMN events.checksum IS 'SHA256(ts||graph_id||kind||payload) for integrity';
COMMENT ON COLUMN snapshots.graph_hash IS 'Deterministic hash of graph state at snapshot time';
COMMENT ON COLUMN nodes.kind IS 'Node type: atom (level 0) or macro (level > 0)';
COMMENT ON COLUMN nodes.v_native IS 'FAIM-native vector (256 dimensions)';
COMMENT ON COLUMN node_repr_v2.repr_hash IS 'SHA256 of canonical Representation V2 sparse channels';
COMMENT ON COLUMN node_repr_v2.normalized_text IS 'Deterministic normalized lexical text for explainable reranking';
COMMENT ON COLUMN node_repr_v2.semantic_phrase_counts IS 'Hashed semantic phrase and skip-phrase buckets for FAIM-native semantic matching';
COMMENT ON COLUMN node_repr_v2.concept_counts IS 'Hashed concept-family buckets derived from deterministic concept-key expansion';
COMMENT ON COLUMN node_repr_v2.morphology_counts IS 'Hashed morphology buckets derived from prefix, suffix, shape, and stem-family signals';
COMMENT ON COLUMN node_repr_v2.alias_families IS 'Deterministic alias-family tuples such as llm|large_language_model';
COMMENT ON COLUMN node_repr_v2.transliterated_tokens IS 'Cross-lingual transliteration tokens for lexical bridging';
COMMENT ON COLUMN node_repr_v2.stem_families IS 'Stem-family tuples preserving morphology-level lexical similarity';
COMMENT ON COLUMN node_repr_v2.relation_cues IS 'Deterministic relation cues such as relation:ownership or relation:dependency';
COMMENT ON COLUMN node_repr_v2.value_cues IS 'Deterministic numeric/currency/range cues mined from text';
COMMENT ON COLUMN node_repr_v2.temporal_cues IS 'Deterministic temporal cues mined from date, year, and time language';
COMMENT ON COLUMN node_repr_v2.channel_lengths IS 'Per-channel document lengths for BM25-style scoring';
COMMENT ON COLUMN node_modality_v1.modality_hash IS 'SHA256 of normalized multimodal sidecar payload';
COMMENT ON COLUMN graph_repr_v2_stats.df_map IS 'Document frequency map keyed by hashed term or token';
COMMENT ON COLUMN graph_term_stats.context_terms IS 'Top bounded co-occurring canonical context terms for deterministic PMI-style mining';
COMMENT ON COLUMN graph_canonical_lexicon.kind IS 'Lexical mapping type: alias, acronym, phrase_pattern, distributional_synonym';
COMMENT ON COLUMN edges.kind IS 'Edge type: inheritance, opposition, semantic geometry kinds, canonical semantic kinds, multilingual kinds, or domain knowledge kinds such as entity_alias/entity_relation/fact_value/fact_time/domain_term';
COMMENT ON COLUMN edges.weight IS 'Inheritance fraction (Σ=1) or opposition magnitude';
COMMENT ON COLUMN edges.meta IS 'Semantic metadata for inheritance edges: {semantic_type, semantic_weight}. NULL for opposition and semantic edges.';

-- =============================================================================
-- Stage-9: Production Readiness Tables
-- =============================================================================

-- -----------------------------------------------------------------------------
-- ingest_dedup: Idempotency tracking for ingest operations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ingest_dedup (
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    packet_hash TEXT NOT NULL,
    raw_id UUID,
    node_count INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (tenant_id, graph_id, packet_hash)
);

CREATE INDEX IF NOT EXISTS idx_ingest_dedup_created ON ingest_dedup(created_at DESC);

COMMENT ON TABLE ingest_dedup IS 'Idempotency tracking for ingest operations (Stage-9)';

-- -----------------------------------------------------------------------------
-- jobs: Durable job queue for background operations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
    job_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    kind TEXT NOT NULL,              -- 'evolve', 'backup', 'cleanup'
    payload_json JSONB DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'running', 'done', 'failed'
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_jobs_tenant_status ON jobs(tenant_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_graph ON jobs(tenant_id, graph_id);

COMMENT ON TABLE jobs IS 'Durable job queue for background operations (Stage-9)';

-- -----------------------------------------------------------------------------
-- storage_files: Upload catalog + ingest lifecycle metadata (P1)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS storage_files (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    raw_id UUID NOT NULL,
    filename TEXT NOT NULL,
    mime_type VARCHAR(128) DEFAULT 'application/octet-stream',
    size_bytes BIGINT NOT NULL DEFAULT 0,
    sha256 VARCHAR(64) NOT NULL,
    ingest_status VARCHAR(32) NOT NULL DEFAULT 'uploaded',
    packet_hash VARCHAR(64),
    node_count INTEGER NOT NULL DEFAULT 0,
    vector_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    last_job_id UUID,
    delete_requested BOOLEAN NOT NULL DEFAULT FALSE,
    delete_requested_at TIMESTAMPTZ,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ingested_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_storage_files_tenant_graph_raw UNIQUE (tenant_id, graph_id, raw_id)
);

CREATE INDEX IF NOT EXISTS idx_storage_files_tenant_graph_status
    ON storage_files(tenant_id, graph_id, ingest_status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_storage_files_sha ON storage_files(tenant_id, sha256);
CREATE INDEX IF NOT EXISTS idx_storage_files_last_job ON storage_files(last_job_id);

COMMENT ON TABLE storage_files IS 'P1 storage catalog metadata and ingest lifecycle state';

-- -----------------------------------------------------------------------------
-- memory_write_requests: K5 idempotency ledger for memory/write API
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memory_write_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'in_progress',
    response_json JSONB,
    packet_hash VARCHAR(64),
    raw_id UUID,
    node_count INTEGER NOT NULL DEFAULT 0,
    vector_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    CONSTRAINT uq_memory_write_requests_tenant_graph_key
        UNIQUE (tenant_id, graph_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_memory_write_requests_tenant_graph_status
    ON memory_write_requests(tenant_id, graph_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_memory_write_requests_request_hash
    ON memory_write_requests(request_hash);

COMMENT ON TABLE memory_write_requests IS
    'K5: idempotency ledger for memory write operations';

-- -----------------------------------------------------------------------------
-- tenant_crypto_keys: Wrapped tenant DEKs for envelope encryption (P2)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenant_crypto_keys (
    tenant_id TEXT PRIMARY KEY,
    dek_wrapped BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rotated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tenant_crypto_keys_created
    ON tenant_crypto_keys(created_at DESC);

COMMENT ON TABLE tenant_crypto_keys IS 'P2: wrapped tenant DEKs for envelope encryption at rest';
COMMENT ON COLUMN tenant_crypto_keys.dek_wrapped IS 'DEK encrypted using FAIM master key';

-- -----------------------------------------------------------------------------
-- users: Formal user registry for identity management
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,                    -- UUID5 deterministic (email-based)
    email TEXT NOT NULL UNIQUE,             -- Verified email address
    full_name TEXT,                         -- Display name
    totp_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    totp_secret_encrypted TEXT,
    totp_confirmed_at TIMESTAMPTZ,
    recovery_code_hashes JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_totp_enabled ON users(totp_enabled);

COMMENT ON TABLE users IS 'Formal user registry for identity management (Enterprise Hardening)';

-- -----------------------------------------------------------------------------
-- tenant_api_keys: Hashed tenant API keys with scope/expiry lifecycle (Phase K2)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenant_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    key_id TEXT NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,
    key_hash TEXT NOT NULL,
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    revoked_reason TEXT,
    created_by TEXT,
    rotated_from_key_id TEXT,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tenant_api_keys_tenant_key UNIQUE (tenant_id, key_id)
);

CREATE INDEX IF NOT EXISTS ix_tenant_api_keys_tenant
    ON tenant_api_keys(tenant_id);
CREATE INDEX IF NOT EXISTS ix_tenant_api_keys_active
    ON tenant_api_keys(tenant_id, revoked_at)
    WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_tenant_api_keys_expires_at
    ON tenant_api_keys(expires_at);
CREATE INDEX IF NOT EXISTS ix_tenant_api_keys_last_used_at
    ON tenant_api_keys(last_used_at DESC);
CREATE INDEX IF NOT EXISTS ix_tenant_api_keys_scopes_gin
    ON tenant_api_keys USING GIN (scopes);

COMMENT ON TABLE tenant_api_keys IS
    'Hashed tenant API keys with scope/expiry lifecycle metadata';

-- -----------------------------------------------------------------------------
-- auth_key_audit_log: Append-only key lifecycle audit stream (Phase K2)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_key_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    key_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT,
    request_id TEXT,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_auth_key_audit_tenant_key_time
    ON auth_key_audit_log(tenant_id, key_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_auth_key_audit_action_time
    ON auth_key_audit_log(action, created_at DESC);

COMMENT ON TABLE auth_key_audit_log IS
    'Append-only key lifecycle audit log for create/rotate/revoke/verify actions';

-- -----------------------------------------------------------------------------
-- self_invention_state: Incremental coactivation cursor/counters (Phase J)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS self_invention_state (
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    last_event_seq BIGINT NOT NULL DEFAULT 0,
    signature_counts JSONB NOT NULL DEFAULT '{}',
    last_cycle_macros INTEGER NOT NULL DEFAULT 0,
    last_cycle_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, graph_id)
);

CREATE INDEX IF NOT EXISTS idx_self_invention_state_updated
    ON self_invention_state(updated_at DESC);

COMMENT ON TABLE self_invention_state IS
    'Incremental self-invention runtime state (cursor + bounded coactivation counts)';

-- -----------------------------------------------------------------------------
-- self_evolution_state: Durable scheduler state for self-evolution (Phase S2)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS self_evolution_state (
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    last_seen_version BIGINT NOT NULL DEFAULT 0,
    last_evolved_version BIGINT NOT NULL DEFAULT 0,
    last_evolved_at TIMESTAMPTZ,
    last_enqueued_job_id UUID,
    control_self_evolve_enabled BOOLEAN,
    control_self_evolve_trigger_mode TEXT,
    control_self_invent_enabled BOOLEAN,
    control_self_invent_on_evolve BOOLEAN,
    control_self_invent_after_upload BOOLEAN,
    control_updated_at TIMESTAMPTZ,
    control_updated_by TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, graph_id)
);

CREATE INDEX IF NOT EXISTS idx_self_evolution_state_updated
    ON self_evolution_state(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_self_evolution_state_due
    ON self_evolution_state(tenant_id, last_evolved_at);

COMMENT ON TABLE self_evolution_state IS
    'Durable scheduler state for self-evolution due-graph selection and enqueue dedupe';

-- -----------------------------------------------------------------------------
-- cortex_sessions: Durable Cortex session state (Phase 3)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cortex_sessions (
    session_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    turn_count INTEGER NOT NULL DEFAULT 0,
    last_turn_id TEXT,
    last_task_type TEXT,
    last_query_hash TEXT,
    last_confidence DOUBLE PRECISION,
    last_turn_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cortex_sessions_tenant_graph
    ON cortex_sessions(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_cortex_sessions_updated
    ON cortex_sessions(updated_at DESC);

COMMENT ON TABLE cortex_sessions IS
    'Durable Cortex session state for structured brain turns';

-- -----------------------------------------------------------------------------
-- cortex_turns: Structured Cortex turn snapshots (Phase 3)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cortex_turns (
    turn_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    query_text TEXT NOT NULL,
    answer_mode TEXT NOT NULL,
    task_type TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    graph_version INTEGER NOT NULL DEFAULT 0,
    graph_hash TEXT NOT NULL DEFAULT '',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    narrative TEXT NOT NULL DEFAULT '',
    answer_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    brain_state_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    reasoning_count INTEGER NOT NULL DEFAULT 0,
    open_question_count INTEGER NOT NULL DEFAULT 0,
    contradiction_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cortex_turns_session_created
    ON cortex_turns(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cortex_turns_tenant_graph
    ON cortex_turns(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_cortex_turns_query_hash
    ON cortex_turns(query_hash);

COMMENT ON TABLE cortex_turns IS
    'Structured Cortex turn snapshots including answer packet and brain state';

-- -----------------------------------------------------------------------------
-- cortex_reasoning_nodes: Structured reasoning tree nodes (Phase 3)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cortex_reasoning_nodes (
    node_id TEXT PRIMARY KEY,
    turn_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    branch TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    evidence_node_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    depends_on JSONB NOT NULL DEFAULT '[]'::jsonb,
    output_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cortex_reasoning_nodes_turn
    ON cortex_reasoning_nodes(turn_id);
CREATE INDEX IF NOT EXISTS idx_cortex_reasoning_nodes_tenant_graph
    ON cortex_reasoning_nodes(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_cortex_reasoning_nodes_branch
    ON cortex_reasoning_nodes(branch);

COMMENT ON TABLE cortex_reasoning_nodes IS
    'Structured Cortex reasoning tree nodes with evidence and confidence';

-- -----------------------------------------------------------------------------
-- cortex_writeback_candidates: Proposed memory writes from Cortex (Phase 3)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cortex_writeback_candidates (
    id BIGSERIAL PRIMARY KEY,
    turn_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed',
    reason TEXT NOT NULL DEFAULT '',
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cortex_writeback_candidates_turn
    ON cortex_writeback_candidates(turn_id);
CREATE INDEX IF NOT EXISTS idx_cortex_writeback_candidates_tenant_graph
    ON cortex_writeback_candidates(tenant_id, graph_id);

COMMENT ON TABLE cortex_writeback_candidates IS
    'Proposal-only memory writeback candidates emitted by Cortex';

CREATE TABLE IF NOT EXISTS coactivations (
    tenant_id UUID NOT NULL,
    graph_id TEXT NOT NULL,
    signature TEXT NOT NULL,
    members JSONB NOT NULL,
    coactivation_count INT NOT NULL DEFAULT 1,
    invented BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tenant_id, graph_id, signature)
);

CREATE INDEX IF NOT EXISTS idx_coactivations_pending 
ON coactivations(tenant_id, graph_id) 
WHERE invented = FALSE AND coactivation_count >= 3;
