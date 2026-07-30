"""Router for FAIM-native perception.

Routes extraction requests to appropriate extractors based on file type.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import (  # noqa: F401
        BlockAnchor,
        EvidenceBlock,
    )
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import EvidenceBlock


# Extension to doc_type mapping
EXTENSION_DOC_TYPE = {
    # PDF
    ".pdf": "pdf",
    # Word
    ".docx": "docx",
    ".doc": "docx",
    # PowerPoint
    ".pptx": "pptx",
    ".ppt": "pptx",
    # Excel
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    # Text
    ".txt": "text",
    ".md": "text",
    ".markdown": "text",
    ".rst": "text",
    # Code
    ".py": "text",
    ".js": "text",
    ".ts": "text",
    ".java": "text",
    ".go": "text",
    ".rs": "text",
    ".c": "text",
    ".cpp": "text",
    ".h": "text",
    ".hpp": "text",
    ".cs": "text",
    ".rb": "text",
    ".php": "text",
    ".swift": "text",
    ".kt": "text",
    ".scala": "text",
    ".sh": "text",
    ".sql": "text",
    # Data
    ".json": "text",
    ".yaml": "text",
    ".yml": "text",
    ".toml": "text",
    ".xml": "text",
    ".csv": "xlsx",  # Treat CSV like spreadsheet
    # HTML
    ".html": "text",
    ".htm": "text",
    # Images (will be stubs)
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".webp": "image",
    ".svg": "image",
    ".bmp": "image",
    ".tiff": "image",
}


def get_doc_type(filename: str) -> str:
    """Get document type from filename extension.

    Args:
        filename: Filename with extension.

    Returns:
        Document type string.
    """
    ext = Path(filename).suffix.lower()
    return EXTENSION_DOC_TYPE.get(ext, "text")


def is_supported(filename: str) -> bool:
    """Check if file type is supported for extraction.

    Args:
        filename: Filename to check.

    Returns:
        True if supported.
    """
    ext = Path(filename).suffix.lower()
    return ext in EXTENSION_DOC_TYPE


def route_extraction(
    file_bytes: bytes,
    filename: str,
    raw_id: str,
    *,
    settings: Optional[dict] = None,
) -> list[EvidenceBlock]:
    """Route extraction to appropriate extractor based on file type.

    This is the main entry point for FAIM-native extraction.

    Args:
        file_bytes: Raw file content.
        filename: Original filename (for type detection).
        raw_id: Reference to RawRef ID.
        settings: Optional extraction settings.

    Returns:
        List of EvidenceBlocks with anchors.
    """
    # Import extractors here to avoid circular imports
    try:
        from faim.Faim_Native.perception.extract.extractors_faim import (
            extract_docx_blocks,
            extract_image_stub,
            extract_pdf_blocks,
            extract_pptx_blocks,
            extract_text_blocks,
            extract_xlsx_blocks,
        )
    except ImportError:
        from perception.extract.extractors_faim import (
            extract_docx_blocks,
            extract_image_stub,
            extract_pdf_blocks,
            extract_pptx_blocks,
            extract_text_blocks,
            extract_xlsx_blocks,
        )

    doc_type = get_doc_type(filename)
    settings = settings or {}
    settings["_requested_extractor_mode"] = "faim_native"
    settings["_effective_extractor_mode"] = "faim_native"
    if doc_type == "pdf":
        return extract_pdf_blocks(file_bytes, raw_id, settings=settings)
    elif doc_type == "docx":
        return extract_docx_blocks(file_bytes, raw_id, settings=settings)
    elif doc_type == "pptx":
        return extract_pptx_blocks(file_bytes, raw_id, settings=settings)
    elif doc_type == "xlsx":
        return extract_xlsx_blocks(
            file_bytes, raw_id, filename=filename, settings=settings
        )
    elif doc_type == "image":
        return extract_image_stub(file_bytes, raw_id, filename=filename)
    else:
        return extract_text_blocks(
            file_bytes, raw_id, filename=filename, settings=settings
        )
