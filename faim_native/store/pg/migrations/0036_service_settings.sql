-- Migration 0036: service_settings table
-- Generic per-tenant durable settings store for operator-facing provider
-- state (e.g., reranker activation) so toggles survive restarts.

CREATE TABLE IF NOT EXISTS service_settings (
    tenant_id  VARCHAR(64) NOT NULL,
    key        VARCHAR(128) NOT NULL,
    value_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, key)
);

COMMENT ON TABLE service_settings IS
    'Per-tenant durable service settings (reranker activation, etc.).';
