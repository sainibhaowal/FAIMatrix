# FAIM Evolution User Manual

## Overview
The FAIM self-evolution system autonomously improves the cognitive memory graph through three mechanisms: reinforcement learning, theory generation, and synthesis invention. This manual explains how to use these features.

## Accessing Evolution
Navigate to: `/evolve?graph_id=<your-graph-id>

## Available Actions

### 1. Run Evolution
- **Trigger:** Click "Run Evolution" on the evolve page
- **Process:** The system performs:
  - Merges compatible nodes
  - Prunes redundant connections
  - Generates cognitive theories (Step 2c)
  - Synthesis invention (Step 7b, if enabled)
  - Emits evolution events

### 2. Theory Generation
- **When:** During evolve STEP 2c
- **Requirements:** Graph must have nodes in ≥2 different galaxies
- **Output:** Cognitive theories are derived and stored in `graph_theories` table
- **Types:**
  - **Correlation:** Concepts appearing in multiple galaxies
  - **Redundancy:** Clusters of similar nodes
  - **Hierarchy:** Composition patterns
  - **Cognitive Composition:** Higher-level abstractions
- **Query:** `GET /evolve/theories?graph_id=<id>` - returns λ-gated, bounded, idempotent theories

### 3. Synthesis Invention
- **When:** STEP 7b of evolve (gated by `synthesis_bridge_enabled`)
- **Requirements:** Concepts observed in ≥2 galaxies with confidence ≥0.6
- **Output:** New "macros" representing synthesized concepts
- **Events:** Emits `EVOLUTION_INVENTION_SYNTHESIS`
- **Bounded:** Max macros per cycle configured by `synthesis_max_macros`

### 4. View Learning State
- **Endpoint:** `GET /reasoning/learning/state?graph_id=<id>`
- **Shows:** 
  - `total_patterns`: Number of learned patterns
  - `reliability_score`: 0.0–1.0 (high rating + few corrections)
  - `adaptive_strategy`: Recommendations (e.g., "raise confidence thresholds")
- **Durability:** Patterns persist across restarts (written to `reinforcement_pattern_stats` table)

### 5. Feedback & Learning
- **Endpoint:** `POST /api/v1/reasoning/feedback`
- **Payload:**
  ```json
  {
    "turn_id": "<turn-id>",
    "user_rating": 0.8,    // 0.0–1.0
    "session_id": "<session>",
    "graph_id": "<graph>"
  }
  ```
- **Minimum:** 3 ratings per pattern before stats are persisted
- **Correction:** Optional `correction` field for improving future answers

## System Settings (Configurable)
- `FAIM_SELF_EVOLVE_ENABLED` — Enable/disable evolution
- `FAIM_SELF_EVOLVE_TRIGGER_MODE` — `hybrid` / `manual` / `auto`
- `FAIM_SELF_EVOLVE_MIN_INTERVAL_SECONDS` — Minimum time between evolutions
- `FAIM_SELF_EVOLVE_MAX_ACTIONS` — Max actions per evolution cycle
- `synthesis_bridge_enabled` — Enable synthesis invention bridge
- `synthesis_max_macros` — Max macros per invention cycle (default: 3)

## Acceptance Tests
- `test_AT_EV_C_invention_flow_surface.py` — Invention flow
- `test_AT_EV_D_evolution_learning_surface.py` — Learning dashboard
- `test_AT_EV_E_backup_restore_surface.py` — Backup/restore
- `test_AT_EV_F_theory_generation_surface.py` — Theory generation
- `test_AT_EV_G_synthesis_invention_surface.py` — Synthesis invention
- `test_AT_REASON_reasoning_router.py` — Reinforcement learning (6 tests)

## Notes
- Theories require ≥2 galaxies of data
- Synthesis invention requires ≥2 galaxies + confidence ≥0.6
- Evolution is deterministic and idempotent
- All stats persist across restarts
- Config knobs default to conservative (gate disabled)
