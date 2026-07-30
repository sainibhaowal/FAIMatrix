-- Migration: 0004_enterprise_identity
-- Description: Adds formal users table for identity management and flow enforcement.

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,                    -- UUID5 deterministic (email-based)
    email TEXT NOT NULL UNIQUE,             -- Verified email address
    full_name TEXT,                         -- Display name
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

COMMENT ON TABLE users IS 'Formal user registry for identity management (Enterprise Hardening)';
