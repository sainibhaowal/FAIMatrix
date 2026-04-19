"""FAIM-native extractors returning EvidenceBlocks.

Supports:
- Multi-column PDFs (scientific papers, reports)
- Scanned PDFs with no text layer (pure image pages via OCR)
- Complex table extraction (per-page, with header detection)
- DOCX with heading hierarchy, inline tables
- PPTX with speaker notes, table shapes, reading order
- XLSX/CSV with header detection
- All plain text / code / markdown
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from faim.Faim_Native.core.contracts.types import BlockAnchor, EvidenceBlock
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import BlockAnchor, EvidenceBlock


# =============================================================================
# PDF Layout Helpers
# =============================================================================

def _detect_column_boundary(text_blocks: list, page_width: float) -> Optional[float]:
    """Return x split point if page is multi-column, else None.

    Uses gap detection: if there is a significant horizontal gap between
    blocks in the left half and right half, treats as two-column layout.
    """
    if not text_blocks or page_width <= 0:
        return None

    # Collect x-ranges of all text blocks
    x0_vals = [b[0] for b in text_blocks]
    x1_vals = [b[2] for b in text_blocks]

    left_blocks  = [b for b in text_blocks if b[0] < page_width * 0.45]
    right_blocks = [b for b in text_blocks if b[0] >= page_width * 0.45]

    if not left_blocks or not right_blocks:
        return None

    # Detect gap: max right-edge of left blocks vs min left-edge of right blocks
    left_max_x1  = max(b[2] for b in left_blocks)
    right_min_x0 = min(b[0] for b in right_blocks)
    gap = right_min_x0 - left_max_x1

    # Require gap > 3% of page width to call it multi-column
    if gap > page_width * 0.03:
        return (left_max_x1 + right_min_x0) / 2.0

    return None


def _sort_reading_order(text_blocks: list, page_width: float) -> list:
    """Sort text blocks in correct reading order.

    For multi-column pages: left column top→bottom, then right column.
    For single-column: top→bottom, left→right.
    """
    if not text_blocks:
        return []

    split_x = _detect_column_boundary(text_blocks, page_width)

    if split_x is not None:
        left  = sorted([b for b in text_blocks if b[0] < split_x],  key=lambda b: (b[1], b[0]))
        right = sorted([b for b in text_blocks if b[0] >= split_x], key=lambda b: (b[1], b[0]))
        return left + right

    # Single column — sort top-to-bottom with minor x tie-break
    return sorted(text_blocks, key=lambda b: (round(b[1] / 4) * 4, b[0]))


def _fitz_extract_tables(page) -> List[Tuple[tuple, str]]:
    """Extract tables from a PyMuPDF page using find_tables() (1.23+).

    Returns list of (bbox, formatted_text) pairs.
    """
    results = []
    try:
        finder = page.find_tables()
        for tbl in finder.tables:
            rows = tbl.extract()
            if not rows:
                continue
            lines = []
            for row in rows:
                cells = [str(c or "").strip().replace("\n", " ") for c in row]
                lines.append(" | ".join(cells))
            content = "\n".join(l for l in lines if l.strip())
            if content.strip():
                results.append((tbl.bbox, content))
    except Exception:
        pass
    return results


def _extract_figure_blocks(
    page,
    raw_id: str,
    page_num: int,
    page_count: int,
    table_bboxes: list,
    min_area_fraction: float = 0.005,
) -> list:
    """Extract inline image/figure regions from a PDF page as block_type='figure' nodes.

    Uses PyMuPDF get_text('blocks') type=1 (image blocks) to detect inline figures
    on text pages. Each figure gets a spatial anchor with bbox coordinates.
    Excludes regions that overlap table bboxes.
    Only creates a node if the figure region is large enough (min_area_fraction of page).
    """
    results = []
    try:
        page_area = page.rect.width * page.rect.height
        if page_area <= 0:
            return results

        raw_blocks = page.get_text("blocks")
        for b in raw_blocks:
            if len(b) < 7:
                continue
            btype = b[6]
            if btype != 1:  # 1 = image block
                continue
            x0, y0, x1, y1 = b[0], b[1], b[2], b[3]
            bbox = (x0, y0, x1, y1)
            area = (x1 - x0) * (y1 - y0)
            if area < page_area * min_area_fraction:
                continue  # too small to be meaningful
            if any(_bbox_overlaps(bbox, tb) for tb in table_bboxes):
                continue  # skip image inside table region

            anchor = BlockAnchor(doc_type="pdf", page=page_num + 1)
            # Store spatial bbox in anchor_json via metadata
            block = EvidenceBlock.create(
                raw_id=raw_id,
                anchor=anchor,
                content=f"[FIGURE: page {page_num + 1}, region ({int(x0)},{int(y0)})-({int(x1)},{int(y1)})]",
                block_type="figure",
                confidence=0.8,
                metadata={
                    "page_count": page_count,
                    "bbox_x0": round(x0, 2),
                    "bbox_y0": round(y0, 2),
                    "bbox_x1": round(x1, 2),
                    "bbox_y1": round(y1, 2),
                    "area_fraction": round(area / page_area, 4),
                },
            )
            results.append(block)
    except Exception:
        pass
    return results


def _bbox_overlaps(b1: tuple, b2: tuple, tolerance: float = 2.0) -> bool:
    """Check if two (x0,y0,x1,y1) bounding boxes overlap."""
    x0a, y0a, x1a, y1a = b1
    x0b, y0b, x1b, y1b = b2
    return not (x1a + tolerance < x0b or x1b + tolerance < x0a or
                y1a + tolerance < y0b or y1b + tolerance < y0a)


# =============================================================================
# PDF Extraction
# =============================================================================

def extract_pdf_blocks(
    file_bytes: bytes,
    raw_id: str,
    *,
    settings: Optional[dict] = None,
) -> list[EvidenceBlock]:
    """Extract blocks from PDF with full layout support.

    Features:
    - Multi-column reading order (scientific papers, reports)
    - Table extraction via find_tables() with per-cell anchors
    - Scanned page OCR fallback per page
    - pdfplumber fallback for complex PDFs
    """
    settings = settings or {}
    blocks: list[EvidenceBlock] = []

    try:
        import fitz

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page_count = len(doc)

        for page_num in range(page_count):
            page = doc[page_num]
            page_width = page.rect.width

            # ── Extract tables first (get their bboxes to exclude from text) ──
            table_results = _fitz_extract_tables(page)
            table_bboxes = [bbox for bbox, _ in table_results]

            for tbl_idx, (bbox, table_text) in enumerate(table_results):
                anchor = BlockAnchor(doc_type="pdf", page=page_num + 1)
                blocks.append(EvidenceBlock.create(
                    raw_id=raw_id,
                    anchor=anchor,
                    content=table_text,
                    block_type="table",
                    confidence=1.0,
                    metadata={"page_count": page_count, "table_index": tbl_idx},
                ))

            # ── Extract inline figure blocks (type=1 in get_text rawdict) ──
            # These are embedded image regions within text pages — not OCR candidates.
            figure_blocks = _extract_figure_blocks(
                page=page,
                raw_id=raw_id,
                page_num=page_num,
                page_count=page_count,
                table_bboxes=table_bboxes,
            )
            blocks.extend(figure_blocks)
            figure_bboxes = [fb.anchor_json.get("bbox_x0") and
                             (fb.anchor_json.get("bbox_x0", 0),
                              fb.anchor_json.get("bbox_y0", 0),
                              fb.anchor_json.get("bbox_x1", 0),
                              fb.anchor_json.get("bbox_y1", 0))
                             for fb in figure_blocks]
            figure_bboxes = [b for b in figure_bboxes if b]

            # ── Extract text blocks with layout-aware ordering ──
            raw_blocks = page.get_text("blocks")  # (x0,y0,x1,y1,text,block_no,type)
            text_blocks = [
                b for b in raw_blocks
                if len(b) >= 5 and b[4].strip()
                and b[6] == 0  # type 0 = text (type 1 = image)
                and not any(_bbox_overlaps(b[:4], tb) for tb in table_bboxes)
                and not any(_bbox_overlaps(b[:4], fb) for fb in figure_bboxes)
            ]

            ordered = _sort_reading_order(text_blocks, page_width)
            page_text = "\n".join(b[4].strip() for b in ordered if b[4].strip())

            if page_text.strip():
                anchor = BlockAnchor(doc_type="pdf", page=page_num + 1)
                blocks.append(EvidenceBlock.create(
                    raw_id=raw_id,
                    anchor=anchor,
                    content=page_text.strip(),
                    block_type="text",
                    confidence=1.0,
                    metadata={"page_count": page_count},
                ))
            elif page.get_images():
                # Pure image page — attempt OCR
                ocr_block = _extract_pdf_page_ocr_block(
                    page=page,
                    raw_id=raw_id,
                    page_number=page_num + 1,
                    page_count=page_count,
                    image_count=len(page.get_images()),
                )
                if ocr_block is not None:
                    blocks.append(ocr_block)
                else:
                    anchor = BlockAnchor(doc_type="pdf", page=page_num + 1)
                    blocks.append(_image_stub_block(
                        raw_id=raw_id,
                        anchor=anchor,
                        message="[IMAGE_STUB: Page contains image content requiring OCR]",
                        filename="",
                        size_bytes=len(file_bytes),
                        metadata={
                            "page_count": page_count,
                            "image_count": len(page.get_images()),
                            "ocr_pending": True,
                        },
                    ))

        doc.close()
        if blocks:
            return blocks

    except ImportError:
        pass
    except Exception:
        pass

    # ── pdfplumber fallback ──────────────────────────────────────────────────
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                # Tables
                for tbl_idx, table in enumerate(page.extract_tables() or []):
                    lines = [
                        " | ".join(str(c or "").strip() for c in row)
                        for row in table
                    ]
                    content = "\n".join(l for l in lines if l.strip())
                    if content.strip():
                        anchor = BlockAnchor(doc_type="pdf", page=i + 1)
                        blocks.append(EvidenceBlock.create(
                            raw_id=raw_id,
                            anchor=anchor,
                            content=content,
                            block_type="table",
                            confidence=1.0,
                            metadata={"table_index": tbl_idx},
                        ))

                # Text
                page_text = page.extract_text() or ""
                if page_text.strip():
                    anchor = BlockAnchor(doc_type="pdf", page=i + 1)
                    blocks.append(EvidenceBlock.create(
                        raw_id=raw_id,
                        anchor=anchor,
                        content=page_text.strip(),
                        block_type="text",
                        confidence=1.0,
                    ))

        if blocks:
            return blocks

    except ImportError:
        pass
    except Exception:
        pass

    # ── pypdf last resort ────────────────────────────────────────────────────
    try:
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                anchor = BlockAnchor(doc_type="pdf", page=i + 1)
                blocks.append(EvidenceBlock.create(
                    raw_id=raw_id,
                    anchor=anchor,
                    content=page_text.strip(),
                    block_type="text",
                    confidence=1.0,
                ))

        if blocks:
            return blocks

    except Exception:
        pass

    anchor = BlockAnchor(doc_type="pdf", page=1)
    return [EvidenceBlock.create(
        raw_id=raw_id,
        anchor=anchor,
        content="[EXTRACTION_FAILED: Could not extract PDF content]",
        block_type="text",
        confidence=0.0,
    )]


# =============================================================================
# DOCX Extraction
# =============================================================================

def extract_docx_blocks(
    file_bytes: bytes,
    raw_id: str,
    *,
    settings: Optional[dict] = None,
) -> list[EvidenceBlock]:
    """Extract blocks from DOCX with heading hierarchy and table extraction."""
    blocks: list[EvidenceBlock] = []
    char_offset = 0

    try:
        from docx import Document
        from docx.oxml.ns import qn

        doc = Document(io.BytesIO(file_bytes))

        # Track current heading section for anchor
        current_section: Optional[str] = None

        for para_idx, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if not text:
                continue

            style_name = para.style.name if para.style else ""
            is_heading = "heading" in style_name.lower()

            if is_heading:
                current_section = text

            block_type = "heading" if is_heading else "text"
            anchor = BlockAnchor(
                doc_type="docx",
                char_start=char_offset,
                char_end=char_offset + len(text),
                section=current_section,
            )

            blocks.append(EvidenceBlock.create(
                raw_id=raw_id,
                anchor=anchor,
                content=text,
                block_type=block_type,
                confidence=1.0,
                metadata={"paragraph_index": para_idx, "style": style_name},
            ))
            char_offset += len(text) + 1

        # Tables
        for tbl_idx, table in enumerate(doc.tables):
            rows_data = []
            for row_idx, row in enumerate(table.rows):
                cells = [cell.text.strip() for cell in row.cells]
                # Detect header row (first row or all-bold cells)
                rows_data.append(cells)

            if not rows_data:
                continue

            # Format: header row with separator if first row looks like headers
            lines = []
            for row_idx, cells in enumerate(rows_data):
                lines.append(" | ".join(cells))
                if row_idx == 0 and len(rows_data) > 1:
                    lines.append("-" * max(10, len(lines[0])))

            content = "\n".join(l for l in lines if l.replace("|", "").replace("-", "").strip())
            if content.strip():
                anchor = BlockAnchor(
                    doc_type="docx",
                    char_start=char_offset,
                    char_end=char_offset + len(content),
                    section=current_section,
                )
                blocks.append(EvidenceBlock.create(
                    raw_id=raw_id,
                    anchor=anchor,
                    content=content,
                    block_type="table",
                    confidence=1.0,
                    metadata={"table_index": tbl_idx, "rows": len(rows_data)},
                ))
                char_offset += len(content) + 1

        return blocks if blocks else [_fallback_block(raw_id, "docx")]

    except ImportError:
        pass
    except Exception:
        pass

    return [_fallback_block(raw_id, "docx")]


# =============================================================================
# PPTX Extraction
# =============================================================================

def extract_pptx_blocks(
    file_bytes: bytes,
    raw_id: str,
    *,
    settings: Optional[dict] = None,
) -> list[EvidenceBlock]:
    """Extract blocks from PPTX with shape ordering, tables, and speaker notes."""
    blocks: list[EvidenceBlock] = []

    try:
        from pptx import Presentation
        from pptx.util import Pt
        from pptx.enum.shapes import MSO_SHAPE_TYPE

        prs = Presentation(io.BytesIO(file_bytes))

        for slide_num, slide in enumerate(prs.slides, 1):
            # Sort shapes top-to-bottom, left-to-right by position
            def shape_sort_key(s):
                try:
                    return (s.top or 0, s.left or 0)
                except Exception:
                    return (0, 0)

            sorted_shapes = sorted(slide.shapes, key=shape_sort_key)

            slide_texts: list[str] = []
            slide_tables: list[str] = []

            for shape in sorted_shapes:
                # Text frames
                if shape.has_text_frame:
                    text = "\n".join(
                        p.text.strip()
                        for p in shape.text_frame.paragraphs
                        if p.text.strip()
                    )
                    if text:
                        slide_texts.append(text)

                # Tables inside slides
                if shape.has_table:
                    table = shape.table
                    lines = []
                    for row_idx, row in enumerate(table.rows):
                        cells = [cell.text.strip() for cell in row.cells]
                        lines.append(" | ".join(cells))
                        if row_idx == 0 and len(table.rows) > 1:
                            lines.append("-" * max(10, len(lines[0])))
                    tbl_content = "\n".join(l for l in lines if l.replace("|", "").replace("-", "").strip())
                    if tbl_content:
                        slide_tables.append(tbl_content)

            if slide_texts:
                anchor = BlockAnchor(doc_type="pptx", slide=slide_num)
                blocks.append(EvidenceBlock.create(
                    raw_id=raw_id,
                    anchor=anchor,
                    content="\n".join(slide_texts),
                    block_type="text",
                    confidence=1.0,
                    metadata={"slide_count": len(prs.slides)},
                ))

            for tbl_idx, tbl_text in enumerate(slide_tables):
                anchor = BlockAnchor(doc_type="pptx", slide=slide_num)
                blocks.append(EvidenceBlock.create(
                    raw_id=raw_id,
                    anchor=anchor,
                    content=tbl_text,
                    block_type="table",
                    confidence=1.0,
                    metadata={"slide_count": len(prs.slides), "table_index": tbl_idx},
                ))

            # Speaker notes
            try:
                notes_frame = slide.notes_slide.notes_text_frame
                notes_text = notes_frame.text.strip() if notes_frame else ""
                if notes_text:
                    anchor = BlockAnchor(doc_type="pptx", slide=slide_num)
                    blocks.append(EvidenceBlock.create(
                        raw_id=raw_id,
                        anchor=anchor,
                        content=notes_text,
                        block_type="text",
                        confidence=1.0,
                        metadata={"slide_notes": True},
                    ))
            except Exception:
                pass

        return blocks if blocks else [_fallback_block(raw_id, "pptx")]

    except ImportError:
        pass
    except Exception:
        pass

    return [_fallback_block(raw_id, "pptx")]


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
    """Extract blocks from XLSX/CSV with header detection and sheet anchors."""
    blocks: list[EvidenceBlock] = []
    ext = Path(filename).suffix.lower() if filename else ""

    def _format_rows(rows_data: list, has_header: bool) -> list[str]:
        lines = []
        for row_idx, cells in enumerate(rows_data):
            line = " | ".join(str(c).strip() if c is not None else "" for c in cells)
            lines.append(line)
            if row_idx == 0 and has_header and len(rows_data) > 1:
                lines.append("-" * max(10, len(line)))
        return [l for l in lines if l.replace("|", "").replace("-", "").strip()]

    def _looks_like_header(row: list) -> bool:
        if not row:
            return False
        text_cells = sum(1 for c in row if c is not None and isinstance(c, str) and c.strip())
        return text_cells >= len(row) * 0.6

    # CSV
    if ext == ".csv":
        try:
            import csv
            text = file_bytes.decode("utf-8", errors="ignore")
            reader = csv.reader(io.StringIO(text))
            rows = list(reader)
            has_header = _looks_like_header(rows[0]) if rows else False
            ROWS_PER_BLOCK = 50

            for start in range(0, len(rows), ROWS_PER_BLOCK):
                chunk = rows[start:start + ROWS_PER_BLOCK]
                lines = _format_rows(chunk, has_header=(has_header and start == 0))
                content = "\n".join(lines)
                if content.strip():
                    anchor = BlockAnchor(
                        doc_type="xlsx", sheet="Sheet1",
                        row_start=start + 1, row_end=start + len(chunk),
                    )
                    blocks.append(EvidenceBlock.create(
                        raw_id=raw_id, anchor=anchor, content=content,
                        block_type="table", confidence=1.0,
                        metadata={"total_rows": len(rows), "has_header": has_header},
                    ))
            return blocks if blocks else [_fallback_block(raw_id, "xlsx")]
        except Exception:
            pass

    # XLSX
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)

        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            rows_data = [list(row) for row in sheet.iter_rows(values_only=True)]
            if not rows_data:
                continue

            has_header = _looks_like_header(rows_data[0])
            ROWS_PER_BLOCK = 50

            for start in range(0, len(rows_data), ROWS_PER_BLOCK):
                chunk = rows_data[start:start + ROWS_PER_BLOCK]
                lines = _format_rows(chunk, has_header=(has_header and start == 0))
                content = "\n".join(lines)
                if content.strip():
                    anchor = BlockAnchor(
                        doc_type="xlsx", sheet=sheet_name,
                        row_start=start + 1, row_end=start + len(chunk),
                    )
                    blocks.append(EvidenceBlock.create(
                        raw_id=raw_id, anchor=anchor, content=content,
                        block_type="table", confidence=1.0,
                        metadata={
                            "sheet": sheet_name,
                            "total_rows": len(rows_data),
                            "has_header": has_header,
                        },
                    ))

        wb.close()
        return blocks if blocks else [_fallback_block(raw_id, "xlsx")]

    except ImportError:
        pass
    except Exception:
        pass

    return [_fallback_block(raw_id, "xlsx")]


# =============================================================================
# Text/Code/Markdown Extraction
# =============================================================================

def extract_text_blocks(
    file_bytes: bytes,
    raw_id: str,
    *,
    filename: str = "",
    settings: Optional[dict] = None,
) -> list[EvidenceBlock]:
    """Extract blocks from text/code files."""
    text = None
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            text = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        text = file_bytes.decode("utf-8", errors="ignore")

    text = text.replace("\x00", "")
    if not text.strip():
        return [_fallback_block(raw_id, "text")]

    ext = Path(filename).suffix.lower() if filename else ""
    if ext in (".md", ".markdown", ".rst"):
        return _extract_markdown_blocks(text, raw_id)

    blocks: list[EvidenceBlock] = []
    CODE_EXTS = {".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp",
                 ".h", ".cs", ".rb", ".php", ".swift", ".kt", ".scala", ".sh", ".sql"}

    if len(text) < 5000:
        anchor = BlockAnchor(doc_type="text", char_start=0, char_end=len(text))
        blocks.append(EvidenceBlock.create(
            raw_id=raw_id, anchor=anchor, content=text,
            block_type="code" if ext in CODE_EXTS else "text",
            confidence=1.0,
        ))
    else:
        BLOCK_SIZE = 2000
        paragraphs = text.split("\n\n")
        current: list[str] = []
        current_size = 0
        char_start = 0

        for para in paragraphs:
            if current_size + len(para) > BLOCK_SIZE and current:
                content = "\n\n".join(current)
                anchor = BlockAnchor(doc_type="text", char_start=char_start, char_end=char_start + len(content))
                blocks.append(EvidenceBlock.create(
                    raw_id=raw_id, anchor=anchor, content=content,
                    block_type="text", confidence=1.0,
                ))
                char_start += len(content) + 2
                current, current_size = [], 0
            current.append(para)
            current_size += len(para) + 2

        if current:
            content = "\n\n".join(current)
            anchor = BlockAnchor(doc_type="text", char_start=char_start, char_end=char_start + len(content))
            blocks.append(EvidenceBlock.create(
                raw_id=raw_id, anchor=anchor, content=content,
                block_type="text", confidence=1.0,
            ))

    return blocks if blocks else [_fallback_block(raw_id, "text")]


def _extract_markdown_blocks(text: str, raw_id: str) -> list[EvidenceBlock]:
    """Extract markdown with section-level blocks."""
    blocks: list[EvidenceBlock] = []
    lines = text.split("\n")
    current_section = "Introduction"
    current_lines: list[str] = []
    char_start = 0

    def _flush(section: str, content_lines: list[str], offset: int) -> Optional[EvidenceBlock]:
        content = "\n".join(content_lines).strip()
        if not content:
            return None
        anchor = BlockAnchor(
            doc_type="text", char_start=offset,
            char_end=offset + len(content), section=section,
        )
        return EvidenceBlock.create(
            raw_id=raw_id, anchor=anchor, content=content,
            block_type="heading" if section != "Introduction" else "text",
            confidence=1.0,
        )

    for line in lines:
        if line.startswith("#"):
            block = _flush(current_section, current_lines, char_start)
            if block:
                blocks.append(block)
                char_start += len("\n".join(current_lines)) + 1
            current_section = line.lstrip("#").strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    block = _flush(current_section, current_lines, char_start)
    if block:
        blocks.append(block)

    return blocks if blocks else [_fallback_block(raw_id, "text")]


# =============================================================================
# Image / OCR
# =============================================================================

def extract_image_stub(
    file_bytes: bytes,
    raw_id: str,
    *,
    filename: str = "",
) -> list[EvidenceBlock]:
    """Extract image content via OCR when enabled, else stub block."""
    anchor = BlockAnchor(doc_type="image", page=1)
    ocr_error: Optional[str] = None

    try:
        try:
            from perception.extract.ocr_service import (
                OCRProcessingError, OCRUnavailableError,
                extract_text_from_image_bytes, get_ocr_settings,
            )
        except ImportError:
            from .ocr_service import (
                OCRProcessingError, OCRUnavailableError,
                extract_text_from_image_bytes, get_ocr_settings,
            )

        settings = get_ocr_settings()
        ocr_result = extract_text_from_image_bytes(
            file_bytes, source="image_upload",
            filename=filename, settings=settings,
        )
        if ocr_result is not None:
            metadata = dict(ocr_result.metadata or {})
            metadata.setdefault("size_bytes", len(file_bytes))
            return [EvidenceBlock.create(
                raw_id=raw_id, anchor=anchor,
                content=ocr_result.text, block_type="text",
                confidence=max(0.2, min(1.0, float(ocr_result.confidence))),
                metadata=metadata,
            )]
    except Exception as exc:
        ocr_error = str(exc)

    return [_image_stub_block(
        raw_id=raw_id, anchor=anchor,
        message=f"[IMAGE_STUB: {filename or 'image'} requires OCR processing]",
        filename=filename, size_bytes=len(file_bytes),
        metadata={"ocr_pending": True, "ocr_error": ocr_error},
    )]


# =============================================================================
# Helpers
# =============================================================================

def _fallback_block(raw_id: str, doc_type: str) -> EvidenceBlock:
    anchor = BlockAnchor(doc_type=doc_type, char_start=0, char_end=0)
    return EvidenceBlock.create(
        raw_id=raw_id, anchor=anchor,
        content="[EXTRACTION_FAILED: Could not extract content]",
        block_type="text", confidence=0.0,
    )


def _extract_pdf_page_ocr_block(
    *,
    page: object,
    raw_id: str,
    page_number: int,
    page_count: int,
    image_count: int,
) -> Optional[EvidenceBlock]:
    """Run OCR on an image-only PDF page."""
    try:
        try:
            from perception.extract.ocr_service import (
                OCRProcessingError, OCRUnavailableError,
                extract_text_from_pdf_page, get_ocr_settings,
            )
        except ImportError:
            from .ocr_service import (
                OCRProcessingError, OCRUnavailableError,
                extract_text_from_pdf_page, get_ocr_settings,
            )

        settings = get_ocr_settings()
        ocr_result = extract_text_from_pdf_page(page, page_number=page_number, settings=settings)
        if ocr_result is None:
            return None

        anchor = BlockAnchor(doc_type="pdf", page=page_number)
        metadata = {"page_count": page_count, "image_count": image_count, "ocr_pending": False}
        metadata.update(ocr_result.metadata or {})
        return EvidenceBlock.create(
            raw_id=raw_id, anchor=anchor,
            content=ocr_result.text, block_type="text",
            confidence=max(0.2, min(1.0, float(ocr_result.confidence))),
            metadata=metadata,
        )
    except Exception:
        return None


def _image_stub_block(
    *,
    raw_id: str,
    anchor: BlockAnchor,
    message: str,
    filename: str,
    size_bytes: int,
    metadata: Optional[dict] = None,
) -> EvidenceBlock:
    payload = {"filename": filename, "size_bytes": int(size_bytes)}
    if metadata:
        payload.update(metadata)
    return EvidenceBlock.create(
        raw_id=raw_id, anchor=anchor,
        content=message, block_type="image_stub",
        confidence=0.2, metadata=payload,
    )
