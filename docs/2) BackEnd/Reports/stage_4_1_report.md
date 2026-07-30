# Stage-4.1 Report: Fractal Physics (s + D/H/λ + Diagnostics)

## ✅ Test Results

```
============= 201 passed, 1 warning in 0.91s =============
✓ All tests passed!
```

---

## Summary

Stage-4.1 adds **fractal physics** to FAIM-Native with explicit diagnostics for:

- **s**: Scaling factor (1/PHI ≈ 0.618)
- **D**: Fractal dimension estimate
- **H**: Entropy/disorder measure
- **λ**: Evolution pressure

**Result: 201 tests pass** (172 existing + 29 new)

---

## Formulas

### Constants

```python
PHI = (1 + √5) / 2  # Golden ratio ≈ 1.618
GOLDEN_S = 1 / PHI  # Scaling factor ≈ 0.618
```

### D: Fractal Dimension (Correlation Dimension)

```
D = slope of log(C(ε)) vs log(ε)

where C(ε) = (# pairs with distance ≤ ε) / (total pairs)
      distance = 1 - cosine_similarity
```

### H: Entropy (Shannon)

```
H = -Σ p_i * log(p_i) / log(bins)

where p_i = histogram bin probabilities over similarities in [-1, 1]
      H ∈ [0, 1], higher = more disorder
```

### λ: Evolution Pressure

```
λ = 0.50 * N + 0.30 * (1 - R) + 0.20 * H

where N = novelty = mean(residuals)
      R = redundancy = fraction of pairs with sim > 0.9
      λ ∈ [0, 1], higher = more pressure to evolve
```

### E: Energy (Boundedness)

```
E = mean(||v||) * s

where ||v|| = L2 norm of vectors
      E should stay bounded for stability
```

---

## Deliverables Checklist

### A) `core/metrics/fractal_physics.py` ✅

| Component                                | Status | Implementation                     |
| ---------------------------------------- | ------ | ---------------------------------- |
| `FractalConfig` dataclass                | ✅     | s_default, epsilons, bins, weights |
| `FractalDiagnostics` dataclass           | ✅     | All D/H/λ/R/N/E fields             |
| `compute_scaling_s(config)`              | ✅     | Returns GOLDEN_S = 1/PHI           |
| `estimate_D_fractal(vectors, epsilons)`  | ✅     | Correlation dimension              |
| `estimate_H_entropy(similarities, bins)` | ✅     | Shannon entropy                    |
| `estimate_lambda(N, R, H)`               | ✅     | λ = 0.5N + 0.3(1-R) + 0.2H         |
| `compute_redundancy_R()`                 | ✅     | Fraction pairs sim > 0.9           |
| `compute_novelty_N()`                    | ✅     | Mean of residuals                  |
| `compute_diagnostics_hash()`             | ✅     | SHA256 canonical JSON              |
| `to_canonical_dict()`                    | ✅     | Stable ordering                    |

### B) `core/invariants.py` ✅

| Invariant                    | Status            |
| ---------------------------- | ----------------- |
| `check_scaling_bounds(s)`    | ✅ 0 < s ≤ 1      |
| `check_D_range(D_hat)`       | ✅ 0 ≤ D ≤ 10     |
| `check_H_range(H_hat)`       | ✅ 0 ≤ H ≤ 1      |
| `check_lambda_range(λ)`      | ✅ 0 ≤ λ ≤ 1      |
| `check_energy_bounded(E)`    | ✅ E ≤ bound      |
| `check_no_orphan_edges()`    | ✅ All refs valid |
| `check_fractal_invariants()` | ✅ Combined check |

### C) `evolution_native.py` ✅

| Feature                      | Status                           |
| ---------------------------- | -------------------------------- |
| Compute D/H/λ at start       | ✅ `compute_graph_diagnostics()` |
| Emit DIAGNOSTICS_SNAPSHOT    | ✅ With full payload             |
| Adapt merge_threshold from R | ✅ `adapt_merge_threshold()`     |
| Adapt prune_policy from N    | ✅ `adapt_prune_policy()`        |
| D/H/λ in EVOLUTION_COMPLETE  | ✅ diagnostics_hash included     |

### D) `invention_native.py` ✅

| Feature                  | Status                              |
| ------------------------ | ----------------------------------- |
| λ threshold check        | ✅ `LAMBDA_THRESHOLD = 0.3`         |
| Coactivation count       | ✅ `MIN_COACTIVATION_COUNT = 3`     |
| Redundancy reduction     | ✅ `compute_redundancy_reduction()` |
| `should_invent()`        | ✅ All 3 conditions                 |
| level = max(parents) + 1 | ✅ Proper hierarchy                 |
| INVENT_MACRO_NODE event  | ✅ With λ_hat                       |

### E) Legacy Files Moved ✅

```
core/legacy/
├── __init__.py          (deprecation notice)
├── engine_legacy.py     (was engine.py)
├── evolution_legacy.py  (was dynamics/evolution.py)
└── invention_legacy.py  (was dynamics/invention.py)
```

### F) Re-export `engine.py` ✅

```python
from .engine_native import FAIMNativeEngine, WriteResult
__all__ = ["FAIMNativeEngine", "WriteResult"]
```

### G) Demo Scripts ✅

