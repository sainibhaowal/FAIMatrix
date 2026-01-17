"""FAIM-Native API: Ingest Router.

POST /v1/ingest - Ingest file into FAIM graph.
"""

from __future__ import annotations

import base64
import logging
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["ingest"])


# =============================================================================
# Request/Response Models
# =============================================================================


class IngestRequest(BaseModel):
    """Ingest request body."""

    graph_id: str
    raw_id: Optional[str] = None  # Existing raw_id, or generate new
    filename: str
    bytes_base64: Optional[str] = None  # Alternative to multipart
    profile: str = "strict"  # strict, fast, relaxed
    persist_mode: str = "relaxed"  # strict, relaxed


class IngestResponse(BaseModel):
    """Ingest response."""

    status: str
    packet_hash: str
    graph_version: int
    nodes_written: int
    merges: int
    block_count: int
    vector_count: int
    events_emitted: list[str]
    latency_ms: int
    error: Optional[str] = None


# =============================================================================
# Ingest Endpoint
# =============================================================================


@router.post("/ingest", response_model=IngestResponse)
async def ingest_file(
    request: IngestRequest,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> IngestResponse:
    """Ingest a file into the FAIM graph.

    Uses Stage-1 raw ingest, then orchestration.run_ingest().

    Returns packet_hash (idempotency key), graph_version, and events.
    """
    try:
        # Decode file bytes
        if request.bytes_base64:
            file_bytes = base64.b64decode(request.bytes_base64)
        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide bytes_base64 or use multipart upload",
            )

        # Import orchestration
        from orchestration.ingest_flow import FAIMProfile, PersistMode, run_ingest

        # Map profile/persist_mode
        profile = FAIMProfile(request.profile.lower())
        persist_mode = PersistMode(request.persist_mode.lower())

        # Run ingest
        result = run_ingest(
            graph_id=request.graph_id,
            raw_id=request.raw_id or "",
            filename=request.filename,
            file_bytes=file_bytes,
            profile=profile,
            persist_mode=persist_mode,
            node_repo=ctx.node_repo,
            edge_repo=ctx.edge_repo,
            event_repo=ctx.event_repo,
            gv_repo=ctx.gv_repo,
        )

        return IngestResponse(
            status=result.status,
            packet_hash=result.packet_hash,
            graph_version=result.graph_version,
            nodes_written=result.nodes_written,
            merges=result.merges,
            block_count=result.block_count,
            vector_count=result.vector_count,
            events_emitted=result.events_emitted,
            latency_ms=result.latency_ms,
            error=result.error,
        )

    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


# =============================================================================
# Multipart Upload
# =============================================================================


@router.post("/ingest/upload", response_model=IngestResponse)
async def ingest_upload(
    graph_id: str = Form(...),
    profile: str = Form("strict"),
    persist_mode: str = Form("relaxed"),
    file: UploadFile = File(...),  # noqa: B008
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> IngestResponse:
    """Ingest a file via multipart upload.

    Alternative to JSON body with bytes_base64.
    """
    try:
        file_bytes = await file.read()
        filename = file.filename or "upload"

        from orchestration.ingest_flow import FAIMProfile, PersistMode, run_ingest

        profile_enum = FAIMProfile(profile.lower())
        persist_mode_enum = PersistMode(persist_mode.lower())

        result = run_ingest(
            graph_id=graph_id,
            raw_id="",
            filename=filename,
            file_bytes=file_bytes,
            profile=profile_enum,
            persist_mode=persist_mode_enum,
            node_repo=ctx.node_repo,
            edge_repo=ctx.edge_repo,
            event_repo=ctx.event_repo,
            gv_repo=ctx.gv_repo,
        )

        return IngestResponse(
            status=result.status,
            packet_hash=result.packet_hash,
            graph_version=result.graph_version,
            nodes_written=result.nodes_written,
            merges=result.merges,
            block_count=result.block_count,
            vector_count=result.vector_count,
            events_emitted=result.events_emitted,
            latency_ms=result.latency_ms,
            error=result.error,
        )

    except Exception as e:
        logger.error(f"Ingest upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904


__all__ = ["router"]
