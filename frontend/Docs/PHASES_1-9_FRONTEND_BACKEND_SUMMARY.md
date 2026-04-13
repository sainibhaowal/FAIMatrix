# FAIM Phases 1-9: Frontend vs Backend Summary

## Executive Summary

**All 9 Phases (1-9) are BACKEND-ONLY changes**, with ONE EXCEPTION:
- **Phase 6 (Temporal Contradiction Resolution)** adds a new `temporal_status` field to the API response
- This field is currently **NOT displayed** in the frontend

---

## What Each Phase Does (Backend Only)

| Phase | Component | What It Does | Frontend Impact |
|-------|-----------|-------------|-----------------|
| **1** | Opposition suppression | Removes lower-scoring contradictions from results | None (internal re-ranking) |
| **2** | Graph-expanded recall | Traverses inheritance edges for candidate recall | None (internal recall) |
| **3A** | Porter stemming | Normalizes word forms (running → run) | None (query preprocessing) |
| **3B** | Entity alias expansion | Expands "nyc" → "new york city" | None (query preprocessing) |
| **3C** | IDF weighting | Boosts queries with rare terms | None (query weighting) |
| **4** | Stop-word removal | Removes "the", "is", "a" before vectorization | None (query preprocessing) |
| **5** | WordNet synonyms | Expands "live" with "dwell", "reside" at query time | None (query expansion) |
| **6** | Temporal labels | Adds `temporal_status: "CURRENT"` or `"HISTORICAL"` to results | **NEW FIELD** - needs frontend display |
| **7** | Inheritance weighting | Blends query with parent vectors | None (internal query enrichment) |

---

## API Response Changes

### Before (Original):
```json
{
  "results": [
    {
      "node_id": "uuid-123",
      "score": 0.95,
      "score_components": { ... },
      "level": 0,
      "touch_count": 42,
      "vector_hash": "abc123"
    }
  ]
}
```

### After (Phase 6 Added):
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
      "temporal_status": "CURRENT"  ← NEW FIELD
    }
  ]
}
```

**Values:**
- `"CURRENT"` — Newest contradicting fact (timestamp-based)
- `"HISTORICAL"` — Older contradicting fact (suppressed but labeled)
- `null` — No contradiction (default for most results)

---

## Frontend Components Currently Using Results

### 1. **GraphContextPanel** (`src/components/graph/GraphContextPanel.tsx`)
**Purpose:** Semantic search for related nodes
**Currently Displays:**
- Score (as percentage)
- Kind/label
- Node ID

**NEEDS UPDATE** to show:
- `temporal_status` badge (if present)
- Example: "User lives in NYC" [CURRENT] vs "User lived in Boston" [HISTORICAL]

### 2. **CommandPalette** (`src/components/layout/CommandPalette.tsx`)
**Purpose:** Quick search/navigation
**Currently Displays:**
- Title
- Subtitle
- Node ID

**NEEDS UPDATE** to show:
- `temporal_status` if available

### 3. **Other Panels**
- NodeInspector, NodeRelationsPanel, GraphAnalyticsPanel — mostly display graph structure, not query results
- **NO CHANGES NEEDED** for these

---

## What Frontend Changes Are NEEDED?

### Option 1: Minimal (Display Only)
Update `GraphContextPanel.tsx` to show temporal status:

```tsx
{results.map((node, i) => (
  <div key={node.id}>
    <div className="flex items-center justify-between">
      <span className="text-xs font-medium text-cyan-300">
        #{i + 1} • {node.kind || "memory"}
        {node.temporal_status && (
          <span className={`ml-2 px-2 py-1 text-[10px] rounded ${
            node.temporal_status === "CURRENT" 
              ? "bg-green-500/20 text-green-300" 
              : "bg-yellow-500/20 text-yellow-300"
          }`}>
            {node.temporal_status}
          </span>
        )}
      </span>
    </div>
  </div>
))}
```

**Effort:** ~15 minutes
**Result:** Visual indicator for temporal facts

### Option 2: Comprehensive (Display + Documentation)
- Add temporal_status display to GraphContextPanel
- Add temporal_status display to CommandPalette
- Update TypeScript interfaces (ContextNode type)
- Add tooltip explaining CURRENT vs HISTORICAL
- Show both facts when temporal_status differs

**Effort:** ~1 hour
**Result:** Full temporal awareness in UI

### Option 3: None (API Response Only)
- Leave frontend unchanged
- Backend returns temporal_status but frontend ignores it
- Frontend displays all facts (both CURRENT and HISTORICAL, no suppression)

**Effort:** 0 minutes
**Result:** API has the data, frontend doesn't use it yet

---

## TypeScript Types to Update

### Current (GraphContextPanel.tsx, line 6):
```typescript
interface ContextNode {
  id: string;
  label: string;
  payload: string;
  score: number;
  kind: string;
}
```

### Should Be:
```typescript
interface ContextNode {
  id: string;
  label: string;
  payload: string;
  score: number;
  kind: string;
  node_id?: string;  // Also returned by API
  temporal_status?: "CURRENT" | "HISTORICAL";  // NEW
  touch_count?: number;  // NEW
  vector_hash?: string;  // NEW
}
```

---

## Summary: What You Need to Do

### IF you want to use Phase 6 (temporal labels):

**Step 1:** ✅ DONE — Backend returns `temporal_status` field

**Step 2:** Choose Frontend Update Level
- **Minimal:** Show temporal badge in GraphContextPanel (~15 min)
- **Comprehensive:** Update multiple panels + types (~1 hour)
- **None:** Leave frontend as-is (backend ready, frontend ignores field)

**Step 3:** Update TypeScript interfaces if chosen Step 2

### IF you DON'T care about temporal labels:
- **NO FRONTEND CHANGES NEEDED**
- All 9 Phases work backend-only
- Frontend displays results as-is
- `temporal_status` field in API just returns `null`

---

## Recommendation

**For now:** Leave frontend unchanged
- All Phases 1-9 work fully at the backend level
- No user-facing feature is broken
- Frontend shows best result (Phase 1 suppression still applies)
- Later: Add temporal status display when you have temporal use cases

**Data is ready for future use:** The API returns `temporal_status`, so whenever you want to display "User moved from Boston to NYC", the data is already there.
