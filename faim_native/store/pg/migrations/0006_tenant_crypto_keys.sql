-- =============================================================================
-- Stage-P2: Tenant DEK Table for Envelope Encryption-at-Rest
-- Version: 0006
-- =============================================================================

CREATE TABLE IF NOT EXISTS tenant_crypto_keys (
    tenant_id TEXT PRIMARY KEY,
    dek_wrapped BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    rotated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tenant_crypto_keys_created
    ON tenant_crypto_keys(created_at DESC);

COMMENT ON TABLE tenant_crypto_keys IS 'P2 wrapped tenant DEKs for envelope encryption';
COMMENT ON COLUMN tenant_crypto_keys.dek_wrapped IS 'Encrypted tenant DEK';
