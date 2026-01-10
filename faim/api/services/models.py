from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# API PREFIX
# -----------------------------------------------------------------------------
API_PREFIX = "/api/v1"


# =============================================================================
# CHAT MODELS (optional, not used by chat.py which has its own)
# =============================================================================


class ChatRequest(BaseModel):
    graph_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    used_nodes: List[Dict[str, Any]]


# =============================================================================
# BASIC GRAPH / NODE MODELS
# =============================================================================


class ParentInfo(BaseModel):
    id: str
    fraction: float = 1.0


class NodeBase(BaseModel):
    id: str
    label: Optional[str] = ""
    vector: Optional[List[float]] = None
    payload: Optional[str] = None


class NodeDetail(NodeBase):
    # Option B
    parents: Optional[List[ParentInfo]] = None
    fractions: Optional[List[float]] = None
    novelty: Optional[Any] = None
    inherited: Optional[Any] = None

    # Option C (advanced inspector)
    children: Optional[List[str]] = None
    degree: Optional[int] = None
    redundancy_score: Optional[float] = None
    evolution_flags: Optional[List[str]] = None
    parent_distances: Optional[Dict[str, float]] = None
    vector_stats: Optional[Dict[str, float]] = None


class LinkModel(BaseModel):
    source: str
    target: str


class GraphSubgraph(BaseModel):
    """
    Structure returned to the FIG 3D graph:
      { nodes: [...], links: [...] }
    """

    nodes: List[NodeBase] = Field(default_factory=list)
    links: List[LinkModel] = Field(default_factory=list)


class NodeScanItem(BaseModel):
    id: str
    degree: Optional[int] = None


# =============================================================================
# GRAPH METRICS (for dashboard + benchmarks)
# =============================================================================


class GraphMetrics(BaseModel):
    """
    Metrics used by:
      - /graph/{graph_id}/metrics
      - /api/v1/benchmarks/{graph_id}*
    """

    node_count: int = 0
    edge_count: int = 0
    compression_ratio: float = 0.0
    redundancy: float = 0.0
    drift: float = 0.0
    retrieve_p50_ms: float = 0.0
    retrieve_p95_ms: float = 0.0
    raw_bytes: int = 0
    faim_bytes: int = 0


class LatencyPoint(BaseModel):
    retrieve_p50_ms: float = 0.0
    retrieve_p95_ms: float = 0.0


class BenchmarkPoint(BaseModel):
    timestamp: str
    nodes: int
    cr: float
    redundancy: float
    drift: float
    latency: LatencyPoint


# =============================================================================
# VECTOR ANALYTICS
# =============================================================================


class NeighborInfo(BaseModel):
    id: str
    distance: float


class VectorStats(BaseModel):
    norm: float
    mean: float
    std: float
    min: float
    max: float


# =============================================================================
# LINEAGE TRACE
# =============================================================================


class LineageModel(BaseModel):
    lineage: List[str]


# =============================================================================
# INGEST STRUCTURES (if you add upload endpoints later)
# =============================================================================


class IngestFileResult(BaseModel):
    filename: str
    size_bytes: int
    content_type: Optional[str]

    chunks: int
    skipped: bool
    note: Optional[str] = None


class IngestResponse(BaseModel):
    status: str
    graph_id: str
    files: List[IngestFileResult]
    nodes_created: int
    source: str = "engine"
    note: Optional[str] = None


# =============================================================================
# HEALTH + GENERIC RESPONSE
# =============================================================================


class Health(BaseModel):
    status: str = "OK"


class APIResponse(BaseModel):
    status: str = "ok"
    data: Any
