# FAIM Core Concepts

The real power of FAIM lies in these 5 foundational concepts. None of them are about byte-level compression—they are about **structuring, organizing, and evolving knowledge intelligently.**

---

## 1. Fractal Inheritance

**What:** New nodes inherit properties from parent nodes, scaled by the golden ratio (φ ≈ 1.618).

```
Document (100% strength)
    └── Section (61.8% strength = 1/φ)
        └── Paragraph (38.2% strength)
            └── Sentence (23.6% strength)
```

**Implementation:** `faim/core/math.py` - `GOLDEN_SCALE`, `construct_child_vector()`

**Purpose:**

- Organize knowledge hierarchically
- Child nodes "know" their parents
- Natural weighting: closer to root = more foundational

---

## 2. Antisymmetric Pruning

**What:** When two nodes are nearly identical (within threshold), merge them instead of keeping duplicates.

```
Node A: "Machine learning is a subset of AI"  ──┐
                                                 ├──→ Single merged node
Node B: "ML is a subset of AI"              ──┘
```

**Implementation:** `faim/core/antisym.py` - `should_merge()`, `merge_records()`

**Purpose:**

- Natural deduplication (no explicit compression needed)
- Reduces graph size automatically
- Preserves semantic meaning

---

## 3. Opposition (Ω Operator)

**What:** Detect and track contradictory information.

```
Node A: "The project deadline is Friday"
Node B: "The project deadline is Monday"  ← Opposition detected

Ω(A, B) = A - B  (difference vector captures the conflict)
```

**Implementation:** `faim/core/antisym.py` - `opposition_vector()`

**Purpose:**

- Handle conflicting facts intelligently
- Track what changed over time
- Enable versioning of knowledge

---

## 4. Self-Evolution

**What:** Automatically improve the graph over time through merge/prune/promote operations.

```
Before Evolution:
├── 1000 nodes
├── 30% redundancy
└── Many cold (unused) leaves

After evolve_graph_once():
├── 700 nodes
├── 5% redundancy
└── Hot paths strengthened
```

**Implementation:** `faim/core/evolution.py` - `evolve_graph_once()`, `EvolutionScheduler`

**Operations:**

- **Merge:** Combine similar nodes
- **Prune:** Remove cold/unused leaves
- **Promote:** Strengthen frequently-used nodes

**Objective Function:** `J = D + λ·H` (Divergence + Entropy trade-off)

---

## 5. Self-Inventing

**What:** Create NEW concepts that weren't explicitly in the source documents.

```
Input Documents:
├── "Apples contain vitamin C"
├── "Vitamin C prevents scurvy"
└── "Sailors got scurvy on long voyages"

Invented Connection:
└── "Apples could have helped sailors" ← Inferred, not stated
```

**Status:** Partially implemented (requires LLM integration for full capability)

**Purpose:**

- Discover hidden insights
- Connect knowledge across domains
- True "understanding" vs just storage

---

## Why No Compression?

FAIM achieves storage efficiency through **semantic operations**, not byte-level compression:

| Approach                  | How It Saves Space                        |
| ------------------------- | ----------------------------------------- |
| **Antisymmetric Pruning** | Merges duplicates → fewer nodes           |
| **Evolution Pruning**     | Removes unused nodes → smaller graph      |
| **Fractal Inheritance**   | Children reference parents → no full copy |
| **Deduplication**         | Same payload = same hash = stored once    |

**Result:** Storage efficiency emerges naturally from the knowledge structure, not from compressing bytes.

---

## File Locations

| Concept               | Primary File                     |
| --------------------- | -------------------------------- |
| Fractal Inheritance   | `faim/core/math.py`              |
| Antisymmetric Ops     | `faim/core/antisym.py`           |
| Evolution Engine      | `faim/core/evolution.py`         |
| Storage (with dedupe) | `faim/storage/postgres_store.py` |
