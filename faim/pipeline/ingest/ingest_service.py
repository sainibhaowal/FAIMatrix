"""
FAIM Document Ingestion Service — Engine-First Architecture
============================================================

Converts uploaded documents into FAIM memory.

Flow:
  1. Extractor: Convert file → Plain text
  2. Chunker: Split text → Chunks (this file)
  3. Engine: Handle everything else (embed, store, events)

This follows "Engine is King" architecture.
All embedding, storage, and event emission is delegated to the Engine.
"""

import logging
from typing import Any, Dict, List, Optional

from faim.pipeline.ingest.extractors import extract_text

logger = logging.getLogger(__name__)

# Chunk settings
DEFAULT_CHUNK_SIZE = 1000  # words approx
CHUNK_OVERLAP = 100


def ingest_document(
    file_bytes: bytes,
    filename: str,
    user_id: str,
    graph_id: str,
    document_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ingest a document into FAIM memory.

    Steps:
      1. Extract text from file
      2. Chunk text into pieces
      3. Send each chunk to Engine (Engine handles embed + store + events)

    Returns:
      Dict with status, nodes_created, etc.
    """
    logger.info(f"[Ingest] Starting: {filename} for user {user_id[:8]}...")

    # =========================================================================
    # STEP 1: Extract text
    # =========================================================================
    extraction_result = extract_text(file_bytes, filename)

    # Handle both tuple (new) and dict (legacy) return formats
    if isinstance(extraction_result, tuple):
        text, token_estimate = extraction_result
    else:
        text = extraction_result.get("content", "")
        token_estimate = extraction_result.get("tokens", 0)

    if not text or len(text.strip()) < 10:
        logger.warning(f"[Ingest] No text extracted from {filename}")
        return {
            "status": "error",
            "error": "No meaningful text extracted",
            "nodes_created": 0,
            "tokens_used": 0,
        }

    # =========================================================================
    # STEP 2: Chunk text (NO embedding here - Engine handles that)
    # =========================================================================
    chunks = _chunk_text(text, chunk_size=DEFAULT_CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    logger.info(f"[Ingest] Created {len(chunks)} chunks from {filename}")

    # =========================================================================
    # STEP 3: Send to Engine (Engine handles embed + store + events)
    # =========================================================================
    from faim.api.adapters.interface import _get_engine

    engine = _get_engine()
    nodes_created = 0
    node_ids: List[str] = []

    # First, create a "root" node for the document
    root_prefix = f"[doc:{filename}] "
    root_summary = f"Document: {filename} ({len(chunks)} chunks, ~{token_estimate} tokens)"

    try:
        root_node_id = engine.add_memory(graph_id, root_prefix + root_summary)
        node_ids.append(str(root_node_id))
        nodes_created += 1
        logger.info(f"[Ingest] Created root node: {root_node_id}")
    except Exception as e:
        logger.error(f"[Ingest] Failed to create root node: {e}")

    # Then, create child nodes for each chunk
    for i, chunk in enumerate(chunks):
        try:
            # Prefix with document info for context
            chunk_text = f"[doc:{filename}:chunk:{i + 1}/{len(chunks)}] {chunk['content']}"

            # Engine handles: embed, store, events (SSE to UI)
            node_id = engine.add_memory(graph_id, chunk_text)
            node_ids.append(str(node_id))
            nodes_created += 1

            if (i + 1) % 10 == 0:
                logger.info(f"[Ingest] Progress: {i + 1}/{len(chunks)} chunks processed")

        except Exception as e:
            logger.error(f"[Ingest] Failed for chunk {i}: {e}")

    # =========================================================================
    # STEP 4: Update token usage
    # =========================================================================
    _update_user_tokens(user_id, token_estimate)

    logger.info(f"[Ingest] Complete: {nodes_created}/{len(chunks) + 1} nodes created")

    return {
        "status": "completed",
        "filename": filename,
        "nodes_created": nodes_created,
        "chunks_total": len(chunks),
        "tokens_used": token_estimate,
        "text_length": len(text),
        "node_ids": node_ids,
    }


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Simple sliding window chunker.

    Args:
        text: Full text to chunk
        chunk_size: Target words per chunk
        overlap: Words overlap between chunks

    Returns:
        List of {"content": str, "metadata": dict}
    """
    if not text:
        return []

    words = text.split()
    chunks = []
    step = max(1, chunk_size - overlap)

    for i in range(0, len(words), step):
        chunk_words = words[i : i + chunk_size]
        if not chunk_words:
            continue

        content = " ".join(chunk_words)
        chunks.append({"content": content, "metadata": {"index": len(chunks), "word_start": i}})

    return chunks


def _update_user_tokens(user_id: str, tokens: int) -> None:
    """Safely update memory usage. (Tokens renamed to memories count)"""
    try:
        from faim.api.services.usage_service import add_memory_usage
        from faim.config.database import SessionLocal

        db = SessionLocal()
        try:
            add_memory_usage(db, user_id, count=1)  # Each chunk = 1 memory
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[Ingest] Memory usage update failed: {e}")
