"""FAIM-native extractors returning EvidenceBlocks.

This module provides extraction functions that return EvidenceBlocks
with anchors instead of text/tokens/HTML.

All functions follow the pattern:
    extract_*_blocks(file_bytes, raw_id, **kwargs) -> list[EvidenceBlock]
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Optional

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import BlockAnchor, EvidenceBlock
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import BlockAnchor, EvidenceBlock


# =============================================================================
# PDF Extraction
# =============================================================================


def extract_pdf_blocks(
    file_bytes: bytes,
    raw_id: str,
    *,
    settings: Optional[dict] = None,
) -> list[EvidenceBlock]:
    """Extract blocks from PDF with page anchors.

    Args:
        file_bytes: PDF content.
        raw_id: Reference to RawRef.
        settings: Optional extraction settings.

    Returns:
        List of EvidenceBlocks with page anchors.
    """
    settings = settings or {}
    blocks = []

    # Try PyMuPDF first
    try:
        import fitz

        doc = fitz.open(stream=file_bytes, filetype="pdf")

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()

            if page_text.strip():
                anchor = BlockAnchor(
                    doc_type="pdf",
                    page=page_num + 1,  # 1-indexed
                )

                blocks.append(
                    EvidenceBlock.create(
                        raw_id=raw_id,
                        anchor=anchor,
                        content=page_text.strip(),
                        block_type="text",
                        confidence=1.0,
                        metadata={"page_count": len(doc)},
                    )
                )

            # Check for image-only pages (OCR stub)
            if not page_text.strip() and page.get_images():
                anchor = BlockAnchor(
                    doc_type="pdf",
                    page=page_num + 1,
                )
                blocks.append(
                    EvidenceBlock.create(
                        raw_id=raw_id,
                        anchor=anchor,
                        content="[IMAGE_STUB: Page contains image content requiring OCR]",
                        block_type="image_stub",
                        confidence=0.2,  # Low confidence for OCR stub
                        metadata={"image_count": len(page.get_images())},
                    )
                )

        doc.close()
        return blocks

    except ImportError:
        pass
    except Exception:
        pass

    # Try pdfplumber
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""

                # Extract tables separately
                tables = page.extract_tables() or []

                if page_text.strip():
                    anchor = BlockAnchor(
                        doc_type="pdf",
                        page=i + 1,
                    )
                    blocks.append(
                        EvidenceBlock.create(
                            raw_id=raw_id,
                            anchor=anchor,
                            content=page_text.strip(),
                            block_type="text",
                            confidence=1.0,
                        )
                    )

                # Add tables as separate blocks
                for table_idx, table in enumerate(tables):
                    table_text = "\n".join(
                        " | ".join(str(cell or "") for cell in row) for row in table
                    )
                    if table_text.strip():
                        anchor = BlockAnchor(
                            doc_type="pdf",
                            page=i + 1,
                        )
                        blocks.append(
                            EvidenceBlock.create(
                                raw_id=raw_id,
                                anchor=anchor,
                                content=table_text.strip(),
                                block_type="table",
                                confidence=1.0,
                                metadata={"table_index": table_idx},
                            )
                        )

        return blocks

    except ImportError:
        pass
    except Exception:
        pass

    # Fallback to pypdf
    try:
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))

        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""

            if page_text.strip():
                anchor = BlockAnchor(
                    doc_type="pdf",
                    page=i + 1,
                )
                blocks.append(
                    EvidenceBlock.create(
                        raw_id=raw_id,
                        anchor=anchor,
                        content=page_text.strip(),
                        block_type="text",
                        confidence=1.0,
                    )
                )

        return blocks

    except Exception:
        pass

    # Ultimate fallback: single stub block
    anchor = BlockAnchor(doc_type="pdf", page=1)
    blocks.append(
        EvidenceBlock.create(
            raw_id=raw_id,
            anchor=anchor,
            content="[EXTRACTION_FAILED: Could not extract PDF content]",
            block_type="text",
            confidence=0.0,
        )
    )

    return blocks


# =============================================================================
# DOCX Extraction
# =============================================================================


def extract_docx_blocks(
    file_bytes: bytes,
    raw_id: str,
    *,
    settings: Optional[dict] = None,
) -> list[EvidenceBlock]:
    """Extract blocks from DOCX with character offset anchors.

    Args:
        file_bytes: DOCX content.
        raw_id: Reference to RawRef.
        settings: Optional extraction settings.

    Returns:
        List of EvidenceBlocks with char anchors.
    """
    blocks = []
    char_offset = 0

    try:
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))

        # Extract paragraphs
        for para_idx, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if not text:
                continue

            # Determine block type based on style
            style_name = para.style.name if para.style else ""
            if "heading" in style_name.lower():
                block_type = "heading"
            else:
                block_type = "text"

            anchor = BlockAnchor(
                doc_type="docx",
                char_start=char_offset,
                char_end=char_offset + len(text),
                section=style_name if "heading" in style_name.lower() else None,
            )

            blocks.append(
                EvidenceBlock.create(
                    raw_id=raw_id,
                    anchor=anchor,
                    content=text,
                    block_type=block_type,
                    confidence=1.0,
                    metadata={"paragraph_index": para_idx},
                )
            )

            char_offset += len(text) + 1  # +1 for newline

        # Extract tables
        for table_idx, table in enumerate(doc.tables):
            table_rows = []
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells]
                table_rows.append(" | ".join(row_text))

            table_text = "\n".join(table_rows)
            if table_text.strip():
                anchor = BlockAnchor(
                    doc_type="docx",
                    char_start=char_offset,
                    char_end=char_offset + len(table_text),
                )

                blocks.append(
                    EvidenceBlock.create(
                        raw_id=raw_id,
                        anchor=anchor,
                        content=table_text,
                        block_type="table",
                        confidence=1.0,
                        metadata={"table_index": table_idx},
                    )
                )

                char_offset += len(table_text) + 1

        return blocks

    except ImportError:
        pass
    except Exception:
        pass

    # Fallback
    anchor = BlockAnchor(doc_type="docx", char_start=0, char_end=0)
    blocks.append(
        EvidenceBlock.create(
            raw_id=raw_id,
            anchor=anchor,
            content="[EXTRACTION_FAILED: Could not extract DOCX content]",
            block_type="text",
            confidence=0.0,
        )
    )

    return blocks


# =============================================================================
# PPTX Extraction
# =============================================================================


def extract_pptx_blocks(
    file_bytes: bytes,
    raw_id: str,
    *,
    settings: Optional[dict] = None,
) -> list[EvidenceBlock]:
    """Extract blocks from PPTX with slide anchors.

    Args:
        file_bytes: PPTX content.
        raw_id: Reference to RawRef.
        settings: Optional extraction settings.

    Returns:
        List of EvidenceBlocks with slide anchors.
    """
    blocks = []

    try:
        from pptx import Presentation

        prs = Presentation(io.BytesIO(file_bytes))

        for slide_num, slide in enumerate(prs.slides, 1):
            slide_texts = []

            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_texts.append(shape.text.strip())

            if slide_texts:
                anchor = BlockAnchor(
                    doc_type="pptx",
                    slide=slide_num,
                )

                blocks.append(
                    EvidenceBlock.create(
                        raw_id=raw_id,
                        anchor=anchor,
                        content="\n".join(slide_texts),
                        block_type="text",
                        confidence=1.0,
                        metadata={"slide_count": len(prs.slides)},
                    )
                )

        return blocks

    except ImportError:
        pass
    except Exception:
        pass

    # Fallback
    anchor = BlockAnchor(doc_type="pptx", slide=1)
    blocks.append(
        EvidenceBlock.create(
            raw_id=raw_id,
            anchor=anchor,
            content="[EXTRACTION_FAILED: Could not extract PPTX content]",
            block_type="text",
            confidence=0.0,
        )
    )

    return blocks


# =============================================================================
# XLSX/CSV Extraction
# =============================================================================


def extract_xlsx_blocks(
    file_bytes: bytes,
    raw_id: str,
    *,
    filename: str = "",
    settings: Optional[dict] = None,
) -> list[EvidenceBlock]:
    """Extract blocks from XLSX/CSV with sheet/row anchors.

    Args:
        file_bytes: XLSX/CSV content.
        raw_id: Reference to RawRef.
        filename: Original filename for type detection.
        settings: Optional extraction settings.

    Returns:
        List of EvidenceBlocks with sheet/row anchors.
    """
    blocks = []
    ext = Path(filename).suffix.lower() if filename else ""

    # CSV handling
    if ext == ".csv":
        try:
            import csv

            text = file_bytes.decode("utf-8", errors="ignore")
            reader = csv.reader(io.StringIO(text))
            rows = list(reader)

            # Group rows into blocks (e.g., 50 rows per block)
            ROWS_PER_BLOCK = 50

            for start_row in range(0, len(rows), ROWS_PER_BLOCK):
                end_row = min(start_row + ROWS_PER_BLOCK, len(rows))
                chunk_rows = rows[start_row:end_row]

                content = "\n".join(" | ".join(row) for row in chunk_rows)

                anchor = BlockAnchor(
                    doc_type="xlsx",
                    sheet="Sheet1",
                    row_start=start_row + 1,  # 1-indexed
                    row_end=end_row,
                )

                blocks.append(
                    EvidenceBlock.create(
                        raw_id=raw_id,
                        anchor=anchor,
                        content=content,
                        block_type="table",
                        confidence=1.0,
                        metadata={"total_rows": len(rows)},
                    )
                )

            return blocks if blocks else [_fallback_block(raw_id, "xlsx")]

        except Exception:
            pass

    # XLSX handling
    try:
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True)

        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            rows_data = list(sheet.iter_rows(values_only=True))

            if not rows_data:
                continue

            # Group rows into blocks
            ROWS_PER_BLOCK = 50

            for start_row in range(0, len(rows_data), ROWS_PER_BLOCK):
                end_row = min(start_row + ROWS_PER_BLOCK, len(rows_data))
                chunk_rows = rows_data[start_row:end_row]

                content_rows = []
                for row in chunk_rows:
                    row_values = [str(cell) if cell is not None else "" for cell in row]
                    content_rows.append(" | ".join(row_values))

                content = "\n".join(content_rows)

                if content.strip():
                    anchor = BlockAnchor(
                        doc_type="xlsx",
                        sheet=sheet_name,
                        row_start=start_row + 1,
                        row_end=end_row,
                    )

                    blocks.append(
                        EvidenceBlock.create(
                            raw_id=raw_id,
                            anchor=anchor,
                            content=content,
                            block_type="table",
                            confidence=1.0,
                            metadata={
                                "sheet": sheet_name,
                                "total_rows": len(rows_data),
                            },
                        )
                    )

        wb.close()
        return blocks if blocks else [_fallback_block(raw_id, "xlsx")]

    except ImportError:
        pass
    except Exception:
        pass

    return [_fallback_block(raw_id, "xlsx")]


# =============================================================================
# Text/Code Extraction
# =============================================================================


def extract_text_blocks(
    file_bytes: bytes,
    raw_id: str,
    *,
    filename: str = "",
    settings: Optional[dict] = None,
) -> list[EvidenceBlock]:
    """Extract blocks from text/code files with char offset anchors.

    Args:
        file_bytes: Text content.
        raw_id: Reference to RawRef.
        filename: Original filename.
        settings: Optional extraction settings.

    Returns:
        List of EvidenceBlocks with char anchors.
    """
    # Decode text
    text = None
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            text = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        text = file_bytes.decode("utf-8", errors="ignore")

    # Remove NUL characters
    text = text.replace("\x00", "")

    if not text.strip():
        return [_fallback_block(raw_id, "text")]

    # Determine if markdown (section-based extraction)
    ext = Path(filename).suffix.lower() if filename else ""
    if ext in (".md", ".markdown", ".rst"):
        return _extract_markdown_blocks(text, raw_id)

    # For regular text/code, create single block or split by natural boundaries
    blocks = []

    # If file is small, single block
    if len(text) < 5000:
        anchor = BlockAnchor(
            doc_type="text",
            char_start=0,
            char_end=len(text),
        )
        blocks.append(
            EvidenceBlock.create(
                raw_id=raw_id,
                anchor=anchor,
                content=text,
                block_type=(
                    "code"
                    if ext in (".py", ".js", ".ts", ".java", ".go", ".rs")
                    else "text"
                ),
                confidence=1.0,
            )
        )
    else:
        # Split into ~2000 char blocks at paragraph boundaries
        BLOCK_SIZE = 2000
        paragraphs = text.split("\n\n")
        current_block = []
        current_size = 0
        char_start = 0

        for para in paragraphs:
            if current_size + len(para) > BLOCK_SIZE and current_block:
                content = "\n\n".join(current_block)
                anchor = BlockAnchor(
                    doc_type="text",
                    char_start=char_start,
                    char_end=char_start + len(content),
                )
                blocks.append(
                    EvidenceBlock.create(
                        raw_id=raw_id,
                        anchor=anchor,
                        content=content,
                        block_type="text",
                        confidence=1.0,
                    )
                )
                char_start += len(content) + 2  # +2 for \n\n
                current_block = []
                current_size = 0

            current_block.append(para)
            current_size += len(para) + 2

        # Final block
        if current_block:
            content = "\n\n".join(current_block)
            anchor = BlockAnchor(
                doc_type="text",
                char_start=char_start,
                char_end=char_start + len(content),
            )
            blocks.append(
                EvidenceBlock.create(
                    raw_id=raw_id,
                    anchor=anchor,
                    content=content,
                    block_type="text",
                    confidence=1.0,
                )
            )

    return blocks


def _extract_markdown_blocks(text: str, raw_id: str) -> list[EvidenceBlock]:
    """Extract blocks from markdown with section anchors."""
    blocks = []
    lines = text.split("\n")

    current_section = "Introduction"
    current_content = []
    char_start = 0

    for line in lines:
        if line.startswith("#"):
            # Save previous section
            if current_content:
                content = "\n".join(current_content)
                anchor = BlockAnchor(
                    doc_type="text",
                    char_start=char_start,
                    char_end=char_start + len(content),
                    section=current_section,
                )
                blocks.append(
                    EvidenceBlock.create(
                        raw_id=raw_id,
                        anchor=anchor,
                        content=content,
                        block_type=(
                            "heading" if current_section != "Introduction" else "text"
                        ),
                        confidence=1.0,
                    )
                )
                char_start += len(content) + 1

            # Start new section
            current_section = line.lstrip("#").strip()
            current_content = [line]
        else:
            current_content.append(line)

    # Final section
    if current_content:
        content = "\n".join(current_content)
        anchor = BlockAnchor(
            doc_type="text",
            char_start=char_start,
            char_end=char_start + len(content),
            section=current_section,
        )
        blocks.append(
            EvidenceBlock.create(
                raw_id=raw_id,
                anchor=anchor,
                content=content,
                block_type="text",
                confidence=1.0,
            )
        )

    return blocks if blocks else [_fallback_block(raw_id, "text")]


# =============================================================================
# Image Stub (OCR placeholder)
# =============================================================================


def extract_image_stub(
    file_bytes: bytes,
    raw_id: str,
    *,
    filename: str = "",
) -> list[EvidenceBlock]:
    """Create stub block for image files (OCR placeholder).

    Args:
        file_bytes: Image content.
        raw_id: Reference to RawRef.
        filename: Original filename.

    Returns:
        Single IMAGE_STUB block with low confidence.
    """
    anchor = BlockAnchor(
        doc_type="image",
        page=1,
    )

    return [
        EvidenceBlock.create(
            raw_id=raw_id,
            anchor=anchor,
            content=f"[IMAGE_STUB: {filename or 'image'} requires OCR processing]",
            block_type="image_stub",
            confidence=0.2,  # Low confidence for OCR stub
            metadata={
                "filename": filename,
                "size_bytes": len(file_bytes),
            },
        )
    ]


# =============================================================================
# Helper Functions
# =============================================================================


def _fallback_block(raw_id: str, doc_type: str) -> EvidenceBlock:
    """Create fallback block when extraction fails."""
    anchor = BlockAnchor(
        doc_type=doc_type,
        char_start=0,
        char_end=0,
    )
    return EvidenceBlock.create(
        raw_id=raw_id,
        anchor=anchor,
        content="[EXTRACTION_FAILED: Could not extract content]",
        block_type="text",
        confidence=0.0,
    )
