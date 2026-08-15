-- Migration 0037: cortex_tool_approvals
-- Human-in-the-loop approval ledger for agent tool actions (upload,
-- delete, reingest, retry). Cortex agents record proposed actions here;
-- an operator approves or rejects them, then approved actions are
-- executed once with a stored receipt.

CREATE TABLE IF NOT EXISTS cortex_tool_approvals (
    id                   BIGSERIAL PRIMARY KEY,
    tenant_id            VARCHAR(64)  NOT NULL,
    graph_id             VARCHAR(64)  NOT NULL,
    session_id           VARCHAR(64),
    turn_id              VARCHAR(64),
    tool_name            VARCHAR(128) NOT NULL,
    status               VARCHAR(32)  NOT NULL DEFAULT 'pending',
    execution_status     VARCHAR(32)  NOT NULL DEFAULT 'pending',
    args_json            JSONB NOT NULL DEFAULT '{}'::jsonb,
    reason               TEXT NOT NULL DEFAULT '',
    proposed_by          VARCHAR(128) NOT NULL DEFAULT 'agent_cortex',
    decision_by          VARCHAR(128),
    decision_note        TEXT,
    execution_receipt_json JSONB DEFAULT '{}'::jsonb,
    execution_error      TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at           TIMESTAMPTZ,
    executed_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_cortex_tool_approvals_tenant_status
    ON cortex_tool_approvals (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_cortex_tool_approvals_tool
    ON cortex_tool_approvals (tool_name);
CREATE INDEX IF NOT EXISTS idx_cortex_tool_approvals_created
    ON cortex_tool_approvals (created_at);

COMMENT ON TABLE cortex_tool_approvals IS
    'Human-in-the-loop approval ledger for agent storage actions.';
