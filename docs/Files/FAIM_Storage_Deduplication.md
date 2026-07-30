# FAIM Storage & Deduplication System

A complete guide to how FAIM Lab stores, deduplicates, and manages memory efficiently.

---

## Overview

FAIM Lab uses **intelligent deduplication** instead of byte compression. This means:

- **No information is ever lost** (lossless)
- **Identical content is stored once** (space efficient)
- **Each document has its own node tree** (clear relationships)
- **Shared payloads across documents** (no duplication)

---

## How Storage Works

### Step 1: Document Upload

When you upload a PDF, DOCX, or any document:

```
ravindersingh.pdf (10MB)
        │
        ▼
   Document Parser
        │
        ▼
   Split into Chunks (~500 chars each)
        │
        ▼
   ~200 chunks ready for storage
```

### Step 2: Chunk Hashing

Each chunk gets a SHA256 hash based on its **content** (not filename):

```python
# From postgres_store.py line 181
payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

Example:

```
Chunk: "Education: Bachelor of Computer Science from MIT..."
Hash:  "a3f2b8c9d4e5..."  (unique fingerprint)
```

### Step 3: Deduplication Check

Before storing, FAIM checks if this hash already exists:

```python
# From postgres_store.py lines 184-191
existing = self._db.query(PayloadStorageModel).filter(
    PayloadStorageModel.payload_ref == str(payload_ref)
).first()

if not existing:
    # Store new payload
else:
    # Skip - already exists!
```

### Step 4: Return Reference

Whether new or existing, the same `payload_ref` is returned:

```python
return payload_ref  # Points to the stored data
```

---

## Real-World Example

### Scenario: Two Similar PDFs

**PDF 1:** `ravindersingh.pdf`

- 100 pages
- Parsed into 200 chunks

**PDF 2:** `ravindersaini.pdf`

- Same 100 pages, but:
  - Name changed (Singh → Saini)
  - 2 words changed inside

### What Gets Stored

| Upload         | Chunks | New Storage          | Reused |
| -------------- | ------ | -------------------- | ------ |
| PDF 1 (first)  | 200    | 200 chunks (~10MB)   | 0      |
| PDF 2 (second) | 200    | **3 chunks** (~15KB) | 197    |

**Total saved:** 197 chunks × ~50KB = ~9.85MB

---

## Node Relationships

### Fractal Inheritance Structure

```
UNIVERSE (Root Node)
    │
    ├── ravindersingh.pdf (Document Node)
    │   │
    │   ├── Section 1: Introduction (fraction=0.618)
    │   │   ├── Chunk 1.1 → payload_ref: aaa111
    │   │   └── Chunk 1.2 → payload_ref: bbb222
    │   │
    │   └── Section 2: Experience (fraction=0.618)
    │       ├── Chunk 2.1 → payload_ref: ccc333
    │       └── Chunk 2.2 → payload_ref: ddd444
    │
    └── ravindersaini.pdf (SEPARATE Document Node)
        │
        ├── Section 1: Introduction (fraction=0.618)
        │   ├── Chunk 1.1 → payload_ref: xxx111 (NEW - name changed)
        │   └── Chunk 1.2 → payload_ref: bbb222 (SHARED!)
        │
        └── Section 2: Experience (fraction=0.618)
            ├── Chunk 2.1 → payload_ref: ccc333 (SHARED!)
            └── Chunk 2.2 → payload_ref: ddd444 (SHARED!)
```

### Key Points

| Aspect            | Behavior                                         |
| ----------------- | ------------------------------------------------ |
| **Nodes**         | Each document has its OWN separate nodes         |
| **Parents**       | Each document has its OWN parent-child hierarchy |
| **Payloads**      | SHARED when content is identical                 |
| **Relationships** | Clear and traceable per document                 |

---

## Database Tables

### NodeStorage

```sql
CREATE TABLE nodes (
    node_id      TEXT PRIMARY KEY,
    graph_id     TEXT,
    project_id   UUID,
    vec          BYTEA,        -- Embedding vector
    parents      JSONB,        -- Parent references with fractions
    children     TEXT[],       -- Child node IDs
    payload_ref  TEXT,         -- Points to PayloadStorage
    use_count    INTEGER,      -- For evolution
    created_at   TIMESTAMP,
    last_used_at TIMESTAMP
);
```

### PayloadStorage

```sql
CREATE TABLE payloads (
    payload_ref  TEXT PRIMARY KEY,  -- SHA256 hash
    graph_id     TEXT,
    project_id   UUID,
    content      TEXT,              -- Full text content
    encrypted    BOOLEAN,
    created_at   TIMESTAMP
);
```

---

## How Retrieval Works

### When You Query

```python
# User searches for "MIT education"
results = engine.retrieve("MIT education", k=10)
```

### FAIM Does

1. **Vector search** - Find nodes with similar embeddings
2. **Get payload_ref** - Each node points to its payload
3. **Fetch content** - `get_payload(payload_ref)` returns full text
4. **Return results** - Complete, lossless content

### Multiple Documents, Same Content

```
Query: "Bachelor of Computer Science from MIT"

Found in:
├── ravindersingh.pdf (Node A) → payload_ref: bbb222
└── ravindersaini.pdf (Node B) → payload_ref: bbb222 (same!)

Both point to ONE stored payload. Content retrieved once.
```

---

## Storage Efficiency Summary

| Method                  | Description                | Savings                  |
| ----------------------- | -------------------------- | ------------------------ |
| **Chunk Deduplication** | Same chunks stored once    | ~30-80% for similar docs |
| **Evolution Pruning**   | Unused nodes removed       | Variable                 |
| **Fractal Inheritance** | Children reference parents | Structural only          |

---

## Code Locations

| Feature           | File                             | Function                   |
| ----------------- | -------------------------------- | -------------------------- |
| Payload storage   | `faim/storage/postgres_store.py` | `store_payload()`          |
| Payload retrieval | `faim/storage/postgres_store.py` | `get_payload()`            |
| Node storage      | `faim/storage/postgres_store.py` | `put()`                    |
| Chunking          | `faim/api/document_parsers.py`   | `chunk_text()`             |
| Inheritance       | `faim/core/math.py`              | `construct_child_vector()` |

---

## FAQ

### Q: Is any data lost?

**A:** No. Full content is stored. Only duplicates are skipped.

### Q: What if I change the filename?

**A:** Filename doesn't matter. Only content is hashed.

### Q: How much space do I save?

**A:** Depends on similarity:

- 90% similar documents → ~90% savings
- Completely different documents → 0% savings

### Q: Can I retrieve the original document?

**A:** Yes. Each document node has its own chunk references.

### Q: Does this affect search quality?

**A:** No. Each document has its own nodes with proper embeddings.
