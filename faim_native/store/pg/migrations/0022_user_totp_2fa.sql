-- Migration: 0022_user_totp_2fa
-- Description: Adds optional TOTP authenticator login and recovery codes.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS totp_secret_encrypted TEXT,
    ADD COLUMN IF NOT EXISTS totp_confirmed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS recovery_code_hashes JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_users_totp_enabled ON users(totp_enabled);

COMMENT ON COLUMN users.totp_enabled IS 'Whether authenticator-app TOTP login is enabled for this user';
COMMENT ON COLUMN users.totp_secret_encrypted IS 'Encrypted TOTP seed; never stored or logged in plaintext';
COMMENT ON COLUMN users.recovery_code_hashes IS 'Argon2id hashes of one-time recovery codes';
