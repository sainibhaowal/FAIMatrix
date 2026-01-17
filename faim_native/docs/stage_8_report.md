# Stage-8 Report: FAIM-Native Query Engine

## ✅ Test Results

```
======================= 372 passed, 2 warnings in 1.59s ========================
✓ All tests passed!
```

---

## What You Get

After Stage-8, FAIM is a **real multi-user memory brain**:

User asks: _"what did I store about X?"_

FAIM returns:

- ✅ Best memory nodes with **physics-based scores** (not just cosine)
- ✅ **Why** it chose them (score_components: sim, novel, opp, red, rec, use, lvl)
- ✅ **Where** they came from (raw_id + anchor)
- ✅ **Live animation** via SSE: QUERY_START → RERANK → TOUCH → COMPLETE

---

## FAIM Score Formula

```
score = w_sim * cosine(q, n.v_native)
      + w_novel * clamp(n.residual)
      - w_opp * opposition_penalty
      - w_red * redundancy_penalty
      + w_rec * recency_boost
      + w_use * log1p(touch_count)
      - w_lvl * level_penalty
```

---

## New Files

| File                          | Purpose                                     |
| ----------------------------- | ------------------------------------------- |
| `core/query/query_engine.py`  | QueryPlan, scorer, recall, re-rank, explain |
| `core/query/__init__.py`      | Module exports                              |
| `orchestration/query_flow.py` | run_query() with events                     |

## Modified Files

| File                   | Changes                                     |
| ---------------------- | ------------------------------------------- |
| `api/routers/query.py` | Stage-8 contract (QueryResultItem, metrics) |
| `api/routers/node.py`  | Enhanced with tenant_id                     |

---

## New Tests (40)

| Test File                           | Tests |
| ----------------------------------- | ----- |
| `test_AT_Q1_query_determinism.py`   | 8     |
| `test_AT_Q2_no_chunking_no_ml.py`   | 6     |
| `test_AT_Q3_tenant_isolation.py`    | 5     |
| `test_AT_Q4_index_fallback.py`      | 4     |
| `test_AT_Q5_explain_correctness.py` | 5     |
| `test_AT_Q6_events_emitted.py`      | 7     |
| `test_AT_Q7_query_flow.py`          | 5     |

---

## Query Example

```bash
curl -X POST http://localhost:8000/v1/query \
  -H "X-Tenant-Id: demo" \
  -H "X-Api-Key: test" \
  -H "Content-Type: application/json" \
  -d '{
    "graph_id": "g1",
    "query_text": "what did I say about pruning?",
    "k": 10,
    "profile": "STRICT",
    "return_explain": true
  }'
```

Response includes:

- `results[]` with node_id, score, score_components, evidence
- `metrics` with CR, R, D_hat, H_hat, lambda_hat
- `query_hash` for verification
