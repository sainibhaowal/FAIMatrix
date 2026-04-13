"""Optional DocNative extraction adapter for FAIM Native.

This adapter is the permanent FAIM-facing name for the document conversion
path. If the dependency is unavailable, callers should fall back to the
native extractor stack.
"""

from __future__ import annotations

from typing import List, Optional

try:
    from faim.Faim_Native.core.contracts.types import BlockAnchor, EvidenceBlock
except (ImportError, RuntimeError):
    from core.contracts.types import BlockAnchor, EvidenceBlock


def extract_with_docnative(
    file_bytes: bytes, filename: str, raw_id: str
) -> Optional[List[EvidenceBlock]]:
    try:
        from docling.document_converter import DocumentConverter
    except Exception:
        return None

    try:
        converter = DocumentConverter()
        result = converter.convert(source=file_bytes)
        text = getattr(result.document, "export_to_markdown", lambda: "")()
        if not text:
            return None
        return [
            EvidenceBlock.create(
                raw_id=raw_id,
                anchor=BlockAnchor(doc_type="text", char_start=0, char_end=len(text)),
                content=text,
                block_type="text",
                confidence=1.0,
                metadata={"extractor": "docnative", "filename": filename},
            )
        ]
    except Exception:
        return None


def is_docnative_available() -> bool:
    try:
        from docling.document_converter import DocumentConverter  # noqa: F401
    except Exception:
        return False
    return True


__all__ = ["extract_with_docnative", "is_docnative_available"]
