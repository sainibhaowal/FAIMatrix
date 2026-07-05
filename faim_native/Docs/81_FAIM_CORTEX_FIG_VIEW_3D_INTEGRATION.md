# 81. FAIM Cortex & FIG View 3D Integration Spec

This document provides a highly detailed, comprehensive analysis of the unified cognitive architecture that connects **FAIM Cortex (the reasoning brain)** and the **3D FIG View Canvas (the sensory-visual representation space)**. It defines the structural topology, real-time pulse tracing, synchronous and asynchronous lifecycle pipelines, concrete usage patterns, and system verification protocols.

---

## 1. Architectural Topology: The Unified Cognitive Loop

The integration between Cortex and FIG View establishes a closed-loop system where cognitive processing dynamically drives visual feedback, and graph state changes in turn guide subsequent AI reasoning pathways.

```mermaid
sequenceDiagram
    autonumber
    actor User as User Chat Interface
    participant FE as ChatContext / Next.js
    participant API as FastAPI Router (/cortex/turn)
    participant CE as Cortex Engine (runtime.py)
    participant QE as Query Engine (query_engine.py)
    participant DB as Postgres/SQLite DB
    participant Canvas as 3D FigCanvas (Three.js)

    User->>FE: Submits query ("What is the current release date?")
    FE->>API: POST /api/v1/cortex/turn (query_text, answer_mode; Cortex thinking is backend-default)
    API->>CE: run_cortex_turn(...)
    CE->>QE: run_query(...) with IWQE + Deterministic Rerank
    QE->>DB: Fetch nodes/edges (optimized indexes)
    DB-->>QE: Return vector matches + inheritance/opposition paths
    QE->>QE: Evaluate 2-hop temporal contradictions (TCT)
    QE-->>CE: Structured QueryResult (with temporal_status & lineage)
    CE->>CE: Run enhanced planner + parallel reasoning branches (Reduce State)
    CE->>DB: Commit transaction / Save turn history
    CE-->>API: CortexTurnResponse (brain_state, narrative, evidence_nodes)
    API-->>FE: HTTP 200 (CortexTurnResponse JSON)
    FE->>FE: Call setActiveReasoningPath(...) with evidence node & reasoning IDs
    FE->>Canvas: Set activeNodeIdSet & activeEdgeIdSet
    Canvas->>Canvas: Dynamic 3D Pulse Effect (Glow & Traverse Path)
    FE-->>User: Renders Answer Card with glowing temporal badges & strike-throughs
```

---

## 2. Sync vs. Async Lifecycle Pipelines

FAIM handles database operations and state synchronization through distinct synchronous and asynchronous processing channels to ensure instant UI responsiveness and background structural optimization.

### 2.1 Synchronous Flow (Real-Time Reasoning Turn)
* **Execution**: Triggered directly by the user's HTTP request.
* **Database Scope**: Limited to reading nodes/edges and writing a single `cortex_turns` record + `cortex_reasoning_nodes` to the persistence ledger.
* **Latency Target**: $< 400\text{ms}$ (excluding LLM synthesis).
* **Isolation**: Clean SQLAlchemy transactional contexts with automatic error rollbacks (`ctx.session.rollback()`) to guarantee system integrity.

### 2.2 Asynchronous Flow (Self-Evolution & State Consolidation)
* **Execution**: Run in the background by autonomous worker schedulers.
* **Database Scope**: Performs heavy relational writes—merging duplicate nodes, updating inheritance edge weights, clearing dead opposition boundaries, and consolidating memory structures.
* **Deduplication**: Monitored via the `ingest_dedup` table, ensuring identical background jobs are never enqueued concurrently.
* **Self-Invention State**: Tracks incremental co-activation counters (`self_invention_state`) to cursor through event streams and harden new concept nodes.

---

## 3. Real-Time "Pulse Path" Tracing Mechanics

When a Cortex turn executes, the 3D graph needs to instantly illustrate the "trail of thought." This is handled by mapping search outcomes and reasoning steps into a set of active visual anchors.

Let:
* $\mathcal{C}$ be the set of active candidate nodes returned from the vector search.
* $\mathcal{R}$ be the set of structured reasoning steps created in the reasoning tree.
* $\mathcal{E}_r$ be the evidence node IDs associated with a specific reasoning step $r \in \mathcal{R}$.

The frontend computes the active visual sets as:

$$\text{ActiveNodes} = \{ n.\text{node\_id} \mid n \in \mathcal{C} \} \cup \{ r.\text{node\_id} \mid r \in \mathcal{R} \}$$

$$\text{ActiveEdges} = \bigcup_{r \in \mathcal{R}} \mathcal{E}_r$$

