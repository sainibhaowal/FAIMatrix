-- =============================================================================
-- Phase K2: Tenant API Key Scope/Expiry Upgrade + Audit Log
-- =============================================================================
-- Version: 0008
-- Description:
--   - Extend tenant_api_keys with scope, expiry, and lifecycle metadata.
--   - Add auth_key_audit_log append-only audit trail table.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Extend tenant_api_keys (additive only)
-- -----------------------------------------------------------------------------
ALTER TABLE tenant_api_keys
    ADD COLUMN IF NOT EXISTS scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS revoked_reason TEXT,
    ADD COLUMN IF NOT EXISTS created_by TEXT,
    ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS rotated_from_key_id TEXT;

CREATE INDEX IF NOT EXISTS ix_tenant_api_keys_expires_at
    ON tenant_api_keys(expires_at);

CREATE INDEX IF NOT EXISTS ix_tenant_api_keys_last_used_at
    ON tenant_api_keys(last_used_at DESC);

CREATE INDEX IF NOT EXISTS ix_tenant_api_keys_scopes_gin
    ON tenant_api_keys USING GIN (scopes);

-- -----------------------------------------------------------------------------
-- auth_key_audit_log: append-only audit events for key lifecycle operations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_key_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    key_id TEXT NOT NULL,
    action TEXT NOT NULL,             -- created | verified | rotated | revoked | denied_*
    actor TEXT,
    request_id TEXT,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_auth_key_audit_tenant_key_time
    ON auth_key_audit_log(tenant_id, key_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_auth_key_audit_action_time
    ON auth_key_audit_log(action, created_at DESC);

COMMENT ON TABLE auth_key_audit_log IS
    'Phase K2: append-only key lifecycle audit trail';
COMMENT ON COLUMN auth_key_audit_log.meta IS
    'bounded structured metadata for key operation context';

