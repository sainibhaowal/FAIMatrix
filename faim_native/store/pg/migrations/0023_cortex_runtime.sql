-- Phase 3: Cortex runtime persistence

CREATE TABLE IF NOT EXISTS cortex_sessions (
    session_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    turn_count INTEGER NOT NULL DEFAULT 0,
    last_turn_id TEXT,
    last_task_type TEXT,
    last_query_hash TEXT,
    last_confidence DOUBLE PRECISION,
    last_turn_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cortex_sessions_tenant_graph
    ON cortex_sessions(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_cortex_sessions_updated
    ON cortex_sessions(updated_at DESC);

CREATE TABLE IF NOT EXISTS cortex_turns (
    turn_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    query_text TEXT NOT NULL,
    answer_mode TEXT NOT NULL,
    task_type TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    graph_version INTEGER NOT NULL DEFAULT 0,
    graph_hash TEXT NOT NULL DEFAULT '',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    narrative TEXT NOT NULL DEFAULT '',
    answer_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    brain_state_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    reasoning_count INTEGER NOT NULL DEFAULT 0,
    open_question_count INTEGER NOT NULL DEFAULT 0,
    contradiction_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cortex_turns_session_created
    ON cortex_turns(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cortex_turns_tenant_graph
    ON cortex_turns(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_cortex_turns_query_hash
    ON cortex_turns(query_hash);

CREATE TABLE IF NOT EXISTS cortex_reasoning_nodes (
    node_id TEXT PRIMARY KEY,
    turn_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    branch TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    evidence_node_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    depends_on JSONB NOT NULL DEFAULT '[]'::jsonb,
    output_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cortex_reasoning_nodes_turn
    ON cortex_reasoning_nodes(turn_id);
CREATE INDEX IF NOT EXISTS idx_cortex_reasoning_nodes_tenant_graph
    ON cortex_reasoning_nodes(tenant_id, graph_id);
CREATE INDEX IF NOT EXISTS idx_cortex_reasoning_nodes_branch
    ON cortex_reasoning_nodes(branch);

CREATE TABLE IF NOT EXISTS cortex_writeback_candidates (
    id BIGSERIAL PRIMARY KEY,
    turn_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed',
    reason TEXT NOT NULL DEFAULT '',
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cortex_writeback_candidates_turn
    ON cortex_writeback_candidates(turn_id);
CREATE INDEX IF NOT EXISTS idx_cortex_writeback_candidates_tenant_graph
    ON cortex_writeback_candidates(tenant_id, graph_id);

