-- =============================================================================
-- Stage-11: Security Hardening - Auth Key Tables
-- =============================================================================
-- Version: 0003
-- Description: Secure API key storage with Argon2id hashes.
--
-- Changes:
--   - Create tenant_api_keys table for hashed tenant keys
--   - Create admin_api_keys table for hashed admin keys
--   - Keys are stored as Argon2id hashes, never plaintext
-- =============================================================================

-- Tenant API Keys (replaces TENANT_KEYS_JSON environment variable)
CREATE TABLE IF NOT EXISTS tenant_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    key_id TEXT NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,
    key_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    
    CONSTRAINT uq_tenant_api_keys_tenant_key UNIQUE (tenant_id, key_id)
);

-- Index for fast lookup by tenant + active status
CREATE INDEX IF NOT EXISTS ix_tenant_api_keys_tenant 
    ON tenant_api_keys(tenant_id);

CREATE INDEX IF NOT EXISTS ix_tenant_api_keys_active 
    ON tenant_api_keys(tenant_id, revoked_at) 
    WHERE revoked_at IS NULL;

-- Admin API Keys (replaces ADMIN_KEYS_JSON environment variable)
CREATE TABLE IF NOT EXISTS admin_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id TEXT NOT NULL,
    key_id TEXT NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,
    key_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    
    CONSTRAINT uq_admin_api_keys_admin_key UNIQUE (admin_id, key_id)
);

CREATE INDEX IF NOT EXISTS ix_admin_api_keys_admin 
    ON admin_api_keys(admin_id);

-- Comment for documentation
COMMENT ON TABLE tenant_api_keys IS 'Stage-11: Hashed API keys for tenant authentication';
COMMENT ON TABLE admin_api_keys IS 'Stage-11: Hashed API keys for admin authentication';
COMMENT ON COLUMN tenant_api_keys.key_hash IS 'Argon2id hash of the API key - never store plaintext';
COMMENT ON COLUMN tenant_api_keys.key_prefix IS 'First 6 chars of key for UI display only';
