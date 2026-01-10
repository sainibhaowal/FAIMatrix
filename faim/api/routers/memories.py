# =============================================================================
# FAIM Memories Router - Thin HTTP Layer
# =============================================================================
# Endpoints for memory management. All logic is in services/memory_service.py
# =============================================================================

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from faim.api.middleware.auth_middleware import get_current_user_oidc
from faim.api.services import memory_service
from faim.config.database import get_db
from faim.config.models import User

router = APIRouter(prefix="/memories", tags=["Memories"])


# =============================================================================
# Pydantic Models (HTTP layer)
# =============================================================================


class MemoryInfoResponse(BaseModel):
    id: str
    content: str
    source: Optional[str] = None
    source_name: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Optional[dict] = None


class MemoryListResponse(BaseModel):
    memories: List[MemoryInfoResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class DeleteResponse(BaseModel):
    success: bool
    deleted_count: int
    failed_ids: List[str]
    memories_count: int
    message: str


class BatchDeleteRequest(BaseModel):
    memory_ids: List[str] = Field(..., min_length=1, max_length=100)


class MemoryStatsResponse(BaseModel):
    total_memories: int
    memories_max: int
    by_source: dict


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """List user's memories with pagination."""
    result = memory_service.list_memories(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        source_filter=source,
        search=search,
    )
    return MemoryListResponse(
        memories=[
            MemoryInfoResponse(
                id=m.id,
                content=m.content,
                source=m.source,
                source_name=m.source_name,
                created_at=m.created_at,
                metadata=m.metadata,
            )
            for m in result.memories
        ],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        has_more=result.has_more,
    )


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_stats(
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """Get memory statistics."""
    stats = memory_service.get_memory_stats(db, current_user.id)
    return MemoryStatsResponse(
        total_memories=stats.total_memories,
        memories_max=stats.memories_max,
        by_source=stats.by_source,
    )


@router.get("/{memory_id}", response_model=MemoryInfoResponse)
async def get_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """Get a single memory."""
    memory = memory_service.get_memory(db, current_user.id, memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return MemoryInfoResponse(
        id=memory.id,
        content=memory.content,
        source=memory.source,
        source_name=memory.source_name,
        created_at=memory.created_at,
        metadata=memory.metadata,
    )


@router.delete("/{memory_id}", response_model=DeleteResponse)
async def delete_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """Delete a single memory."""
    result = memory_service.delete_memory(db, current_user.id, memory_id)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.message)
    return DeleteResponse(
        success=result.success,
        deleted_count=result.deleted_count,
        failed_ids=result.failed_ids,
        memories_count=result.new_memories_count,
        message=result.message,
    )


@router.post("/batch-delete", response_model=DeleteResponse)
async def batch_delete(
    request: BatchDeleteRequest,
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """Delete multiple memories at once (max 100)."""
    result = memory_service.batch_delete_memories(
        db=db,
        user_id=current_user.id,
        memory_ids=request.memory_ids,
    )
    return DeleteResponse(
        success=result.success,
        deleted_count=result.deleted_count,
        failed_ids=result.failed_ids,
        memories_count=result.new_memories_count,
        message=result.message,
    )


@router.delete("/clear/all", response_model=DeleteResponse)
async def clear_all(
    confirm: bool = Query(False),
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """⚠️ DANGER: Delete ALL memories. Requires confirm=true."""
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must pass confirm=true to delete all memories.",
        )
    result = memory_service.clear_all_memories(db, current_user.id)
    return DeleteResponse(
        success=result.success,
        deleted_count=result.deleted_count,
        failed_ids=result.failed_ids,
        memories_count=result.new_memories_count,
        message=result.message,
    )
