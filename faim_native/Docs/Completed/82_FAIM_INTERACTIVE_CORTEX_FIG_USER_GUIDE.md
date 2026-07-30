# 82 - FAIM Interactive Cortex & FIG View User Guide

## 1. Status
Completed for the current FAIM runtime contract.

This guide describes the real interactive lifecycle of a user query in FAIM.
It matches the current Cortex + FIG View runtime and is not a speculative
mock-up.

## 2. What is real

- Cortex accepts the user query through the chat/API surface
- the query is routed through the deterministic Cortex runtime
- retrieval expands through the live semantic and graph layers
- FIG View receives active reasoning paths, overlay mode, and timeline state
- the canvas, inspector, relation drawer, and legend reuse the same proof
  surfaces
- temporal contradiction handling can mark nodes as CURRENT or HISTORICAL
- uploads can create new facts that later show up in the next query and graph
  state

## 3. User-facing scenarios

### Scenario A: Grounded answer
The user asks a stable factual question. FAIM:

- recalls candidates
- expands from inheritance and semantic context
- ranks the best evidence
- returns a grounded answer
- highlights the evidence trail in FIG View

### Scenario B: Temporal contradiction
The user asks about a fact that changed over time. FAIM:

- recalls conflicting facts
- resolves CURRENT vs HISTORICAL
- surfaces lineage fields
- dims the superseded node in FIG View
- keeps the correction visible in the answer and trace drawer

### Scenario C: New upload changes memory
The user uploads a document that introduces updated facts. FAIM:

- ingests the file
- stores the new memory
- evolves graph state through the approved runtime path
- exposes the new fact in the next query
- shows the updated node/path state in FIG View

## 4. Implementation surface

Source files:

- `/home/sephi-asi/FAIM/faim_native/api/routers/cortex.py`
- `/home/sephi-asi/FAIM/faim_native/core/cortex/runtime.py`
- `/home/sephi-asi/FAIM/faim_native/core/query/query_engine.py`
- `/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py`
- `/home/sephi-asi/FAIM/faim_native/api/routers/graph.py`
- `/home/sephi-asi/FAIM/frontend/src/contexts/ChatContext.tsx`
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigViewPage.tsx`
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigCanvas.tsx`
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigInspector.tsx`
- `/home/sephi-asi/FAIM/frontend/src/components/graph/FigRelationPanel.tsx`

## 5. What the user sees

- a grounded answer card in chat
- source/provenance information
- active reasoning path highlights
- temporal CURRENT/HISTORICAL badges
- a live FIG View graph with overlay and timeline state

## 6. Runtime truth

This user guide is aligned with the shipped runtime. It does not claim a
separate hidden cognition service or a fake visual-only mock layer.

## 7. Validation

Relevant runtime coverage is already present in:

- `tests/acceptance/test_AT_Q7_query_flow.py`
- `tests/acceptance/test_AT_semantic_fusion_determinism.py`
- `tests/acceptance/test_AT_fig_interaction_pulse_write.py`
- `tests/unit/test_transitive_contradiction.py`

---

*Status: Completed and reconciled to runtime truth*
