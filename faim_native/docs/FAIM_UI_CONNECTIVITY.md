# FAIM-Native UI: Connectivity Guide

This guide provides the exact "wire" connections needed to bridge your premium Frontend UI with the FAIM-Native Backend.

---

## 1. THE PERCEPTION LAYER (Ingest)
**Component**: `IngestStation.tsx`

### Action: File Upload
- **Endpoint**: `POST /v1/ingest/upload`
- **Method**: Multipart Form Data
- **Payload**:
  - `file`: The binary file (PDF, TXT, DOCX, etc.)
  - `graph_id`: The target graph identifier
  - `profile`: `"strict"` (Recommended)
- **Response**: `200 OK` with `packet_hash` and `graph_version`.

---

## 2. THE CORE ENGINE (Visualizer)
**Component**: `NeuralBrain.tsx` (Cytoscape or React Flow)

### Action: Graph Discovery
- **Endpoint**: `GET /v1/node` (with filters)
- **Method**: GET
- **Headers**: `X-Graph-Id: my_graph_001`
- **Data Model**: Returns an array of Nodes and Edges. Apply **Bio-Purple** glow to nodes with high `influence`.

---

## 3. THE RECALL LAYER (Knowledge Search)
**Component**: `RecallConsole.tsx`

### Action: Semantic Search
- **Endpoint**: `POST /v1/query`
- **Payload**:
  ```json
  {
    "query": "What are the user's project preferences?",
    "k": 5,
    "profile": "strict"
  }
  ```
- **Response**: Sorted list of memories with `score` and `reasoning_path`.

---

## 4. THE EVOLUTION LAYER (Live Heartbeat)
**Component**: `EvolutionLab.tsx`

### Action: SSE Live Feed
- **Endpoint**: `GET /v1/events/stream`
- **Implementation**:
  ```javascript
  const eventSource = new EventSource("/v1/events/stream?graph_id=...");
  eventSource.addEventListener("NODE_MERGED", (e) => {
    const data = JSON.parse(e.data);
    // Trigger 'Merge Animation' in Graph UI
  });
  ```

---

## 5. THE SECURITY SHIELD (Multi-Tenancy)
**Requirement**: Every request MUST include the headers provided by your Auth system.

```javascript
headers: {
  "X-Tenant-Id": "your_tenant_id",
  "X-Api-Key": "faim_..."
}
```

---

## 🚀 SUMMARY
By following this guide, you connect the **Visual Beauty** of the UI to the **Mathematical Rigor** of the backend. The UI becomes a window into the machine's "Thinking" process.
