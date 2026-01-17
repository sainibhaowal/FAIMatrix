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

-- Baseline Setup

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
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_raw_refs_tenant_sha256 UNIQUE (tenant_id, sha256)
);

CREATE INDEX IF NOT EXISTS idx_raw_refs_tenant_graph ON raw_refs(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_raw_refs_created ON raw_refs(created_at DESC);

-- -----------------------------------------------------------------------------
-- events: Append-only event journal
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    seq SERIAL PRIMARY KEY,              -- Strict ordering (auto-increment)
    id UUID NOT NULL,                       -- UUID7 deterministic
    tenant_id TEXT NOT NULL,                -- Stage-7.1: Multi-tenant (required)
    ts TIMESTAMP NOT NULL,                -- Event timestamp
    graph_id VARCHAR(64) NOT NULL,          -- Graph scope
    kind VARCHAR(64) NOT NULL,              -- Event type
    payload JSON DEFAULT '{}',    -- Event data
    checksum VARCHAR(64) NOT NULL,          -- SHA256(ts||graph_id||kind||payload)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
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
    metadata JSON,                         -- Optional metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
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
    anchor_json JSON,
    v_native JSON NOT NULL,                   -- array of floats
    opp_signature JSON,
    residual DOUBLE PRECISION DEFAULT 0.0,
    level INTEGER DEFAULT 0,
    touch_count INTEGER DEFAULT 0,
    last_access TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
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
    meta JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_edges_tenant_graph_src_dst_kind UNIQUE (tenant_id, graph_id, src_node_id, dst_node_id, kind)
);

-- Stage-7.1: Composite indexes
CREATE INDEX IF NOT EXISTS idx_edges_tenant_graph ON edges(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_edges_child ON edges(tenant_id, graph_id, dst_node_id, kind);
CREATE INDEX IF NOT EXISTS idx_edges_parent ON edges(tenant_id, graph_id, src_node_id, kind);

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
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (tenant_id, graph_id, packet_hash)
);

CREATE INDEX IF NOT EXISTS idx_ingest_dedup_created ON ingest_dedup(created_at DESC);

-- -----------------------------------------------------------------------------
-- jobs: Durable job queue for background operations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
    job_id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    kind TEXT NOT NULL,              -- 'evolve', 'backup', 'cleanup'
    payload_json JSON DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'running', 'done', 'failed'
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_tenant_status ON jobs(tenant_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_graph ON jobs(tenant_id, graph_id);

-- End of migration

