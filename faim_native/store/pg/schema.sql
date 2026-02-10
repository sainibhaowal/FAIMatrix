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

-- -----------------------------------------------------------------------------
-- edges: inheritance and opposition edges
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS edges (
    edge_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,                   -- Stage-7.1: Multi-tenant (required)
    graph_id VARCHAR(64) NOT NULL,
    src_node_id UUID NOT NULL,                 -- parent (inheritance) or node A (opposition)
    dst_node_id UUID NOT NULL,                 -- child (inheritance) or node B (opposition)
    kind VARCHAR(32) NOT NULL,                 -- "inheritance" or "opposition"
    weight DOUBLE PRECISION DEFAULT 0.0,       -- fraction or magnitude
    meta JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uq_edges_tenant_graph_src_dst_kind UNIQUE (tenant_id, graph_id, src_node_id, dst_node_id, kind)
);

-- Stage-7.1: Composite indexes
CREATE INDEX IF NOT EXISTS idx_edges_tenant_graph ON edges(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_edges_child ON edges(tenant_id, graph_id, dst_node_id, kind);
CREATE INDEX IF NOT EXISTS idx_edges_parent ON edges(tenant_id, graph_id, src_node_id, kind);

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
COMMENT ON TABLE edges IS 'FIG graph edges (inheritance and opposition)';

COMMENT ON COLUMN events.seq IS 'Auto-assigned sequence for strict ordering';
COMMENT ON COLUMN events.checksum IS 'SHA256(ts||graph_id||kind||payload) for integrity';
COMMENT ON COLUMN snapshots.graph_hash IS 'Deterministic hash of graph state at snapshot time';
COMMENT ON COLUMN nodes.kind IS 'Node type: atom (level 0) or macro (level > 0)';
COMMENT ON COLUMN nodes.v_native IS 'FAIM-native vector (256 dimensions)';
COMMENT ON COLUMN edges.kind IS 'Edge type: inheritance (parent-child) or opposition';
COMMENT ON COLUMN edges.weight IS 'Inheritance fraction (Σ=1) or opposition magnitude';

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
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

COMMENT ON TABLE users IS 'Formal user registry for identity management (Enterprise Hardening)';
