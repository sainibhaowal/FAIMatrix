-- =============================================================================
-- Stage-P1: Storage Catalog and Upload Metadata
-- Version: 0005
-- Description:
--   Adds storage_files table for operational file catalog, upload lifecycle,
--   and UI-facing status/metrics.
-- =============================================================================

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
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ingested_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_storage_files_tenant_graph_raw UNIQUE (tenant_id, graph_id, raw_id)
);

CREATE INDEX IF NOT EXISTS idx_storage_files_tenant_graph_status
    ON storage_files(tenant_id, graph_id, ingest_status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_storage_files_sha
    ON storage_files(tenant_id, sha256);

CREATE INDEX IF NOT EXISTS idx_storage_files_last_job
    ON storage_files(last_job_id);

COMMENT ON TABLE storage_files IS 'P1 storage catalog metadata and ingest lifecycle state';
COMMENT ON COLUMN storage_files.delete_requested IS 'Logical deletion request flag only; no physical deletion in P1';
