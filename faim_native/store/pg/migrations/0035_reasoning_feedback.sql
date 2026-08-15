-- Migration 0035: reasoning_feedback table
-- Enables the durable feedback loop: user ratings + corrections tied to real
-- cortex turns so reasoning quality learning is never written with placeholders.

CREATE TABLE IF NOT EXISTS reasoning_feedback (
    feedback_id         VARCHAR(36) PRIMARY KEY,
    turn_id             VARCHAR(36) NOT NULL,
    session_id          VARCHAR(36),
    tenant_id           VARCHAR(64) NOT NULL,
    graph_id            VARCHAR(64),
    query_text          TEXT NOT NULL,
    reasoning_path_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    answer_given        TEXT NOT NULL,
    user_rating         DOUBLE PRECISION NOT NULL,
    user_correction     TEXT,
    correction_type     VARCHAR(32),
    pattern_hash        VARCHAR(16) NOT NULL,
    query_signature     VARCHAR(32) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed           VARCHAR(1) NOT NULL DEFAULT '0'
);

CREATE INDEX IF NOT EXISTS idx_reasoning_feedback_tenant_created
    ON reasoning_feedback (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reasoning_feedback_turn
    ON reasoning_feedback (turn_id);
CREATE INDEX IF NOT EXISTS idx_reasoning_feedback_pattern
    ON reasoning_feedback (pattern_hash);

COMMENT ON TABLE reasoning_feedback IS
    'User feedback on reasoning quality, hydrated from durable cortex turns.';
