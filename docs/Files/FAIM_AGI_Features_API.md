# FAIM AGI Features API Reference

Complete documentation for all 6 AGI features implemented in FAIM Lab.

---

## 1. Batch Upload with Progress

Upload multiple files with real-time progress tracking via Server-Sent Events.

### Endpoints

#### Upload Files

```
POST /api/v1/batch/upload
```

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/batch/upload \
  -F "files=@document1.pdf" \
  -F "files=@document2.docx" \
  -F "graph_id=MAIN"
```

**Response:**

```json
{
  "batch_id": "abc123def456",
  "total_files": 2,
  "status": "processing",
  "progress_url": "/api/v1/batch/abc123def456/progress"
}
```

#### Progress Stream (SSE)

```
GET /api/v1/batch/{batch_id}/progress
```

**Events:**

- `connected` - Initial connection
- `progress` - Status update
- `complete` - All files done

---

## 2. Cross-document Inference

Find hidden connections between nodes from different documents.

### Endpoints

#### Run Inference

```
POST /api/v1/graphs/{graph_id}/infer
```

**Request:**

```json
{
  "min_similarity": 0.75,
  "max_results": 50,
  "exclude_same_doc": true
}
```

**Response:**

```json
{
  "graph_id": "MAIN",
  "total_nodes": 150,
  "pairs_checked": 11175,
  "inferences_found": 23,
  "inferences": [
    {
      "link_id": "abc123",
      "source": "node_1",
      "target": "node_2",
      "similarity": 0.85,
      "source_doc": "resume.pdf",
      "target_doc": "jobreq.pdf"
    }
  ]
}
```

#### Get Cached Inferences

```
GET /api/v1/graphs/{graph_id}/inferences
```

---

## 3. Semantic Auto-clustering

Automatically group related concepts into clusters.

### Endpoints

#### Run Clustering

```
POST /api/v1/graphs/{graph_id}/cluster
```

**Request:**

```json
{
  "n_clusters": null,
  "min_cluster_size": 3,
  "use_llm_labels": true
}
```

**Response:**

```json
{
  "graph_id": "MAIN",
  "total_nodes": 150,
  "n_clusters": 8,
  "clusters": [
    {
      "cluster_id": "abc123",
      "label": "Machine Learning Concepts",
      "description": "Cluster of ML-related terminology",
      "size": 15,
      "coherence": 0.72
    }
  ]
}
```

#### Get Clusters

```
GET /api/v1/graphs/{graph_id}/clusters
```

---

## 4. Hidden Insights Discovery

Reveal non-obvious patterns and surprising connections.

### Endpoints

#### Discover Insights

```
POST /api/v1/graphs/{graph_id}/discover-insights
```

**Request:**

```json
{
  "max_insights": 20,
  "min_surprise": 0.3,
  "use_llm": true
}
```

**Response:**

```json
{
  "graph_id": "MAIN",
  "insights_found": 12,
  "insights": [
    {
      "insight_id": "abc123",
      "title": "Hidden Link Between Projects",
      "description": "Two seemingly unrelated projects share core methodology",
      "type": "connection",
      "surprise_score": 0.85,
      "related_nodes": ["node_1", "node_2"],
      "evidence": "Similarity: 82%"
    }
  ]
}
```

#### Get Cached Insights

```
GET /api/v1/graphs/{graph_id}/insights
```

---

## 5. Image Understanding

Extract and understand images from documents.

### Endpoints

#### Process Document Images

```
POST /api/v1/images/process
```

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/images/process \
  -F "file=@document.pdf" \
  -F "graph_id=MAIN" \
  -F "use_vision_api=true"
```

**Response:**

```json
{
  "filename": "document.pdf",
  "images_found": 5,
  "images": [
    {
      "image_id": "img_abc123",
      "page": 3,
      "description": "Bar chart showing quarterly revenues",
      "objects": ["chart", "bars", "legend"],
      "has_text": true,
      "node_id": "node_123"
    }
  ]
}
```

#### Get Image Info

```
GET /api/v1/images/{image_id}
```

---

## 6. Self-Inventing Concepts

Automatically synthesize new concepts from existing knowledge.

### Endpoints

#### Run Invention

```
POST /api/v1/graphs/{graph_id}/invent
```

**Request:**

```json
{
  "max_inventions": 5,
  "min_sources": 2,
  "max_sources": 4,
  "create_nodes": true
}
```

**Response:**

```json
{
  "graph_id": "MAIN",
  "inventions_created": 3,
  "inventions": [
    {
      "concept_id": "abc123",
      "title": "Unified Data Pipeline Architecture",
      "description": "A synthesis of ETL and streaming approaches",
      "content": "This new concept combines...",
      "source_nodes": ["node_1", "node_2", "node_3"],
      "confidence": 0.78,
      "node_id": "invented_node_456"
    }
  ]
}
```

#### Get Inventions

```
GET /api/v1/graphs/{graph_id}/inventions
```

---

## Configuration

### Environment Variables

| Variable         | Purpose                                        |
| ---------------- | ---------------------------------------------- |
| `GROQ_API_KEY`   | LLM for clustering labels, insights, invention |
| `OPENAI_API_KEY` | Vision API for image understanding             |

---

## Safety Features

- All modules are NEW files (no existing code modified)
- Routers use try/except for graceful degradation
- Features work without LLM (fallback behavior)
- In-memory storage (production would use Redis)
