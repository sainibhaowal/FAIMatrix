# =============================================================================
# FAIM Document Service - Business Logic for Document Management
# =============================================================================
# File: faim/api/services/document_service.py
#
# Contains all document-related business logic:
# - List documents
# - Delete single document
# - Batch delete documents
# - Delete all documents
# - Get document stats
# =============================================================================

from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from faim.config.models import Document, User

# =============================================================================
# Data Transfer Objects
# =============================================================================


@dataclass
class DocumentInfo:
    """Document information."""

    id: str
    filename: str
    status: str
    file_size_bytes: int
    graph_id: Optional[str]
    created_at: Optional[str]


@dataclass
class DocumentListResult:
    """Result of listing documents."""

    documents: List[DocumentInfo]
    total: int
    page: int
    page_size: int
    has_more: bool


@dataclass
class DeleteResult:
    """Result of delete operation."""

    success: bool
    deleted_count: int
    failed_ids: List[str]
    storage_reclaimed_bytes: int
    message: str


@dataclass
class DocumentStats:
    """Document statistics."""

    total_documents: int
    total_size_bytes: int
    storage_max_bytes: int
    by_status: dict


# =============================================================================
# List Documents
# =============================================================================


def list_documents(
    db: Session,
    user_id: UUID,
    page: int = 1,
    page_size: int = 50,
    status_filter: Optional[str] = None,
) -> DocumentListResult:
    """
    List documents for a user with pagination.

    Args:
        db: Database session
        user_id: User's UUID
        page: Page number (1-indexed)
        page_size: Items per page
        status_filter: Optional filter by status (pending, processing, completed, failed)

    Returns:
        DocumentListResult with paginated documents
    """
    query = db.query(Document).filter(Document.user_id == user_id)

    if status_filter:
        query = query.filter(Document.status == status_filter)

    # Order by most recent first
    query = query.order_by(Document.created_at.desc())

    # Get total count
    total = query.count()

    # Paginate
    offset = (page - 1) * page_size
    docs = query.offset(offset).limit(page_size).all()

    return DocumentListResult(
        documents=[
            DocumentInfo(
                id=str(d.id),
                filename=d.filename,
                status=d.status,
                file_size_bytes=d.file_size_bytes or 0,
                graph_id=d.graph_id,
                created_at=d.created_at.isoformat() if d.created_at else None,
            )
            for d in docs
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(docs)) < total,
    )


# =============================================================================
# Get Single Document
# =============================================================================


def get_document(db: Session, user_id: UUID, document_id: str) -> Optional[DocumentInfo]:
    """
    Get a single document by ID.

    Returns None if not found or not owned by user.
    """
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()

    if not doc:
        return None

    return DocumentInfo(
        id=str(doc.id),
        filename=doc.filename,
        status=doc.status,
        file_size_bytes=doc.file_size_bytes or 0,
        graph_id=doc.graph_id,
        created_at=doc.created_at.isoformat() if doc.created_at else None,
    )


# =============================================================================
# Delete Single Document
# =============================================================================


def delete_document(db: Session, user_id: UUID, document_id: str) -> DeleteResult:
    """
    Delete a single document and reclaim storage.
    """
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()

    if not doc:
        return DeleteResult(
            success=False,
            deleted_count=0,
            failed_ids=[document_id],
            storage_reclaimed_bytes=0,
            message="Document not found",
        )

    storage_reclaimed = doc.file_size_bytes or 0

    # Update user's storage
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.storage_used_bytes = max(0, (user.storage_used_bytes or 0) - storage_reclaimed)

    db.delete(doc)
    db.commit()

    return DeleteResult(
        success=True,
        deleted_count=1,
        failed_ids=[],
        storage_reclaimed_bytes=storage_reclaimed,
        message=f"Deleted {doc.filename}, reclaimed {storage_reclaimed:,} bytes",
    )


# =============================================================================
# Batch Delete Documents
# =============================================================================


def batch_delete_documents(
    db: Session,
    user_id: UUID,
    document_ids: List[str],
) -> DeleteResult:
    """
    Delete multiple documents at once.

    Args:
        db: Database session
        user_id: User's UUID
        document_ids: List of document IDs to delete

    Returns:
        DeleteResult with count and any failed IDs
    """
    deleted_count = 0
    failed_ids = []
    storage_reclaimed = 0

    for doc_id in document_ids:
        doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user_id).first()

        if doc:
            storage_reclaimed += doc.file_size_bytes or 0
            db.delete(doc)
            deleted_count += 1
        else:
            failed_ids.append(doc_id)

    # Update user's storage
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.storage_used_bytes = max(0, (user.storage_used_bytes or 0) - storage_reclaimed)

    db.commit()

    return DeleteResult(
        success=deleted_count > 0,
        deleted_count=deleted_count,
        failed_ids=failed_ids,
        storage_reclaimed_bytes=storage_reclaimed,
        message=f"Deleted {deleted_count} documents, reclaimed {storage_reclaimed:,} bytes",
    )


# =============================================================================
# Delete All Documents
# =============================================================================


def clear_all_documents(db: Session, user_id: UUID) -> DeleteResult:
    """
    Delete ALL documents for a user.

    ⚠️ DANGER: This is irreversible!

    Returns:
        DeleteResult with total count and storage reclaimed
    """
    # Get all documents
    docs = db.query(Document).filter(Document.user_id == user_id).all()

    deleted_count = len(docs)
    storage_reclaimed = sum(d.file_size_bytes or 0 for d in docs)

    # Delete all
    db.query(Document).filter(Document.user_id == user_id).delete()

    # Reset user's storage
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.storage_used_bytes = 0

    db.commit()

    return DeleteResult(
        success=True,
        deleted_count=deleted_count,
        failed_ids=[],
        storage_reclaimed_bytes=storage_reclaimed,
        message=f"Deleted all {deleted_count} documents, reclaimed {storage_reclaimed:,} bytes",
    )


# =============================================================================
# Document Statistics
# =============================================================================


def get_document_stats(db: Session, user_id: UUID) -> DocumentStats:
    """
    Get document statistics for a user.
    """
    docs = db.query(Document).filter(Document.user_id == user_id).all()

    total = len(docs)
    total_size = sum(d.file_size_bytes or 0 for d in docs)

    # Count by status
    by_status = {}
    for doc in docs:
        status = doc.status or "unknown"
        by_status[status] = by_status.get(status, 0) + 1

    # Get user's storage limit
    user = db.query(User).filter(User.id == user_id).first()
    storage_max = user.storage_max_bytes if user else 104_857_600  # 100MB default

    return DocumentStats(
        total_documents=total,
        total_size_bytes=total_size,
        storage_max_bytes=storage_max,
        by_status=by_status,
    )
