-- =============================================================================
-- Stage-P2: Tenant DEK Rotation Metadata
-- Version: 0027
-- =============================================================================

ALTER TABLE tenant_crypto_keys
    ADD COLUMN IF NOT EXISTS master_key_fingerprint TEXT NOT NULL DEFAULT '';

COMMENT ON COLUMN tenant_crypto_keys.master_key_fingerprint
    IS 'SHA256 fingerprint of the master key used to wrap dek_wrapped';
