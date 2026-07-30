-- =============================================================================
-- Phase K5: Memory write idempotency ledger
-- =============================================================================
-- Version: 0009
-- Description:
--   - Add idempotency table for /api/v1/memory/write safety.
--   - Enforce tenant+graph+idempotency_key uniqueness.
-- =============================================================================

CREATE TABLE IF NOT EXISTS memory_write_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'in_progress', -- in_progress | completed | failed
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
    'Phase K5: idempotency ledger for memory write operations';
COMMENT ON COLUMN memory_write_requests.response_json IS
    'Stored response payload for deterministic replay';
