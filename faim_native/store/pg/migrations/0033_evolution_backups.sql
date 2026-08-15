-- 0033: Evolution pre-action backups (safe undo for destructive actions).
-- Snapshots taken before any node deletion during evolution cycles.

CREATE TABLE IF NOT EXISTS evolution_backups (
    backup_id   UUID PRIMARY KEY,
    tenant_id   VARCHAR(64)  NOT NULL,
    graph_id    VARCHAR(64)  NOT NULL,
    version     INTEGER      NOT NULL DEFAULT 0,
    action_type VARCHAR(32)  NOT NULL DEFAULT 'prune',
    node_id     UUID         NOT NULL,
    reason      TEXT,
    node_json   JSONB        NOT NULL,
    repr_json   JSONB,
    edges_json  JSONB,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_evolution_backups_graph
    ON evolution_backups (tenant_id, graph_id, version);

CREATE INDEX IF NOT EXISTS idx_evolution_backups_node
    ON evolution_backups (tenant_id, graph_id, node_id);