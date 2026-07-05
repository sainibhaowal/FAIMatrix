"""Dedicated domain intelligence API for FAIM."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context  # noqa: E402
from domain.intelligence import (  # noqa: E402
    build_domain_graph,
    build_domain_overview,
    list_domain_terms,
)


router = APIRouter(prefix="/domain", tags=["domain"])


class DomainSourceKindCount(BaseModel):
    source_kind: str
    count: int


class DomainKindCount(BaseModel):
    kind: str
    count: int


class DomainPackStrength(BaseModel):
    domain_pack: str
    term_count: int
    support_total: int
    avg_score: float


class DomainTopTerm(BaseModel):
    surface_form: str
    canonical_form: str
    kind: str
    domain_pack: Optional[str] = None
    support_count: int
    score: float
    has_node: bool
    node_id: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
    updated_at: Optional[str] = None


class DomainTopSource(BaseModel):
    source_id: str
    source_kind: str
    source_hash: str
    meta: Dict[str, Any] = Field(default_factory=dict)
    updated_at: Optional[str] = None


class DomainOverviewResponse(BaseModel):
    graph_id: str
    graph_version: int
    jobs_enabled: bool
    domain_autonomy_enabled: bool
    lexicon_total: int
    source_total: int
    linked_total: int
    maturity_score: int
    detected_packs: List[str]
    kind_breakdown: List[DomainKindCount]
    pack_strengths: List[DomainPackStrength]
    source_kinds: List[DomainSourceKindCount]
    top_terms: List[DomainTopTerm]
    top_sources: List[DomainTopSource]
    last_updated_at: Optional[str] = None


class DomainTermsResponse(BaseModel):
    graph_id: str
    total: int
    limit: int
    offset: int
    items: List[DomainTopTerm]


class DomainGraphNode(BaseModel):
    id: str
    label: str
    type: str
    pack: Optional[str] = None
    kind: Optional[str] = None
    score: Optional[float] = None
    support_count: Optional[int] = None
    canonical_form: Optional[str] = None
    cognitive_type: Optional[str] = None
    cluster_id: Optional[int] = None


class DomainGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    kind: str
    weight: float


class DomainGraphResponse(BaseModel):
    graph_id: str
    graph_version: int
    nodes: List[DomainGraphNode]
    edges: List[DomainGraphEdge]
    terms_sampled: int
    packs_sampled: int
    linked_nodes_sampled: int
    generated_at: str


@router.get("/overview", response_model=DomainOverviewResponse)
async def get_domain_overview(
    graph_id: str = Query(...),
    limit: int = Query(12, ge=1, le=50),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> DomainOverviewResponse:
    payload = build_domain_overview(
        session=ctx.session,
        tenant_id=ctx.tenant_id,
        graph_id=graph_id,
        limit=limit,
    )
    return DomainOverviewResponse(**payload)


@router.get("/terms", response_model=DomainTermsResponse)
async def get_domain_terms(
    graph_id: str = Query(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
    kind: Optional[str] = Query(None),
    domain_pack: Optional[str] = Query(None),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> DomainTermsResponse:
    payload = list_domain_terms(
        session=ctx.session,
        tenant_id=ctx.tenant_id,
        graph_id=graph_id,
        limit=limit,
        offset=offset,
        q=q,
        kind=kind,
        domain_pack=domain_pack,
    )
    return DomainTermsResponse(**payload)


@router.get("/graph", response_model=DomainGraphResponse)
async def get_domain_graph(
    graph_id: str = Query(...),
    limit: int = Query(24, ge=6, le=64),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> DomainGraphResponse:
    payload = build_domain_graph(
        session=ctx.session,
        tenant_id=ctx.tenant_id,
        graph_id=graph_id,
        limit=limit,
    )
    return DomainGraphResponse(**payload)
