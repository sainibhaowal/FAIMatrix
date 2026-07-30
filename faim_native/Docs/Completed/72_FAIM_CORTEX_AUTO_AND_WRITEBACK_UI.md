# 72 - FAIM Cortex Auto and Writeback UI Report

## 1. Overview
This document clarifies the truthful runtime story behind Cortex auto mode and
writeback-oriented UI behavior.

## 2. What is real now
- Cortex uses a small deterministic task router for mode selection.
- Retrieval before Cortex reasoning is strengthened by:
  - ConceptNet expansion
  - semantic registry runtime
  - canonical semantics
  - multilingual bridges
  - domain-memory expansions
- adaptive bounded hop planning is real
- pulse-v2 graph/query explain ledgers are real and feed FIG View node glow,
  path motion, inspector proof, relation traces, and semantic-layer legends
- structured writeback and memory-update flows are real where implemented in the
  current Cortex/runtime path
- approved writebacks now execute through a durable, idempotent backend path
  and persist a receipt instead of remaining proposal-only

## 3. Important distinction
The older wording implied:
- one giant `1M+ Semantic Registry` directly classifies the task
- Cortex only stores writeback proposals and never executes approved updates

That is not the correct architecture.

The truthful architecture is:
1. retrieval expansion uses the larger semantic registry runtime
2. Cortex mode selection uses the smaller deterministic task router
3. reasoning depth and traversal then follow the planned bounded-hop path
4. FIG View visual proof reads the emitted pulse-v2 reason ledger, not a
   separate guessed overlay
5. approved writebacks now execute through the durable memory pipeline and
   record execution receipts for replay safety

## 4. UI wording guidance
When describing Cortex Auto, use:
- `automatic task routing`
- `semantic-registry-backed retrieval broadening`
- `adaptive bounded hop planning`
- `pulse-v2 FIG proof from graph/query explain payloads`

Do not use:
- `the 1M+ registry directly classifies every turn`
- `writebacks stay proposal-only forever`

## 5. Status
The runtime is real and stronger than the older wording suggested, but the
subsystems should stay clearly separated in documentation and UI copy. Cortex
still gatekeeps structural updates, yet approved writebacks are now real
executions with receipts rather than dead-end proposals.

---
*Status: Documentation reconciled to runtime truth*