These sets are stored in active state context within [`ChatContext.tsx`](file:///home/sephi-asi/FAIM/frontend/src/contexts/ChatContext.tsx#L943). The 3D Three.js renderer (`FigCanvas.tsx`) reads these sets on every render tick:
1. **Node Glow**: If a 3D node's ID exists in `ActiveNodes`, its material emissive property is boosted, creating a vibrant halo.
2. **Edge Pulse**: If an edge connects active nodes or is defined in `ActiveEdges`, a particle effect travels along the 3D line vector, showing the directional flow of cognitive association.

---

## 4. End-to-End Concrete Use Case: Temporal Fact Resolution

### 4.1 Scenario
An enterprise software system changes its target release date twice:
1. **Fact A (Historical)**: "Project Sirius will launch on June 1st, 2026."
2. **Fact B (Current)**: "Project Sirius launch rescheduled to July 15th, 2026 due to QA constraints."

### 4.2 Graph Representation in Postgres
In the `nodes` table, we have:
* Node A (`node_id: 3c27e8a9...`): "Launch set to June 1st" (`created_at: 2026-05-01`).
* Node B (`node_id: 8d90f23a...`): "Launch rescheduled to July 15th" (`created_at: 2026-05-15`).

An `opposition` edge connects Node A and Node B because they represent contradictory values for the launch timeline of the same project.

### 4.3 Cortex Turn Execution
When the user asks: *"When is Project Sirius launching?"*
Cortex recalls both Node A and Node B.
1. The Transitive Contradiction Traversal (TCT) engine detects the `opposition` edge.
2. It compares the timestamps:
   $$\text{Node B (May 15th)} > \text{Node A (May 1st)}$$
3. Resolution assigns:
   * Node B $\to$ `temporal_status: "CURRENT"`, `supersedes: ["3c27e8a9..."]`
   * Node A $\to$ `temporal_status: "HISTORICAL"`, `superseded_by: "8d90f23a..."`

### 4.4 API JSON Payload
The endpoint returns:

```json
{
  "turn_id": "9f8e7d6c5b4a3b2a",
  "query_hash": "a1b2c3d4e5f6g7h8",
  "task_type": "contradiction",
  "answer_mode": "contradiction",
  "narrative": "FAIM Cortex isolated the conflicting memory values. Project Sirius is currently scheduled to launch on July 15th, 2026. Prior launch target of June 1st has been superseded.",
  "brain_state": {
    "confidence": 0.95,
    "active_facts": [
      "Project Sirius launch rescheduled to July 15th, 2026 due to QA constraints"
    ],
    "contradictions": [
      "Timeline conflict: launch rescheduled from June 1st to July 15th."
    ],
    "evidence_nodes": [
      {
        "node_id": "8d90f23a-f2b3-4c5d-8e9f-0a1b2c3d4e5f",
        "score": 0.94,
        "temporal_status": "CURRENT",
        "supersedes": ["3c27e8a9-f2b3-4c5d-8e9f-0a1b2c3d4e5f"],
        "superseded_by": null,
        "raw_id": "file_alpha.pdf"
      },
      {
        "node_id": "3c27e8a9-f2b3-4c5d-8e9f-0a1b2c3d4e5f",
        "score": 0.81,
        "temporal_status": "HISTORICAL",
        "supersedes": null,
        "superseded_by": "8d90f23a-f2b3-4c5d-8e9f-0a1b2c3d4e5f",
        "raw_id": "file_beta.pdf"
      }
    ]
  }
}
```

### 4.5 Visual Rendering in the 3D Canvas & UI

```
+-----------------------------------------------------------+
| FAIM CORTEX RESPONSE                                      |
|                                                           |
| "Project Sirius is currently scheduled to launch on       |
|  July 15th, 2026. Prior launch target has been            |
|  superseded."                                             |
|                                                           |
| Memory Anchors:                                           |
| [ File Alpha (94%) ] -> CURRENT                           |
| [ File Beta (81%) ]  -> HISTORICAL (Superseded by Alpha)  |
+-----------------------------------------------------------+
```

* **Node A (June 1st Launch)**: Displays on the 3D graph as a **dimmed out, translucent orange node** with a faint dotted link to Node B.
* **Node B (July 15th Launch)**: Displays as a **highly illuminated, pulsing teal node**, visually signaling it as the active source of current truth.
* **The Hover Tooltip**: Hovering over the File Beta anchor badge in the Chat UI displays the interactive tooltip: `"Superseded by node 8d90f23a..."` pointing exactly to the newer launch fact.

---

## 5. Performance Diagnostics & Optimization

To prevent real-time search lag as graphs scale past 8 million words and semantic links, the integration employs strict optimization boundaries:

| Metric | Target | Optimization Strategy |
| :--- | :--- | :--- |
| **Vector Recall Lookup** | $< 15\text{ms}$ | Flat array vector matching on in-memory arrays and dedicated indexing. |
| **Contradiction Resolution** | $< 8\text{ms}$ | 2-hop index lookups restricted using composite graph indexes (`idx_edges_child` & `idx_edges_parent`). |
| **3D Rendering overhead** | $< 1.5\text{ms}$ per frame | ID sets (`ActiveNodes`, `ActiveEdges`) are instantiated as JavaScript `Set` structures, reducing lookup complexity to $O(1)$ constant time on every frame loop. |
| **Database Transaction Lockout** | $0\text{ms}$ | Turn storage and reasoning traces use non-blocking `INSERT` statements with distinct database sessions to avoid locking active reader pools. |
