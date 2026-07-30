-- Migration 0026: Add coactivations table
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
