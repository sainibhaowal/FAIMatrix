# 79 - FAIM Advanced Temporal Contradiction Resolution

## 1. Status
Completed for the current FAIM runtime contract.

FAIM now handles temporal contradiction resolution with:

- transitive opposition detection through bounded inheritance ancestry
- CURRENT vs HISTORICAL labeling
- soft suppression by default
- hard suppression when `include_historical = False`
- supersedes / superseded_by lineage fields in the query API

## 2. What is real

The live query engine now:

- walks ancestry up to 2 hops for candidate contradiction checks
- detects opposition edges across inherited descendants
- uses `created_at` first, then score as a fallback
- marks the newer node as `CURRENT`
- marks the older node as `HISTORICAL`
- exposes lineage links instead of silently deleting history when soft mode is
  enabled

## 3. Configuration and API surface

The query API exposes:

- `include_historical: bool`

Behavior:

- `include_historical = True`
  - keep historical nodes in the result set
  - annotate them with temporal status and lineage
- `include_historical = False`
  - suppress historical nodes from the returned results

## 4. Why it matters

This is the production-safe version of contradiction handling because it
preserves both correctness and traceability:

- deterministic current-state answers when you want a clean result set
- historical traceability when you want to inspect how facts evolved
- downstream UI and narrators can explain why a node was suppressed or kept

## 5. Implementation surface

Source files:

- `/home/sephi-asi/FAIM/faim_native/api/routers/query.py`
- `/home/sephi-asi/FAIM/faim_native/core/query/query_engine.py`
- `/home/sephi-asi/FAIM/faim_native/store/pg/models_faim.py`
- `/home/sephi-asi/FAIM/faim_native/store/pg/schema.sql`

Validation:

- `tests/unit/test_transitive_contradiction.py`
- `tests/acceptance/test_AT_AS2_contradiction_notes.py`
- `tests/unit/test_cortex_runtime.py`

## 6. Runtime truth

The doc’s design intent is now aligned with the shipped runtime. This is not a
future-only concept.

---

*Status: Completed and reconciled to runtime truth*
