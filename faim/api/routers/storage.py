"""
FAIM Storage Router - Document Upload with FAIM Ingestion

Uploads documents and immediately ingests them into FAIM memory.
All documents become searchable/visible in FIG View.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from faim.api.middleware.auth_middleware import get_current_user_oidc
from faim.api.services.usage_service import PLAN_LIMITS
from faim.config.database import get_db
from faim.config.models import Document, GraphOwnership, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storage", tags=["Storage"])


class DocumentOut(BaseModel):
    id: str
    filename: str
    status: str
    file_size_bytes: int
    created_at: Optional[str] = None
    nodes_created: Optional[int] = None
    tokens_used: Optional[int] = None


def _get_user_graph_id(user_id, db: Session) -> Optional[str]:
    """Get user's default graph ID."""
    graph = db.query(GraphOwnership).filter(GraphOwnership.user_id == user_id).first()
    return graph.graph_id if graph else None


def _run_ingestion(
    file_bytes: bytes,
    filename: str,
    user_id: str,
    graph_id: str,
    document_id: str,
    db_url: str,
):
    """Background task to ingest document."""
    try:
        from faim.config.database import SessionLocal
        from faim.config.models import Document
        from faim.pipeline.ingest.ingest_service import ingest_document

        # ingest_document now handles embedding + storage
        result = ingest_document(
            file_bytes=file_bytes,
            filename=filename,
            user_id=user_id,
            graph_id=graph_id,
            document_id=document_id,
        )

        # Update document status
        db = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = result.get("status", "completed")
                db.commit()
        finally:
            db.close()

        logger.info(f"[Storage] Ingestion complete: {result}")

    except Exception as e:
        logger.error(f"[Storage] Ingestion failed: {e}")


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    graph_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """
    Upload a document and ingest it into FAIM memory.

    The document is immediately stored and indexed.
    After ingestion, memory nodes appear in FIG View.
    Tracks storage usage and enforces limits.
    """
    # Get or verify graph
    if graph_id:
        graph = (
            db.query(GraphOwnership)
            .filter(GraphOwnership.graph_id == graph_id, GraphOwnership.user_id == current_user.id)
            .first()
        )
        if not graph:
            raise HTTPException(status_code=403, detail="Graph not found or access denied")
    else:
        # Use user's default graph
        graph_id = _get_user_graph_id(current_user.id, db)
        if not graph_id:
            raise HTTPException(status_code=400, detail="No graph found. Please create one first.")

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Check storage limit
    limits = PLAN_LIMITS.get(current_user.plan or "free", PLAN_LIMITS["free"])
    current_storage = current_user.storage_used_bytes or 0

    if current_storage + file_size > limits["storage_bytes"]:
        raise HTTPException(
            status_code=402,
            detail=f"Storage limit exceeded ({current_storage:,}/{limits['storage_bytes']:,} bytes). Upgrade your plan.",
        )

    s3_key = f"documents/{current_user.id}/{uuid.uuid4()}/{file.filename}"

    # Create document record
    doc = Document(
        user_id=current_user.id,
        graph_id=graph_id,
        filename=file.filename,
        s3_key=s3_key,
        file_size_bytes=file_size,
        status="processing",
    )
    db.add(doc)

    # Update storage usage
    current_user.storage_used_bytes = (current_user.storage_used_bytes or 0) + file_size
    db.commit()
    db.refresh(doc)

    # Start ingestion in background for faster response
    background_tasks.add_task(
        _run_ingestion,
        file_bytes=content,
        filename=file.filename,
        user_id=str(current_user.id),
        graph_id=graph_id,
        document_id=str(doc.id),
        db_url="",  # Not used, SessionLocal handles it
    )

    logger.info(f"[Storage] Upload started: {file.filename} ({file_size} bytes) for user {current_user.id}")

    return DocumentOut(
        id=str(doc.id),
        filename=doc.filename,
        status=doc.status,
        file_size_bytes=doc.file_size_bytes,
        created_at=doc.created_at.isoformat() if doc.created_at else None,
    )


@router.get("/documents")
@router.get("/files")
def list_documents(
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """List user's documents."""
    docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    return [
        DocumentOut(
            id=str(d.id),
            filename=d.filename,
            status=d.status,
            file_size_bytes=d.file_size_bytes,
            created_at=d.created_at.isoformat() if d.created_at else None,
        )
        for d in docs
    ]


@router.delete("/documents/{doc_id}")
@router.delete("/files/{doc_id}")
def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """Delete a document and reclaim storage."""
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Reclaim storage
    current_user.storage_used_bytes = max(0, (current_user.storage_used_bytes or 0) - doc.file_size_bytes)
    db.delete(doc)
    db.commit()

    logger.info(f"[Storage] Deleted: {doc.filename}, reclaimed {doc.file_size_bytes} bytes")

    return {"status": "deleted", "id": doc_id}


@router.get("/files/{doc_id}/content")
@router.get("/documents/{doc_id}/content")
def get_document_content(
    doc_id: str,
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """Get document content (for preview)."""
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"content": "Preview not available. Document has been ingested into FAIM memory."}


# =============================================================================
# Batch Delete Endpoints
# =============================================================================

from typing import List


class BatchDeleteRequest(BaseModel):
    """Request to delete multiple documents."""

    document_ids: List[str]


class BatchDeleteResponse(BaseModel):
    """Response for batch delete."""

    success: bool
    deleted_count: int
    failed_ids: List[str]
    storage_reclaimed_bytes: int
    message: str


@router.post("/documents/batch-delete", response_model=BatchDeleteResponse)
@router.post("/files/batch-delete", response_model=BatchDeleteResponse)
def batch_delete_documents(
    request: BatchDeleteRequest,
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """
    Delete multiple documents at once.

    Select multiple files in UI and delete them all.
    Reclaims storage for all deleted files.
    """
    from faim.api.services import document_service

    result = document_service.batch_delete_documents(
        db=db,
        user_id=current_user.id,
        document_ids=request.document_ids,
    )

    return BatchDeleteResponse(
        success=result.success,
        deleted_count=result.deleted_count,
        failed_ids=result.failed_ids,
        storage_reclaimed_bytes=result.storage_reclaimed_bytes,
        message=result.message,
    )


@router.delete("/documents/all", response_model=BatchDeleteResponse)
@router.delete("/files/all", response_model=BatchDeleteResponse)
def delete_all_documents(
    confirm: bool = Query(False),
    current_user: User = Depends(get_current_user_oidc),
    db: Session = Depends(get_db),
):
    """
    ⚠️ DANGER: Delete ALL user's documents.

    Requires confirm=true query parameter.
    Reclaims all storage used by documents.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must pass confirm=true to delete all documents.",
        )

    from faim.api.services import document_service

    result = document_service.clear_all_documents(db, current_user.id)

    return BatchDeleteResponse(
        success=result.success,
        deleted_count=result.deleted_count,
        failed_ids=result.failed_ids,
        storage_reclaimed_bytes=result.storage_reclaimed_bytes,
        message=result.message,
    )
