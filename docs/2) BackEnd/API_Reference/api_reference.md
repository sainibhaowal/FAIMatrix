# FAIM-Native Store Layer - API Reference

## Core Types (`core/contracts/types.py`)

### uuid7

```python
def uuid7(timestamp_ms: Optional[int] = None) -> UUID:
    """Generate UUID version 7 (time-ordered, random)."""
```

### RawRef

```python
@dataclass(frozen=True, slots=True)
class RawRef:
    id: UUID              # UUID7 identifier
    sha256: Sha256Hex     # SHA256 hex digest
    uri: str              # file://path or s3://bucket/key
    mime_type: str        # MIME type
    size_bytes: int       # Content size
    created_at: datetime
    graph_id: Optional[GraphId]

    @classmethod
    def create(cls, sha256, uri, size_bytes, mime_type="application/octet-stream",
               graph_id=None, created_at=None) -> RawRef
```

### EventRecord

```python
@dataclass(frozen=True, slots=True)
class EventRecord:
    id: UUID              # UUID7 identifier
    seq: Optional[int]    # Auto-assigned by database
    ts: datetime          # Event timestamp
    graph_id: GraphId
    kind: str             # Event type
    payload: Dict[str, Any]
    checksum: str         # SHA256(ts||graph_id||kind||payload)
    created_at: datetime

    @classmethod
    def create(cls, graph_id, kind, payload, ts=None) -> EventRecord

    def verify_checksum(self) -> bool
```

### SnapshotRecord

```python
@dataclass(frozen=True, slots=True)
class SnapshotRecord:
    id: UUID
    graph_id: GraphId
    graph_version: int    # Version at snapshot time
    graph_hash: str       # Integrity receipt
    node_count: int
    created_at: datetime
    metadata: Optional[Dict[str, Any]]

    @classmethod
    def create(cls, graph_id, graph_version, graph_hash, node_count,
               metadata=None, created_at=None) -> SnapshotRecord
```

### GraphVersion

```python
@dataclass(frozen=True, slots=True)
class GraphVersion:
    graph_id: GraphId
    version: int          # Monotonically increasing
    reason: Optional[str]
    updated_at: datetime

    @classmethod
    def initial(cls, graph_id) -> GraphVersion

    def bump(self, reason) -> GraphVersion
```

### Utility Functions

```python
def compute_sha256(data: bytes) -> Sha256Hex
def compute_graph_hash(node_hashes: list[str]) -> str
```

---

## RawStore (`store/raw/raw_store.py`)

```python
class RawStore:
    STORE_VERSION = "v1"

    def __init__(self, base_path: str | Path)

    def store(self, content: bytes, mime_type="application/octet-stream",
              graph_id=None) -> RawRef

    def load(self, raw_ref: RawRef, verify=True) -> bytes

    def load_by_sha(self, sha256: str, verify=True) -> bytes

    def exists(self, raw_ref: RawRef) -> bool

    def exists_by_sha(self, sha256: str) -> bool

    def verify(self, raw_ref: RawRef) -> bool

    def get_stats(self) -> dict
```

---

## SessionFactory (`store/pg/session.py`)

```python
class SessionFactory:
    def __init__(self, url=None, engine=None, echo=False)

    def session(self) -> Generator[Session, None, None]
        """Context manager, no auto-commit."""

    def atomic(self) -> Generator[Session, None, None]
        """Context manager with auto-commit/rollback."""

    def create(self) -> Session
        """Raw session, caller handles cleanup."""

def get_engine(url=None, echo=False, pool_size=5, max_overflow=10) -> Engine

def atomic(session: Session) -> Generator[Session, None, None]
    """Transaction helper for existing session."""
```

---

## Repositories

### RawRepo (`store/pg/repos/raw_repo.py`)

```python
class RawRepo:
    def create(session, raw_ref: RawRef) -> RawRef
    def get_by_id(session, id: UUID) -> Optional[RawRef]
    def get_by_sha(session, sha256: str) -> Optional[RawRef]
    def list_all(session, graph_id=None, limit=100, offset=0) -> List[RawRef]
    def count(session, graph_id=None) -> int
    def exists(session, sha256: str) -> bool
```

### EventRepo (`store/pg/repos/event_repo.py`)

```python
class EventRepo:
    def append(session, event: EventRecord) -> EventRecord
    def get_by_id(session, id: UUID) -> Optional[EventRecord]
    def get_by_seq(session, graph_id, after_seq=0, limit=100) -> List[EventRecord]
    def get_latest(session, graph_id) -> Optional[EventRecord]
    def get_all(session, graph_id, kind=None, limit=1000) -> List[EventRecord]
    def count(session, graph_id) -> int
    def get_max_seq(session, graph_id) -> int
```

### SnapshotRepo (`store/pg/repos/snapshot_repo.py`)

