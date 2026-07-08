-- =============================================================================
-- Phase 72: Cortex writeback execution receipts
-- Version: 0031
-- Description:
--   Adds explicit execution lifecycle fields and idempotency receipts for
--   Cortex writeback candidates.
-- =============================================================================

ALTER TABLE cortex_writeback_candidates
    ADD COLUMN IF NOT EXISTS execution_status TEXT NOT NULL DEFAULT 'pending';

ALTER TABLE cortex_writeback_candidates
    ADD COLUMN IF NOT EXISTS execution_key TEXT;

ALTER TABLE cortex_writeback_candidates
    ADD COLUMN IF NOT EXISTS execution_request_hash TEXT;

ALTER TABLE cortex_writeback_candidates
    ADD COLUMN IF NOT EXISTS execution_receipt_json JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE cortex_writeback_candidates
    ADD COLUMN IF NOT EXISTS execution_error TEXT;

ALTER TABLE cortex_writeback_candidates
    ADD COLUMN IF NOT EXISTS executed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_cortex_writeback_candidates_execution_key
    ON cortex_writeback_candidates(execution_key);

CREATE INDEX IF NOT EXISTS idx_cortex_writeback_candidates_execution_status
    ON cortex_writeback_candidates(tenant_id, graph_id, execution_status);

COMMENT ON COLUMN cortex_writeback_candidates.execution_status IS
    'Execution lifecycle for the candidate: pending, running, executed, failed, skipped, replayed';

COMMENT ON COLUMN cortex_writeback_candidates.execution_key IS
    'Deterministic idempotency key for the execution receipt';

COMMENT ON COLUMN cortex_writeback_candidates.execution_request_hash IS
    'Deterministic hash of the execution request payload';

COMMENT ON COLUMN cortex_writeback_candidates.execution_receipt_json IS
    'Execution receipt for the memory write or replayed result';

COMMENT ON COLUMN cortex_writeback_candidates.execution_error IS
    'Truncated execution failure detail if the writeback fails';

COMMENT ON COLUMN cortex_writeback_candidates.executed_at IS
    'Timestamp when the candidate execution was attempted or completed';