| Script                     | Purpose                        |
| -------------------------- | ------------------------------ |
| `faim_write_demo.py`       | raw → extract → encode → write |
| `faim_diagnostics_demo.py` | Display D/H/λ/R/N/E            |

### H) Tests ✅

| File                                  | Tests |
| ------------------------------------- | ----- |
| `test_fractal_physics_determinism.py` | 25    |
| `test_AT_C5_diagnostics_events.py`    | 4     |

---

## Event Payloads for UI

### DIAGNOSTICS_SNAPSHOT

```json
{
  "graph_id": "...",
  "region_id": "global",
  "node_count": 100,
  "edge_count": 250,
  "s": 0.618034,
  "D_hat": 2.5,
  "H_hat": 0.7,
  "lambda_hat": 0.65,
  "redundancy_R": 0.15,
  "novelty_N": 0.3,
  "energy_E": 0.5,
  "graph_version": 42,
  "diagnostics_hash": "abc123..."
}
```

### EVOLUTION_COMPLETE

```json
{
  "version": 43,
  "merges": 5,
  "prunes": 2,
  "D_hat": 2.5,
  "H_hat": 0.7,
  "lambda_hat": 0.65,
  "diagnostics_hash": "abc123..."
}
```

### INVENT_MACRO_NODE

```json
{
  "macro_id": "uuid...",
  "member_ids": ["uuid1", "uuid2"],
  "level": 2,
  "lambda_hat": 0.58,
  "redundancy_reduction": 0.35,
  "coactivation_count": 5
}
```

---

## Files Created/Modified

### NEW Files

| File                                                | Lines | Description           |
| --------------------------------------------------- | ----- | --------------------- |
| `core/metrics/fractal_physics.py`                   | 575   | PHI, D/H/λ estimators |
| `core/engine.py`                                    | 15    | Re-export             |
| `core/legacy/__init__.py`                           | 11    | Deprecation notice    |
| `scripts/faim_write_demo.py`                        | 175   | Pipeline demo         |
| `scripts/faim_diagnostics_demo.py`                  | 175   | Metrics display       |
| `tests/unit/test_fractal_physics_determinism.py`    | 310   | 25 tests              |
| `tests/acceptance/test_AT_C5_diagnostics_events.py` | 220   | 4 tests               |

### MODIFIED Files

| File                                | Changes                  |
| ----------------------------------- | ------------------------ |
| `core/invariants.py`                | +200 lines (7 checks)    |
| `core/dynamics/evolution_native.py` | +110 lines (diagnostics) |
| `core/dynamics/invention_native.py` | +150 lines (λ trigger)   |
| `core/operators/prune.py`           | +4 lines (datetime fix)  |

### MOVED Files

| From                         | To                                |
| ---------------------------- | --------------------------------- |
| `core/engine.py`             | `core/legacy/engine_legacy.py`    |
| `core/dynamics/evolution.py` | `core/legacy/evolution_legacy.py` |
| `core/dynamics/invention.py` | `core/legacy/invention_legacy.py` |

---

## Test Summary by Stage

| Stage     | Category         | Tests   |
| --------- | ---------------- | ------- |
| 1         | Store Layer      | 32      |
| 2         | Perception Layer | 41      |
| 3         | Encoding Layer   | 49      |
| 4         | Core Physics     | 50      |
| 4.1       | Fractal Physics  | 29      |
| **Total** |                  | **201** |

---

## Usage Examples

### Compute Diagnostics

```python
from core.metrics.fractal_physics import compute_diagnostics

diag = compute_diagnostics(
    graph_id="my_graph",
    vectors=vectors,
    residuals=residuals,
    edge_count=len(edges),
    graph_version=42,
)
print(f"D={diag.D_hat}, H={diag.H_hat}, λ={diag.lambda_hat}")
```

### Check Invariants

```python
from core.invariants import check_fractal_invariants

result = check_fractal_invariants(s=0.618, D_hat=2.5, H_hat=0.7, lambda_hat=0.6, energy_E=0.5)
assert result.passed
```

### Evolution with Diagnostics

```python
from core.dynamics.evolution_native import evolve_once

result = evolve_once(graph_id, node_repo, edge_repo, event_repo, gv_repo)
print(f"Diagnostics: {result.diagnostics.D_hat}")
# Automatically emits DIAGNOSTICS_SNAPSHOT event
```

### λ-Triggered Invention

```python
from core.dynamics.invention_native import should_invent, invent_macro

if should_invent(lambda_hat=0.5, coactivation_count=5, redundancy_reduction=0.3):
    macro_id = invent_macro(graph_id, member_ids, node_repo, edge_repo, event_repo)
```

---

## Run Commands

```bash
# Full test suite
cd /home/sephi-asi/FAIM/faim/Faim_Native
./scripts/verify.sh

# Write demo
python scripts/faim_write_demo.py

# Diagnostics demo
python scripts/faim_diagnostics_demo.py
```

---

## FAIM-Native Rules Compliance

| Rule                 | Status                |
| -------------------- | --------------------- |
| No ML models         | ✅ Pure cosine + math |
| No numpy             | ✅ stdlib only        |
| No randomness        | ✅ Deterministic      |
| Postgres is truth    | ✅ Events + DB        |
| Inheritance Σf=1     | ✅ Checked            |
| Boundedness          | ✅ Checked            |
| Events for mutations | ✅ All covered        |
