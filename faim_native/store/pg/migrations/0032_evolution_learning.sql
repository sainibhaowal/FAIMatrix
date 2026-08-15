-- =============================================================================
-- Phase 1: Evolution Learning (Outcomes, Policy State, Meta-Metrics)
-- Version: 0032
-- Description:
--   Adds durable storage for per-cycle evolution outcomes, per-graph learned
--   policy state (contextual bandit arms + lambda calibration), and rolling
--   meta-metrics used to prove evolution maturity.
--   All new behavior is opt-in via FAIM_EVOLUTION_LEARNING_ENABLED.
-- =============================================================================

-- Per-cycle evolution outcome rows (before/after metrics + reward).
CREATE TABLE IF NOT EXISTS evolution_outcomes (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    graph_version BIGINT NOT NULL DEFAULT 0,
    cycle_ts TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    merges INT NOT NULL DEFAULT 0,
    prunes INT NOT NULL DEFAULT 0,
    inventions INT NOT NULL DEFAULT 0,
    theories INT NOT NULL DEFAULT 0,
    lambda_before DOUBLE PRECISION NOT NULL DEFAULT 0,
    lambda_after DOUBLE PRECISION NOT NULL DEFAULT 0,
    r_before DOUBLE PRECISION NOT NULL DEFAULT 0,
    r_after DOUBLE PRECISION NOT NULL DEFAULT 0,
    n_before DOUBLE PRECISION NOT NULL DEFAULT 0,
    n_after DOUBLE PRECISION NOT NULL DEFAULT 0,
    d_before DOUBLE PRECISION NOT NULL DEFAULT 0,
    d_after DOUBLE PRECISION NOT NULL DEFAULT 0,
    h_before DOUBLE PRECISION NOT NULL DEFAULT 0,
    h_after DOUBLE PRECISION NOT NULL DEFAULT 0,
    e_before DOUBLE PRECISION NOT NULL DEFAULT 0,
    e_after DOUBLE PRECISION NOT NULL DEFAULT 0,
    retrieval_delta DOUBLE PRECISION,
    reward DOUBLE PRECISION NOT NULL DEFAULT 0,
    policy_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evolution_outcomes_graph_ts
    ON evolution_outcomes(tenant_id, graph_id, cycle_ts DESC);

CREATE INDEX IF NOT EXISTS idx_evolution_outcomes_version
    ON evolution_outcomes(tenant_id, graph_id, graph_version DESC);

-- Per-graph learned policy state (bandit arms + lambda calibration).
CREATE TABLE IF NOT EXISTS evolution_policy_state (
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    policy_version INT NOT NULL DEFAULT 0,
    arms JSONB NOT NULL DEFAULT '{}'::jsonb,
    lambda_calibration JSONB NOT NULL DEFAULT '{}'::jsonb,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tenant_id, graph_id)
);

-- Rolling meta-metrics proving evolution maturity.
CREATE TABLE IF NOT EXISTS evolution_meta_metrics (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    graph_id TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    merge_usefulness DOUBLE PRECISION NOT NULL DEFAULT 0,
    invention_utilization DOUBLE PRECISION NOT NULL DEFAULT 0,
    prune_regret DOUBLE PRECISION NOT NULL DEFAULT 0,
    d_drift DOUBLE PRECISION NOT NULL DEFAULT 0,
    h_drift DOUBLE PRECISION NOT NULL DEFAULT 0,
    alerts JSONB NOT NULL DEFAULT '{}'::jsonb,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_evolution_meta_metrics_graph_ts
    ON evolution_meta_metrics(tenant_id, graph_id, ts DESC);

COMMENT ON TABLE evolution_outcomes IS
    'Per-cycle evolution outcome rows with before/after diagnostics and reward';
COMMENT ON TABLE evolution_policy_state IS
    'Per-graph learned policy state: contextual bandit arms + lambda calibration';
COMMENT ON TABLE evolution_meta_metrics IS
    'Rolling maturity meta-metrics: merge usefulness, invention utilization, prune regret, drift';
