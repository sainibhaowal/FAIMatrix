"""
FAIM Workers - Background Tasks

Celery tasks for asynchronous processing:
- Document ingestion (PDF, DOCX, TXT)
- Graph reindexing
- Memory pruning/cleanup
- Usage aggregation
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def ingest_document(self, document_id: str, graph_id: str, storage_key: str):
    """
    Ingest a document into the FAIM memory graph.

    Steps:
    1. Read file from local storage (uploaded via router_storage.py)
    2. Extract text (PDF, DOCX, TXT)
    3. Chunk text into fragments
    4. Store each fragment in the graph
    5. Update document status
    """
    try:
        logger.info(f"Starting ingestion for document {document_id}")

        # Import here to avoid circular imports
        from faim.db import SessionLocal
        from faim.models_sql import Document

        db = SessionLocal()
        try:
            # Update status to processing
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                logger.error(f"Document {document_id} not found")
                return {"status": "error", "message": "Document not found"}

            doc.status = "processing"
            db.commit()

            # Read from local storage (storage_key is the local file path)
            file_path = Path(storage_key)
            if not file_path.exists():
                raise Exception(f"File not found: {storage_key}")

            file_data = file_path.read_bytes()

            # Extract text based on file type
            text = ""
            filename = doc.filename or ""

            if filename.endswith(".pdf"):
                text = _extract_pdf_text(file_data)
            elif filename.endswith(".docx"):
                text = _extract_docx_text(file_data)
            else:
                # Assume text file
                text = file_data.decode("utf-8", errors="ignore")

            # Chunk and store
            chunks = _chunk_text(text, max_chars=4000)
            stored_count = 0

            for i, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue
                try:
                    # Store in FAIM graph
                    from faim.api.state import store_memories

                    store_memories(graph_id, [{"text": chunk, "source": filename, "chunk": i}])
                    stored_count += 1
                except Exception as e:
                    logger.warning(f"Failed to store chunk {i}: {e}")

            # Update status to completed
            doc.status = "completed"
            doc.processed_at = datetime.utcnow()
            db.commit()

            # Clean up the temp file after successful ingestion (Pure Ingestion)
            try:
                file_path.unlink()
                logger.info(f"Deleted temp file: {storage_key}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")

            logger.info(f"Ingestion complete: {stored_count} chunks stored")
            return {"status": "completed", "chunks": stored_count}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Ingestion failed for {document_id}: {e}")
        # Retry on failure
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            # Mark as failed after max retries
            from faim.db import SessionLocal
            from faim.models_sql import Document

            db = SessionLocal()
            try:
                doc = db.query(Document).filter(Document.id == document_id).first()
                if doc:
                    doc.status = "failed"
                    db.commit()
            finally:
                db.close()
            return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True)
def reindex_graph(self, graph_id: str):
    """
    Reindex all nodes in a graph for improved retrieval performance.
    """
    try:
        logger.info(f"Starting reindex for graph {graph_id}")

        # This would call your FAIM engine's reindex function
        # For now, just log the action
        from faim.api.state import get_engine

        engine = get_engine(graph_id)

        if hasattr(engine, "reindex"):
            engine.reindex()
            logger.info(f"Reindex complete for graph {graph_id}")
            return {"status": "completed", "graph_id": graph_id}
        else:
            logger.info(f"Reindex not supported for graph {graph_id}")
            return {"status": "skipped", "message": "Reindex not supported"}

    except Exception as e:
        logger.error(f"Reindex failed for {graph_id}: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task
def prune_old_memory():
    """
    Periodic task to clean up old/inactive memory.

    Runs hourly and:
    1. Identifies graphs with no activity in 30+ days
    2. Sends warning notifications
    3. Archives/deletes after 90 days (configurable)
    """
    try:
        logger.info("Starting memory pruning task")

        from faim.db import SessionLocal

        db = SessionLocal()
        try:
            # Find inactive graphs (no usage in 30 days)
            datetime.utcnow() - timedelta(days=30)
            datetime.utcnow() - timedelta(days=90)

            # This is a placeholder - actual implementation would:
            # 1. Query usage_events for last activity per graph
            # 2. Flag graphs with no activity
            # 3. Send notifications
            # 4. Archive/delete very old data

            logger.info("Memory pruning check complete")
            return {"status": "completed", "checked": True}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Memory pruning failed: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task
def aggregate_usage():
    """
    Periodic task to aggregate usage events into daily rollups.

    Runs every 5 minutes and:
    1. Groups raw usage_events by day
    2. Creates summary records
    3. Optionally purges old raw events
    """
    try:
        logger.info("Starting usage aggregation task")

        # Placeholder implementation
        # In production, this would query usage_events and create daily summaries

        return {"status": "completed"}

    except Exception as e:
        logger.error(f"Usage aggregation failed: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task
def run_backup():
    """
    Scheduled task to perform database backup.

    Runs daily at 2 AM (configured in celery_app.py beat schedule).
    Backups are saved to /tmp/faim/backups/ (local Docker volume).
    """
    try:
        logger.info("Starting scheduled database backup")

        from faim.ops.backup import perform_backup

        result = perform_backup()

        if result.get("status") == "success":
            logger.info(f"Backup completed: {result.get('backup_file')}")
        else:
            logger.error(f"Backup failed: {result.get('message')}")

        return result

    except Exception as e:
        logger.error(f"Backup task failed: {e}")
        return {"status": "failed", "error": str(e)}


# --- Helper functions ---


def _extract_pdf_text(data: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=data, filetype="pdf")
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        return "\n\n".join(text_parts)
    except ImportError:
        logger.warning("PyMuPDF not installed, PDF extraction unavailable")
        return ""
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ""


def _extract_docx_text(data: bytes) -> str:
    """Extract text from DOCX bytes."""
    try:
        import io
        import xml.etree.ElementTree as ET
        import zipfile

        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            xml_content = zf.read("word/document.xml")

        tree = ET.fromstring(xml_content)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = tree.findall(".//w:p", ns)

        text_parts = []
        for p in paragraphs:
            texts = p.findall(".//w:t", ns)
            para_text = "".join(t.text or "" for t in texts)
            if para_text.strip():
                text_parts.append(para_text)

        return "\n\n".join(text_parts)
    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        return ""


def _chunk_text(text: str, max_chars: int = 4000) -> list:
    """Split text into chunks of max_chars."""
    if not text:
        return []

    chunks = []
    current = ""

    for para in text.split("\n\n"):
        if len(current) + len(para) + 2 <= max_chars:
            current += para + "\n\n"
        else:
            if current.strip():
                chunks.append(current.strip())
            current = para + "\n\n"

    if current.strip():
        chunks.append(current.strip())

    return chunks
