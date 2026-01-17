# FAIM-Native Store Layer Guide

## Overview

The store layer provides production-grade, deterministic storage for FAIM-Native following core doctrine:

- **RawTruth is immutable**: Original bytes stored unchanged
- **Postgres is truth**: Graph/journal/snapshots metadata
- **Event journal is append-only**: No mutations, checksum integrity
- **Everything deterministic**: uuid7 IDs, stable ordering

---

## Core Components

### 1. Core Types (`core/contracts/types.py`)

```python
from core.contracts.types import RawRef, EventRecord, SnapshotRecord, GraphVersion, uuid7

# UUID7 - time-ordered deterministic IDs
id = uuid7()

# RawRef - immutable blob reference
ref = RawRef.create(
    sha256="abc123...",
    uri="file:///path/to/blob",
    size_bytes=1024,
    mime_type="text/plain",
    graph_id="my_graph"
)

# EventRecord - append-only journal entry
event = EventRecord.create(
    graph_id="my_graph",
    kind="node_created",
    payload={"node_id": "abc"}
)
assert event.verify_checksum()  # Integrity check

# SnapshotRecord - point-in-time graph state
snapshot = SnapshotRecord.create(
    graph_id="my_graph",
    graph_version=5,
    graph_hash="def456...",
    node_count=100
)
```

---

### 2. Raw Blob Store (`store/raw/raw_store.py`)

SHA256-addressed immutable filesystem storage.

```python
from store.raw.raw_store import RawStore

store = RawStore("/path/to/blobs")

# Store content (idempotent)
raw_ref = store.store(b"content", mime_type="text/plain")
print(raw_ref.sha256)  # Content hash
print(raw_ref.uri)     # file:///path/to/blobs/ab/abc123...

# Load and verify
content = store.load(raw_ref, verify=True)  # Raises on hash mismatch

# Check existence
assert store.exists(raw_ref)

# Verify integrity
assert store.verify(raw_ref)

# Statistics
stats = store.get_stats()
# {"blob_count": 42, "total_size_bytes": 12345, "store_version": "v1"}
```

**Storage layout:**

```
/blobs/
├── ab/
│   └── abc123def456...  # Full sha256 as filename
├── cd/
│   └── cdef789012...
```

---

### 3. PostgreSQL Layer

#### Session Factory (`store/pg/session.py`)

```python
from store.pg.session import SessionFactory, atomic

factory = SessionFactory("postgresql://user:pass@host/db")

# Context manager with auto-cleanup
with factory.session() as session:
    # work...
    session.commit()

# Atomic transaction (auto-commit/rollback)
with factory.atomic() as session:
    # all operations commit together or rollback
    pass
```

#### ORM Models (`store/pg/models_faim.py`)

| Model               | Table           | Purpose             |
| ------------------- | --------------- | ------------------- |
| `RawRefModel`       | `raw_refs`      | Blob metadata       |
| `EventModel`        | `events`        | Append-only journal |
| `SnapshotModel`     | `snapshots`     | Graph snapshots     |
| `GraphVersionModel` | `graph_version` | Cache invalidation  |

```python
from store.pg.models_faim import create_all_tables

create_all_tables(engine)  # Initialize database
```

---

### 4. Repositories

#### RawRepo (`store/pg/repos/raw_repo.py`)

```python
from store.pg.repos.raw_repo import RawRepo

repo = RawRepo()

# Create (idempotent)
saved = repo.create(session, raw_ref)

# Query
ref = repo.get_by_sha(session, "abc123...")
ref = repo.get_by_id(session, uuid)
refs = repo.list_all(session, graph_id="my_graph", limit=100)

# Check
exists = repo.exists(session, "abc123...")
count = repo.count(session, graph_id="my_graph")
```

#### EventRepo (`store/pg/repos/event_repo.py`)

```python
from store.pg.repos.event_repo import EventRepo

repo = EventRepo()

# Append only (no update/delete)
saved = repo.append(session, event)  # seq auto-assigned

# Read with cursor pagination
events = repo.get_by_seq(session, "my_graph", after_seq=0, limit=100)
latest = repo.get_latest(session, "my_graph")
all_events = repo.get_all(session, "my_graph", kind="node_created")

# Ordering
max_seq = repo.get_max_seq(session, "my_graph")
```

#### SnapshotRepo (`store/pg/repos/snapshot_repo.py`)

```python
from store.pg.repos.snapshot_repo import SnapshotRepo

repo = SnapshotRepo()

# Create
saved = repo.create(session, snapshot)

# Query
snap = repo.get_by_id(session, uuid)
snap = repo.get_latest(session, "my_graph")
snap = repo.get_by_version(session, "my_graph", version=5)
snaps = repo.list_by_graph(session, "my_graph", limit=10)
```

#### GraphVersionRepo (`store/pg/repos/graph_version_repo.py`)

```python
from store.pg.repos.graph_version_repo import GraphVersionRepo

repo = GraphVersionRepo()

# Get current version
version = repo.get_version(session, "my_graph")  # 0 if none

# Bump version (for cache invalidation)
new_version = repo.bump(session, "my_graph", reason="node added")
```

---

### 5. Event Journal (`store/journal/event_journal.py`)

High-level wrapper with checksum verification.

```python
from store.journal.event_journal import EventJournal

journal = EventJournal(session)

# Append (validates checksum before storing)
event = EventRecord.create("my_graph", "node_created", {"node_id": "abc"})
saved = journal.append(event)  # Raises ChecksumMismatchError if invalid

# Read
events = journal.read("my_graph", after_seq=0, limit=100)
latest = journal.get_latest("my_graph")

# Verify all checksums
is_valid = journal.verify_integrity("my_graph")
```

---

## Database Schema

```sql
-- Blob references
CREATE TABLE raw_refs (
    id UUID PRIMARY KEY,
    sha256 VARCHAR(64) NOT NULL UNIQUE,
    uri TEXT NOT NULL,
    mime_type VARCHAR(128),
    size_bytes BIGINT NOT NULL,
    graph_id VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL
);

-- Append-only events
CREATE TABLE events (
    seq BIGSERIAL PRIMARY KEY,
    id UUID NOT NULL UNIQUE,
    ts TIMESTAMPTZ NOT NULL,
    graph_id VARCHAR(64) NOT NULL,
    kind VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

-- Graph snapshots
CREATE TABLE snapshots (
    id UUID PRIMARY KEY,
    graph_id VARCHAR(64) NOT NULL,
    graph_version BIGINT NOT NULL,
    graph_hash VARCHAR(64) NOT NULL,
    node_count INTEGER NOT NULL,
    extra_meta JSONB,
    created_at TIMESTAMPTZ NOT NULL
);

-- Version tracking
CREATE TABLE graph_version (
    graph_id VARCHAR(64) PRIMARY KEY,
    version BIGINT NOT NULL,
    reason TEXT,
    updated_at TIMESTAMPTZ NOT NULL
);
```

---

## Demo Scripts

```bash
# Ingest a file
python scripts/raw_ingest.py /path/to/file.txt --graph-id my_graph

# Verify blob integrity
python scripts/raw_verify.py abc123def456...

# Append and read events
python scripts/event_append_demo.py --graph-id my_graph

# Create snapshot
python scripts/snapshot_create_demo.py --graph-id my_graph
```

---

## Running Tests

```bash
cd /home/sephi-asi/FAIM/faim/Faim_Native
./scripts/verify.sh
```

Or manually:

```bash
PYTHONPATH="$(pwd)" python3 -m pytest tests/ -v -c pytest.ini
```
