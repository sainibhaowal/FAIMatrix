# FAIM-Native Core Layer Guide

Stage-4: Core Physics, FIG Graph, and Replay.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     FIG Graph (PostgreSQL)                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                │
│  │  nodes   │───▶│  edges   │───▶│  events  │                │
│  └──────────┘    └──────────┘    └──────────┘                │
└──────────────────────────────────────────────────────────────┘
                           │
            ▼──────────────┴──────────────▼
     ┌─────────────┐              ┌─────────────┐
     │ Inheritance │              │  Antisym    │
     │  Σf = 1     │              │ lower wins  │
     └─────────────┘              └─────────────┘
```

## Core Engine

```python
from core.engine_native import FAIMNativeEngine

engine = FAIMNativeEngine(
    node_repo=node_repo,
    edge_repo=edge_repo,
    event_repo=event_repo,
    graph_version_repo=graph_version_repo,
    parent_top_k=8,
    antisym_threshold=0.95,
)

# Write atoms to graph
result = engine.write_atoms(graph_id, vectors)
print(f"Nodes: {result.nodes_written}")
print(f"Edges: {result.edges_written}")
print(f"Merges: {result.merges}")
print(f"Version: {result.graph_version}")
```

## Operators

### Inheritance (Σfractions = 1)

```python
from core.operators.inheritance import compute_inheritance_plan

plan = compute_inheritance_plan(child_vector, candidates, k=8)
# plan.parents      - List of parent node IDs
# plan.fractions    - Weights (Σ=1 exactly)
# plan.residual     - Novelty proxy (0-1)
```

### Antisymmetric Merge

```python
from core.antisym import opposition_score, should_merge, merge_vectors

score = opposition_score(v1, v2)  # 0-1
if should_merge(score, threshold=0.95):
    result = merge_vectors(a_id, b_id, a_hash, b_hash, score)
    # result.winner_id  - Lower hash wins (deterministic)
    # result.loser_id   - Node to merge/cancel
```

### Prune Policy

```python
from core.operators.prune import PrunePolicy, can_prune

policy = PrunePolicy(
    min_age_days=7,
    max_touch_count=0,
    min_similarity_for_redundancy=0.98,
    protect_macros=True,
)

if can_prune(node, max_similarity, policy):
    # Safe to delete: old + low usage + redundant
```

## Invariants

```python
from core.invariants import check_inheritance_sum, check_boundedness

# Verify Σfractions = 1
result = check_inheritance_sum(edge_repo, node_repo, graph_id)
assert result.passed

# Verify no NaN/Inf, residual in [0,1]
result = check_boundedness(node_repo, graph_id)
assert result.passed
```

## Graph Hash

```python
# Deterministic hash of graph state
graph_hash = engine.compute_graph_hash(graph_id)
# SHA256 of sorted nodes + edges
```

## Events Emitted

| Event                | When                 |
| -------------------- | -------------------- |
| `NODE_UPSERT`        | Node created/updated |
| `INHERITANCE_SET`    | Parents assigned     |
| `MERGE`              | Antisym merge        |
| `GRAPH_VERSION_BUMP` | After write batch    |

## FAIM-Native Rules

| Rule           | Implementation                |
| -------------- | ----------------------------- |
| No ML models   | Cosine similarity only        |
| No randomness  | Lower vector_hash wins        |
| Σfractions = 1 | Renormalize + stable rounding |
| Events emitted | Every mutation → journal      |
| Deterministic  | Stable ordering everywhere    |
