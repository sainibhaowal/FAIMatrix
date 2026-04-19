-- Migration 0018: Long-term memory flag on nodes
-- Prevents cold pruning from deleting high-value nodes regardless of access recency.
ALTER TABLE nodes ADD COLUMN long_term BOOLEAN NOT NULL DEFAULT false;
