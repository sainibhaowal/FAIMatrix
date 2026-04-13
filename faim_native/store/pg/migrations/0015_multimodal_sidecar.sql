-- 0015_multimodal_sidecar.sql
--
-- Add additive multimodal sidecar for Phase 7.

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

CREATE INDEX IF NOT EXISTS idx_node_modality_v1_tenant_graph
    ON node_modality_v1(tenant_id, graph_id);

CREATE INDEX IF NOT EXISTS idx_node_modality_v1_hash
    ON node_modality_v1(tenant_id, graph_id, modality_hash);

COMMENT ON TABLE node_modality_v1 IS
    'Additive multimodal sidecar keyed by node_id';