```python
class SnapshotRepo:
    def create(session, snapshot: SnapshotRecord) -> SnapshotRecord
    def get_by_id(session, id: UUID) -> Optional[SnapshotRecord]
    def get_latest(session, graph_id) -> Optional[SnapshotRecord]
    def list_by_graph(session, graph_id, limit=100, offset=0) -> List[SnapshotRecord]
    def list_by_version_range(session, graph_id, min_v, max_v) -> List[SnapshotRecord]
    def count(session, graph_id) -> int
    def get_by_version(session, graph_id, version) -> Optional[SnapshotRecord]
```

### GraphVersionRepo (`store/pg/repos/graph_version_repo.py`)

```python
class GraphVersionRepo:
    def get_version(session, graph_id) -> int
    def get(session, graph_id) -> Optional[GraphVersion]
    def bump(session, graph_id, reason) -> int
    def set_version(session, graph_id, version, reason) -> None
```

---

## EventJournal (`store/journal/event_journal.py`)

```python
class EventJournal:
    def __init__(self, session: Session)

    def append(self, event: EventRecord) -> EventRecord
        """Append event, validates checksum first."""

    def read(self, graph_id, after_seq=0, limit=100) -> List[EventRecord]

    def get_latest(self, graph_id) -> Optional[EventRecord]

    def get_all(self, graph_id, kind=None, limit=1000) -> List[EventRecord]

    def count(self, graph_id) -> int

    def verify_integrity(self, graph_id) -> bool

class EventJournalError(Exception): ...
class ChecksumMismatchError(EventJournalError): ...
```

---

## Exceptions

| Exception               | Module        | Description        |
| ----------------------- | ------------- | ------------------ |
| `RawStoreError`         | raw_store     | Base store error   |
| `BlobNotFoundError`     | raw_store     | Blob doesn't exist |
| `BlobVerificationError` | raw_store     | Hash mismatch      |
| `EventJournalError`     | event_journal | Base journal error |
| `ChecksumMismatchError` | event_journal | Invalid checksum   |

---

## Stage-5: Orchestration Types

### IngestResult (`orchestration/ingest_flow.py`)

```python
@dataclass(frozen=True)
class IngestResult:
    status: str                    # "completed" or "error"
    packet_hash: str               # Idempotency key
    graph_version: int             # Version after write
    nodes_written: int
    merges: int
    block_count: int
    vector_count: int
    diagnostics_hash: Optional[str]
    events_emitted: List[str]
    latency_ms: int
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]
```

### EvolveResult (`orchestration/evolve_flow.py`)

```python
@dataclass(frozen=True)
class EvolveResult:
    status: str                    # "completed" or "error"
    graph_version: int
    merges: int
    prunes: int
    diagnostics: Optional[Dict]    # MetricsSnapshot.to_dict()
    events_emitted: List[str]
    latency_ms: int
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]
```

### run_ingest

```python
def run_ingest(
    graph_id: str,
    raw_id: str,
    filename: str,
    file_bytes: bytes,
    *,
    persist_mode: PersistMode = PersistMode.RELAXED,
    profile: FAIMProfile = FAIMProfile.STRICT,
    node_repo=None, edge_repo=None, event_repo=None, gv_repo=None,
) -> IngestResult
```

### run_evolve

```python
def run_evolve(
    graph_id: str,
    *,
    profile: FAIMProfile = FAIMProfile.STRICT,
    persist_mode: PersistMode = PersistMode.RELAXED,
    node_repo=None, edge_repo=None, event_repo=None, gv_repo=None,
) -> EvolveResult
```

---

## Stage-4.1.1: Metric Contract Types

### MetricsSnapshot (`core/metrics/metrics_defs.py`)

```python
@dataclass(frozen=True)
class MetricsSnapshot:
    graph_id: str
    graph_version: int
    graph_hash: str
    metrics: Dict[str, float]      # Uses METRIC_KEYS_ORDERED
    diagnostics_hash: str
    created_at: Optional[datetime] = None  # NEVER in hashes

    def to_dict(self) -> Dict[str, Any]
    def to_canonical_dict(self) -> Dict[str, Any]  # Excludes created_at
    def to_event_payload(self) -> Dict[str, Any]
```

### MetricKey

```python
class MetricKey:
    CR = "CR"              # Compression ratio
    R = "R"                # Redundancy
    D_HAT = "D_hat"        # Fractal dimension
    H_HAT = "H_hat"        # Entropy
    LAMBDA_HAT = "lambda_hat"  # Evolution pressure
    NOVELTY = "novelty"
    ENERGY = "energy"

METRIC_KEYS_ORDERED = ["CR", "D_hat", "energy", "H_hat", "lambda_hat", "novelty", "R"]
```

### validate_metric_payload

```python
def validate_metric_payload(payload: Dict[str, Any]) -> List[str]:
    """Returns empty list if valid, otherwise error messages."""
```
