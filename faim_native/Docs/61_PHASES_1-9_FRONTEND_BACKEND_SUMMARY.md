# FAIM Phases 1-9: Frontend vs Backend Summary

Date: 2026-04-16 (updated — all phases implemented and frontend display complete)

## Executive Summary

**All 9 Phases (1-9) are implemented and active.** Phases 1–5 and 7 are backend-only. Phase 6 adds `temporal_status` to the API response — **this field is now displayed in the frontend** via `QueryAnswerCard.tsx`.

---

## What Each Phase Does

| Phase | Component | What It Does | Frontend Impact |
|-------|-----------|-------------|-----------------|
| **1** | Opposition suppression | Removes lower-scoring contradictions from results | None (internal re-ranking) — `query_engine.py:861-934` |
| **2** | Graph-expanded recall | Traverses inheritance edges for candidate recall | None (internal recall) — `query_engine.py:315-472` |
| **3A** | Porter stemming | Normalizes word forms (running → run) | None (query preprocessing) — `porter_stemmer.py:247-296` |
| **3B** | Entity alias expansion | Expands "nyc" → "new york city" | None (query preprocessing) — `text_vectorizer.py:50-78` |
| **3C** | IDF weighting | Boosts queries with rare terms | None (query weighting) — `idf_cache.py:26-91` |
| **4** | Stop-word removal | Removes "the", "is", "a" before vectorization | None (query preprocessing) — `porter_stemmer.py:15-42` |
| **5** | WordNet synonyms | Expands "live" with "dwell", "reside" at query time | None (query expansion) — `synonym_expander.py:80-113` |
| **6** | Temporal labels | Adds `temporal_status: "CURRENT"` or `"HISTORICAL"` to results | **DONE** — displayed in `QueryAnswerCard.tsx` |
| **7** | Inheritance weighting | Blends query with parent vectors | None (internal query enrichment) — `query_engine.py:524-681` |

---

## API Response — Phase 6 Field

```json
{
  "results": [
    {
      "node_id": "uuid-123",
      "score": 0.95,
      "score_components": { ... },
      "level": 0,
      "touch_count": 42,
      "vector_hash": "abc123",
      "temporal_status": "CURRENT"
    }
  ]
}
```

**Values:**
- `"CURRENT"` — Newest contradicting fact (timestamp-based)
- `"HISTORICAL"` — Older contradicting fact (suppressed but labeled)
- `null` — No contradiction (default for most results)

Serialized at `query_flow.py:672`: `"temporal_status": r.get("temporal_status")`

---

## Frontend Implementation — Phase 6 Display (COMPLETE)

### `QueryAnswerCard.tsx`

`temporal_status` is rendered as a colored badge on each result span:

```tsx
function temporalVariant(status?: string | null) {
  if (status === "CURRENT")    return "success";   // green badge
  if (status === "HISTORICAL") return "warning";   // amber badge
  return "outline";
}

// Rendered per span:
<Badge variant={temporalVariant(span.temporal_status)} size="xs">
  {span.temporal_status}
</Badge>
```

### TypeScript Types

`FaimQueryResultItem` and `FaimQueryAnswerSpan` in `ChatContext.tsx` both include:
```typescript
temporal_status?: string | null;
```

### What is NOT displayed (by design)

- `GraphContextPanel.tsx` — shows graph structure nodes (not query result spans); temporal labels are not relevant here
- `CommandPalette.tsx` — shows navigation items; temporal labels are not relevant here

---

## Query Execution Order (verified in `query_flow.py`)

All 9 phases fire on every query in this order:

1. **Canonicalization** — graph-local lexicon + multilingual
2. **Vectorize** — applies Phase 3A (stemming), 3B (aliases), 4 (stopwords), 5 (synonyms)
3. **IDF weighting** — Phase 3C applied to query vector
4. **Inheritance expansion** — Phase 7 blends query with parent vectors (alpha=0.2)
5. **Graph-expanded recall** — Phase 2 multi-hop traversal
6. **FAIM re-rank** — Phase 1 (opposition suppression) + Phase 6 (temporal labeling)
7. **Result serialization** — `temporal_status` included in every result item

---

## Status: All Done

| Phase | Backend | Frontend |
|-------|---------|----------|
| 1 | ✓ Active | N/A |
| 2 | ✓ Active | N/A |
| 3A | ✓ Active | N/A |
| 3B | ✓ Active | N/A |
| 3C | ✓ Active | N/A |
| 4 | ✓ Active | N/A |
| 5 | ✓ Active | N/A |
| 6 | ✓ Active | ✓ Displayed (green/amber badge in QueryAnswerCard) |
| 7 | ✓ Active | N/A |
