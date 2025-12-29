"""
FAIM Storage Router - File Upload and Ingestion

Supports uploading files with:
- Local file storage (no MinIO/S3 required)
- Automatic content extraction (TXT, MD, JSON, PDF, code)
- Direct FAIM memory ingestion
- Real-time status updates
"""
import os
import uuid
import logging
import shutil
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from faim.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Storage"])

# Upload directory (local storage)
UPLOAD_DIR = os.getenv("FAIM_UPLOAD_DIR", "/tmp/faim_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    # Text
    ".txt", ".md", ".markdown",
    # Data
    ".json", ".csv",
    # PDF
    ".pdf",
    # Office Documents (NEW)
    ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    # Code
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
    ".c", ".cpp", ".h", ".cs", ".rb", ".php", ".swift", ".kt",
    ".scala", ".sh", ".bash", ".sql", ".yaml", ".yml", ".toml",
    ".xml", ".html", ".css", ".scss", ".vue", ".svelte",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


# --- Schemas ---

class DocumentOut(BaseModel):
    id: str
    filename: str
    status: str  # pending, processing, ingested, error
    created_at: str
    file_size_bytes: int
    chunks_ingested: int = 0
    error_message: Optional[str] = None


class UploadResponse(BaseModel):
    success: bool
    document: Optional[DocumentOut] = None
    message: str


# --- In-memory document store (for dev mode without full DB) ---
# In production, this uses the Document model from SQL

_documents: dict[str, dict] = {}


def get_document(doc_id: str) -> Optional[dict]:
    """Get document by ID."""
    return _documents.get(doc_id)


def save_document(doc: dict):
    """Save document to in-memory store."""
    _documents[doc["id"]] = doc


def list_documents(project_id: str) -> List[dict]:
    """List documents for a project."""
    return [d for d in _documents.values() if d.get("project_id") == project_id]


# --- Endpoints ---

@router.post("/storage/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    graph_id: Optional[str] = Form(None),
):
    """
    Upload a file and ingest it into FAIM memory.
    
    Supports: TXT, MD, JSON, PDF, and code files.
    Files are parsed, chunked, and stored as FAIM memories.
    """
    # Validate file extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return UploadResponse(
            success=False,
            message=f"Unsupported file type: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    
    # Generate document ID
    doc_id = str(uuid.uuid4())
    
    # S3 key for this document
    s3_key = f"{project_id}/{doc_id}{ext}"
    
    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        if file_size > MAX_FILE_SIZE:
            return UploadResponse(
                success=False,
                message=f"File too large. Max size: {MAX_FILE_SIZE // 1024 // 1024}MB"
            )
        
        # Try S3 upload first, fall back to local storage
        use_s3 = os.getenv("S3_ENDPOINT_URL", "").strip() != ""
        file_path = None
        
        if use_s3:
            try:
                from faim.storage.s3_client import upload_bytes
                from io import BytesIO
                
                upload_bytes(
                    content,
                    s3_key,
                    content_type=file.content_type or "application/octet-stream",
                    metadata={
                        "filename": file.filename,
                        "project_id": project_id,
                        "graph_id": graph_id or "",
                    }
                )
                logger.info(f"Uploaded to S3: {s3_key} ({file_size} bytes)")
            except Exception as s3_err:
                logger.warning(f"S3 upload failed, falling back to local: {s3_err}")
                use_s3 = False
        
        if not use_s3:
            # Fall back to local storage
            project_dir = os.path.join(UPLOAD_DIR, project_id)
            os.makedirs(project_dir, exist_ok=True)
            file_path = os.path.join(project_dir, f"{doc_id}{ext}")
            
            with open(file_path, "wb") as f:
                f.write(content)
            logger.info(f"Saved file locally: {file_path} ({file_size} bytes)")
        
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        return UploadResponse(success=False, message=f"File save failed: {str(e)}")
    
    # Create document record
    doc = {
        "id": doc_id,
        "project_id": project_id,
        "graph_id": graph_id,
        "filename": file.filename,
        "file_path": file_path,
        "file_size_bytes": file_size,
        "status": "processing",
        "created_at": datetime.utcnow().isoformat(),
        "chunks_ingested": 0,
        "error_message": None,
    }
    save_document(doc)
    
    # Extract and ingest content
    try:
        from faim.api.document_parsers import extract_text
        
        result = extract_text(file_path, file.filename)
        chunks = result.get("chunks", [])
        
        if not chunks and result.get("content"):
            # Fallback: single chunk
            chunks = [{"content": result["content"], "metadata": {}}]
        
        logger.info(f"Extracted {len(chunks)} chunks from {file.filename}")
        
        # Ingest chunks into FAIM using the correct add_fragment function
        ingested = 0
        node_ids = []
        faim_graph_id = graph_id
        
        # Resolve graph_id if not provided - use default universe graph
        if not faim_graph_id:
            faim_graph_id = os.getenv("FAIM_DEFAULT_GRAPH_ID", "U:default")
        
        if faim_graph_id:
            from starlette.concurrency import run_in_threadpool
            
            def process_ingestion():
                """Run synchronous FAIM ingestion."""
                try:
                    from faim.engine.interface import add_fragment
                    local_ingested = 0
                    local_ids = []
                    
                    for i, chunk in enumerate(chunks):
                        chunk_content = chunk.get("content", "")
                        if not chunk_content.strip():
                            continue
                        
                        # Build rich text with metadata context
                        metadata = chunk.get("metadata", {})
                        text_with_context = f"[Source: {file.filename}]"
                        if metadata.get("section"):
                            text_with_context += f" [Section: {metadata['section']}]"
                        if metadata.get("page"):
                            text_with_context += f" [Page: {metadata['page']}]"
                        if metadata.get("slide"):
                            text_with_context += f" [Slide: {metadata['slide']}]"
                        if metadata.get("sheet"):
                            text_with_context += f" [Sheet: {metadata['sheet']}]"
                        text_with_context += f"\n\n{chunk_content}"
                        
                        try:
                            # This is the blocking call (compute intensive + DB IO)
                            nid = add_fragment(faim_graph_id, text_with_context)
                            if nid:
                                local_ids.append(nid)
                                local_ingested += 1
                                logger.info(f"Ingested chunk {i+1}/{len(chunks)}: {nid[:16]}...")
                        except Exception as e:
                            logger.warning(f"Failed to ingest chunk {i}: {e}")
                    
                    return local_ingested
                except Exception as e:
                    logger.error(f"Ingestion worker failed: {e}")
                    return 0

            # Run in thread pool to avoid blocking the asyncio loop (Crucial for WebSockets!)
            try:
                ingested = await run_in_threadpool(process_ingestion)
                logger.info(f"✅ Ingested {ingested}/{len(chunks)} chunks into {faim_graph_id}")
            except Exception as e:
                logger.error(f"Async ingestion failed: {e}")
        
        # Update document status
        doc["status"] = "ingested"
        doc["chunks_ingested"] = ingested
        save_document(doc)
        
        return UploadResponse(
            success=True,
            document=DocumentOut(
                id=doc["id"],
                filename=doc["filename"],
                status=doc["status"],
                created_at=doc["created_at"],
                file_size_bytes=doc["file_size_bytes"],
                chunks_ingested=ingested,
            ),
            message=f"Successfully ingested {ingested} chunks from {file.filename}"
        )
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        doc["status"] = "error"
        doc["error_message"] = str(e)
        save_document(doc)
        
        return UploadResponse(
            success=False,
            document=DocumentOut(
                id=doc["id"],
                filename=doc["filename"],
                status=doc["status"],
                created_at=doc["created_at"],
                file_size_bytes=doc["file_size_bytes"],
                error_message=str(e),
            ),
            message=f"Ingestion failed: {str(e)}"
        )


@router.get("/storage/files", response_model=List[DocumentOut])
async def list_files(
    project_id: str = Query(...),
):
    """
    List uploaded documents for a project.
    """
    docs = list_documents(project_id)
    
    return [
        DocumentOut(
            id=d["id"],
            filename=d["filename"],
            status=d["status"],
            created_at=d["created_at"],
            file_size_bytes=d["file_size_bytes"],
            chunks_ingested=d.get("chunks_ingested", 0),
            error_message=d.get("error_message"),
        )
        for d in sorted(docs, key=lambda x: x["created_at"], reverse=True)
    ]


@router.delete("/storage/files/{doc_id}")
async def delete_file(doc_id: str):
    """
    Delete an uploaded document.
    """
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file from disk
    file_path = doc.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to delete file: {e}")
    
    # Remove from store
    del _documents[doc_id]
    
    return {"success": True, "message": "Document deleted"}


@router.get("/storage/status/{doc_id}")
async def get_document_status(doc_id: str):
    """
    Get status of a document (for polling during ingestion).
    """
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentOut(
        id=doc["id"],
        filename=doc["filename"],
        status=doc["status"],
        created_at=doc["created_at"],
        file_size_bytes=doc["file_size_bytes"],
        chunks_ingested=doc.get("chunks_ingested", 0),
        error_message=doc.get("error_message"),
    )
