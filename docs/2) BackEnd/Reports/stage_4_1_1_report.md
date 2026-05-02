# Stage-4.1.1 Report: Metric Contract Unification

## ✅ Test Results

```
======================== 216 passed, 1 warning in 0.87s ========================
```

---

## Summary

Stage-4.1.1 establishes a **unified metric contract** for FAIM-Native:

- `metrics_defs.py` is now **contract-only** (no numpy, no computation)
- All metric computation is centralized in `fractal_physics.py`
- UI/API uses `MetricsSnapshot` as the canonical format

---

## Deliverables

### A) `metrics_defs.py` Rewritten ✅

| Before                | After                |
| --------------------- | -------------------- |
| 461 lines             | 260 lines            |
| numpy import          | NO numpy             |
| 15+ compute functions | 0 compute functions  |
| Legacy types          | Clean contract types |

### B) MetricKey Constants ✅

```python
class MetricKey:
    CR = "CR"                    # Compression ratio
    R = "R"                      # Redundancy
    D_HAT = "D_hat"              # Fractal dimension
    H_HAT = "H_hat"              # Entropy
    LAMBDA_HAT = "lambda_hat"    # Evolution pressure
    NOVELTY = "novelty"          # Novelty measure
    ENERGY = "energy"            # Energy/boundedness
```

### C) METRIC_KEYS_ORDERED ✅

```python
METRIC_KEYS_ORDERED = ["CR", "D_hat", "energy", "H_hat", "lambda_hat", "novelty", "R"]
```

Stable ordering for deterministic hashing.

### D) MetricsSnapshot Dataclass ✅

```python
@dataclass(frozen=True)
class MetricsSnapshot:
    graph_id: str
    graph_version: int
    graph_hash: str
    metrics: Dict[str, float]  # Uses METRIC_KEYS_ORDERED
    diagnostics_hash: str
    created_at: Optional[datetime] = None  # NEVER used in hashes
```

### E) validate_metric_payload() ✅

```python
def validate_metric_payload(payload: Dict[str, Any]) -> List[str]:
    """Returns empty list if valid, otherwise error messages."""
```

Checks:

- Required fields present
- Metric values are numeric
- Values in valid ranges

### F) FractalDiagnostics.to_metrics_snapshot() ✅

```python
def to_metrics_snapshot(self, graph_hash: str) -> MetricsSnapshot:
    """Convert to MetricsSnapshot for UI/API contract."""
```

---

## UI Wiring Rule

| Source                         | Format                               |
| ------------------------------ | ------------------------------------ |
| Event: `DIAGNOSTICS_SNAPSHOT`  | `MetricsSnapshot.to_event_payload()` |
| Endpoint: `/metrics/scorecard` | `MetricsSnapshot.to_dict()`          |

Both return the same canonical format.

---

## Files Changed

| File                                             | Change                          |
| ------------------------------------------------ | ------------------------------- |
| `core/metrics/metrics_defs.py`                   | REWRITTEN (no numpy)            |
| `core/metrics/fractal_physics.py`                | +40 lines (to_metrics_snapshot) |
| `tests/unit/test_metric_contract_unification.py` | NEW (15 tests)                  |

---

## Test Summary

| Category               | Tests   |
| ---------------------- | ------- |
| Existing (Stage 1-4.1) | 201     |
| New (Stage-4.1.1)      | 15      |
| **Total**              | **216** |

### New Tests

| Test Class                        | Tests |
| --------------------------------- | ----- |
| TestMetricContractNoNumpy         | 2     |
| TestMetricKeysOrdered             | 3     |
| TestMetricsSnapshotSchema         | 3     |
| TestFractalDiagnosticsConformance | 3     |
| TestValidateMetricPayload         | 3     |
| TestNoDuplicateComputation        | 1     |

---

## Usage Examples

### Create MetricsSnapshot from Diagnostics

```python
from core.metrics.fractal_physics import compute_diagnostics

diag = compute_diagnostics(graph_id, vectors, residuals, edge_count, version)
snapshot = diag.to_metrics_snapshot(graph_hash="abc123")

print(snapshot.metrics)
# {'CR': 0.5, 'D_hat': 2.5, 'energy': 0.6, 'H_hat': 0.7, ...}
```

### Validate API Payload

```python
from core.metrics.metrics_defs import validate_metric_payload

errors = validate_metric_payload(request.json)
if errors:
    return {"errors": errors}, 400
```

### Access Individual Metrics

```python
from core.metrics.metrics_defs import MetricKey

d_hat = snapshot.metrics[MetricKey.D_HAT]
lambda_hat = snapshot.metrics[MetricKey.LAMBDA_HAT]
```

---

## Contract Compliance

| Rule                                  | Status |
| ------------------------------------- | ------ |
| No numpy in metrics_defs.py           | ✅     |
| No computation in metrics_defs.py     | ✅     |
| All computation in fractal_physics.py | ✅     |
| MetricsSnapshot for UI/API            | ✅     |
| METRIC_KEYS_ORDERED stable            | ✅     |
| created_at excluded from hashes       | ✅     |
