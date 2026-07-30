-- =============================================================================
-- Phase S1/S2: Self-Evolution Graph Control Overrides
-- Version: 0028
-- Description:
--   Adds graph-scoped control overrides for self-evolve/self-invent behavior.
-- =============================================================================

ALTER TABLE self_evolution_state
    ADD COLUMN IF NOT EXISTS control_self_evolve_enabled BOOLEAN;

ALTER TABLE self_evolution_state
    ADD COLUMN IF NOT EXISTS control_self_evolve_trigger_mode TEXT;

ALTER TABLE self_evolution_state
    ADD COLUMN IF NOT EXISTS control_self_invent_enabled BOOLEAN;

ALTER TABLE self_evolution_state
    ADD COLUMN IF NOT EXISTS control_self_invent_on_evolve BOOLEAN;

ALTER TABLE self_evolution_state
    ADD COLUMN IF NOT EXISTS control_self_invent_after_upload BOOLEAN;

ALTER TABLE self_evolution_state
    ADD COLUMN IF NOT EXISTS control_updated_at TIMESTAMPTZ;

ALTER TABLE self_evolution_state
    ADD COLUMN IF NOT EXISTS control_updated_by TEXT;

COMMENT ON COLUMN self_evolution_state.control_self_evolve_enabled IS
    'Graph-scoped override for self-evolve enablement; NULL falls back to runtime default';

COMMENT ON COLUMN self_evolution_state.control_self_evolve_trigger_mode IS
    'Graph-scoped override for self-evolve trigger mode; NULL falls back to runtime default';

COMMENT ON COLUMN self_evolution_state.control_self_invent_enabled IS
    'Graph-scoped override for self-invent enablement; NULL falls back to runtime default';

COMMENT ON COLUMN self_evolution_state.control_self_invent_on_evolve IS
    'Graph-scoped override for self-invent-on-evolve; NULL falls back to runtime default';

COMMENT ON COLUMN self_evolution_state.control_self_invent_after_upload IS
    'Graph-scoped override for self-invent-after-upload; NULL falls back to runtime default';

COMMENT ON COLUMN self_evolution_state.control_updated_at IS
    'Last time the graph-scoped autonomy control row was updated';

COMMENT ON COLUMN self_evolution_state.control_updated_by IS
    'Best-effort identity of the last user who updated autonomy controls';
