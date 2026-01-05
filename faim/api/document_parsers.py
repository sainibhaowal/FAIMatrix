"""
FAIM Document Parsers - Full Format Support

Extracts text content from all document formats for FAIM ingestion.
Supports: TXT, MD, JSON, PDF (with tables), DOCX, XLSX, PPTX, Code files

All extractors produce chunks with proper metadata for FAIM's
Fractal Antisymmetric Inheritance Memory system.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# =============================================================================
# MAIN EXTRACTOR
# =============================================================================

def extract_text(file_path: str, filename: str) -> Dict[str, Any]:
    """
    Extract text content from a file.
    Returns dict with: content, metadata, chunks (FAIM-ready)
    """
    ext = Path(filename).suffix.lower()
    
    extractors = {
        # Text formats
        ".txt": extract_text_file,
        ".md": extract_markdown_file,
        ".markdown": extract_markdown_file,
        # Data formats
        ".json": extract_json_file,
        ".csv": extract_csv_file,
        # PDF (enhanced with tables + OCR fallback)
        ".pdf": extract_pdf_with_ocr,
        # Office documents (modern)
        ".docx": extract_docx_file,
        ".xlsx": extract_xlsx_file,
        ".pptx": extract_pptx_file,
        # Office documents (legacy - with dedicated parsers)
        ".doc": extract_doc_legacy,
        ".xls": extract_xls_legacy,
        ".ppt": extract_ppt_legacy,
        # Code files
        ".py": extract_code_file,
        ".js": extract_code_file,
        ".ts": extract_code_file,
        ".jsx": extract_code_file,
        ".tsx": extract_code_file,
        ".go": extract_code_file,
        ".rs": extract_code_file,
        ".java": extract_code_file,
        ".c": extract_code_file,
        ".cpp": extract_code_file,
        ".h": extract_code_file,
        ".cs": extract_code_file,
        ".rb": extract_code_file,
        ".php": extract_code_file,
        ".swift": extract_code_file,
        ".kt": extract_code_file,
        ".scala": extract_code_file,
        ".sh": extract_code_file,
        ".bash": extract_code_file,
        ".sql": extract_code_file,
        ".yaml": extract_code_file,
        ".yml": extract_code_file,
        ".toml": extract_code_file,
        ".xml": extract_code_file,
        ".html": extract_code_file,
        ".css": extract_code_file,
        ".scss": extract_code_file,
        ".vue": extract_code_file,
        ".svelte": extract_code_file,
    }
    
    extractor = extractors.get(ext, extract_text_file)
    
    try:
        result = extractor(file_path, filename)
        # Add FAIM inheritance metadata
        result["faim_metadata"] = {
            "source_file": filename,
            "file_type": ext,
            "extraction_method": extractor.__name__,
            "chunk_count": len(result.get("chunks", [])),
        }
        return result
    except Exception as e:
        logger.error(f"Failed to extract content from {filename}: {e}")
        return {
            "content": f"[Extraction Error: {str(e)}]",
            "metadata": {"error": str(e), "filename": filename},
            "chunks": [],
            "file_type": ext,
        }


# =============================================================================
# TEXT EXTRACTORS
# =============================================================================

def extract_text_file(file_path: str, filename: str) -> Dict[str, Any]:
    """Extract plain text file."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    return {
        "content": content,
        "metadata": {"type": "text", "filename": filename, "char_count": len(content)},
        "chunks": chunk_text(content, source=filename),
        "file_type": "txt",
    }


def extract_markdown_file(file_path: str, filename: str) -> Dict[str, Any]:
    """Extract markdown file with section awareness."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    # Extract sections by headers (FAIM inheritance: sections are children)
    sections = []
    current_section = {"title": "Introduction", "level": 0, "content": ""}
    
    for line in content.split("\n"):
        if line.startswith("#"):
            if current_section["content"].strip():
                sections.append(current_section)
            level = len(line) - len(line.lstrip("#"))
            title = line.lstrip("#").strip()
            current_section = {"title": title, "level": level, "content": ""}
        else:
            current_section["content"] += line + "\n"
    
    if current_section["content"].strip():
        sections.append(current_section)
    
    # Create chunks with inheritance metadata
    chunks = []
    for i, section in enumerate(sections):
        if section["content"].strip():
            chunks.append({
                "content": section["content"].strip(),
                "metadata": {
                    "section": section["title"],
                    "section_level": section["level"],
                    "section_index": i,
                    "inheritance": f"section:{section['title']}",
                },
            })
    
    return {
        "content": content,
        "metadata": {"type": "markdown", "filename": filename, "sections": len(sections)},
        "chunks": chunks if chunks else chunk_text(content, source=filename),
        "file_type": "markdown",
    }


def extract_json_file(file_path: str, filename: str) -> Dict[str, Any]:
    """Extract JSON file with structure preservation."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    
    try:
        data = json.loads(raw)
        content = json.dumps(data, indent=2)
        keys = extract_json_keys(data)
        
        # Create chunks for large JSON objects
        chunks = []
        if isinstance(data, list):
            for i, item in enumerate(data[:50]):  # Limit to 50 items
                chunks.append({
                    "content": json.dumps(item, indent=2),
                    "metadata": {"item_index": i, "inheritance": "array_item"},
                })
        elif isinstance(data, dict):
            for key, value in list(data.items())[:30]:  # Limit to 30 keys
                chunks.append({
                    "content": f"{key}: {json.dumps(value, indent=2)}",
                    "metadata": {"key": key, "inheritance": f"object:{key}"},
                })
        
        if not chunks:
            chunks = chunk_text(content, source=filename)
        
        return {
            "content": content,
            "metadata": {"type": "json", "filename": filename, "keys": keys[:20]},
            "chunks": chunks,
            "file_type": "json",
        }
    except json.JSONDecodeError:
        return extract_text_file(file_path, filename)


def extract_csv_file(file_path: str, filename: str) -> Dict[str, Any]:
    """Extract CSV file with row awareness."""
    import csv
    
    rows = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        headers = next(reader, [])
        for row in reader:
            rows.append(row)
    
    # Create content representation
    content = f"Headers: {', '.join(headers)}\n"
    content += f"Rows: {len(rows)}\n\n"
    for i, row in enumerate(rows[:100]):  # Limit preview
        content += f"Row {i+1}: {', '.join(row)}\n"
    
    # Create chunks per row (with header context)
    chunks = []
    for i, row in enumerate(rows[:200]):  # Limit to 200 rows
        row_dict = {h: v for h, v in zip(headers, row, strict=False) if v}
        chunks.append({
            "content": json.dumps(row_dict),
            "metadata": {"row_index": i, "inheritance": "csv_row"},
        })
    
    return {
        "content": content,
        "metadata": {"type": "csv", "filename": filename, "headers": headers, "row_count": len(rows)},
        "chunks": chunks if chunks else chunk_text(content, source=filename),
        "file_type": "csv",
    }


def extract_json_keys(obj, prefix="") -> List[str]:
    """Recursively extract JSON keys."""
    keys = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            keys.append(path)
            keys.extend(extract_json_keys(v, path))
    elif isinstance(obj, list) and obj:
        keys.extend(extract_json_keys(obj[0], f"{prefix}[]"))
    return keys[:50]


# =============================================================================
# PDF EXTRACTOR (ENHANCED WITH TABLES + OCR FALLBACK)
# =============================================================================

def extract_pdf_with_ocr(file_path: str, filename: str) -> Dict[str, Any]:
    """
    Extract PDF with full support:
    - Text extraction (pdfplumber)
    - Table extraction
    - OCR fallback for image-only/scanned pages (pytesseract)
    - Page-level chunks with FAIM inheritance
    """
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed, falling back to basic PDF extraction")
        return extract_pdf_basic(file_path, filename)
    
    pages_data = []
    full_text = ""
    total_tables = 0
    ocr_used = False
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                page_text = page.extract_text() or ""
                
                # Extract tables
                tables = page.extract_tables() or []
                table_text = ""
                for t_idx, table in enumerate(tables):
                    total_tables += 1
                    table_text += f"\n[Table {t_idx+1}]\n"
                    for row in table:
                        table_text += " | ".join(str(cell or "") for cell in row) + "\n"
                
                combined = page_text + table_text
                
                # OCR fallback if page has little/no text (likely scanned or image)
                if len(combined.strip()) < 50:
                    ocr_text = extract_page_with_ocr(file_path, page_num)
                    if ocr_text:
                        combined = ocr_text
                        ocr_used = True
                
                pages_data.append({
                    "page": page_num,
                    "content": combined,
                    "has_tables": len(tables) > 0,
                    "table_count": len(tables),
                    "ocr_used": len(combined.strip()) < 50,
                })
                full_text += f"\n--- Page {page_num} ---\n{combined}"
        
        # Create page-level chunks with FAIM inheritance
        chunks = []
        for page in pages_data:
            if page["content"].strip():
                chunks.append({
                    "content": page["content"].strip(),
                    "metadata": {
                        "page": page["page"],
                        "has_tables": page["has_tables"],
                        "ocr_used": page.get("ocr_used", False),
                        "inheritance": f"page:{page['page']}",
                    },
                })
        
        return {
            "content": full_text.strip(),
            "metadata": {
                "type": "pdf",
                "filename": filename,
                "pages": len(pages_data),
                "tables": total_tables,
                "ocr_used": ocr_used,
            },
            "chunks": chunks if chunks else chunk_text(full_text, source=filename),
            "file_type": "pdf",
        }
        
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return extract_pdf_basic(file_path, filename)


def extract_page_with_ocr(pdf_path: str, page_num: int) -> str:
    """
    Extract text from a specific PDF page using OCR.
    Requires: pytesseract, pdf2image, Pillow
    """
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        logger.warning("OCR dependencies (pdf2image, pytesseract) not installed")
        return ""
    
    try:
        # Convert specific page to image
        images = convert_from_path(
            pdf_path,
            first_page=page_num,
            last_page=page_num,
            dpi=300  # High DPI for better OCR
        )
        
        if not images:
            return ""
        
        # Run OCR on the page image
        text = pytesseract.image_to_string(images[0], lang='eng')
        logger.info(f"OCR extracted {len(text)} chars from page {page_num}")
        return text
        
    except Exception as e:
        logger.warning(f"OCR failed for page {page_num}: {e}")
        return ""


def extract_pdf_basic(file_path: str, filename: str) -> Dict[str, Any]:
    """Basic PDF extraction using pypdf."""
    try:
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
        
        reader = PdfReader(file_path)
        pages = []
        full_text = ""
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages.append({"page": i + 1, "content": text})
            full_text += f"\n--- Page {i + 1} ---\n{text}"
        
        chunks = []
        for page in pages:
            if page["content"].strip():
                chunks.append({
                    "content": page["content"].strip(),
                    "metadata": {"page": page["page"], "inheritance": f"page:{page['page']}"},
                })
        
        return {
            "content": full_text.strip(),
            "metadata": {"type": "pdf", "filename": filename, "pages": len(pages)},
            "chunks": chunks if chunks else chunk_text(full_text, source=filename),
            "file_type": "pdf",
        }
        
    except Exception as e:
        return {
            "content": f"[PDF Error: {str(e)}]",
            "metadata": {"type": "pdf", "filename": filename, "error": str(e)},
            "chunks": [],
            "file_type": "pdf",
        }

# =============================================================================
# LEGACY OFFICE FORMAT EXTRACTORS (.doc, .xls, .ppt)
# =============================================================================

def extract_doc_legacy(file_path: str, filename: str) -> Dict[str, Any]:
    """
    Extract legacy .doc files (Word 97-2003).
    Uses antiword command-line tool or textract as fallback.
    """
    import subprocess
    
    content = ""
    method = "unknown"
    
    # Try antiword first (system command)
    try:
        result = subprocess.run(
            ["antiword", file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            content = result.stdout
            method = "antiword"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Try catdoc as fallback
    if not content:
        try:
            result = subprocess.run(
                ["catdoc", file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                content = result.stdout
                method = "catdoc"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    # Try textract as fallback
    if not content:
        try:
            import textract
            content = textract.process(file_path).decode('utf-8', errors='ignore')
            method = "textract"
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"textract failed: {e}")
    
    if not content:
        return {
            "content": "[DOC extraction requires: sudo apt-get install antiword catdoc OR pip install textract]",
            "metadata": {"type": "doc", "filename": filename, "error": "No .doc parser available"},
            "chunks": [],
            "file_type": "doc",
        }
    
    return {
        "content": content,
        "metadata": {"type": "doc", "filename": filename, "method": method},
        "chunks": chunk_text(content, source=filename),
        "file_type": "doc",
    }


def extract_xls_legacy(file_path: str, filename: str) -> Dict[str, Any]:
    """
    Extract legacy .xls files (Excel 97-2003).
    Uses xlrd library.
    """
    try:
        import xlrd
    except ImportError:
        return {
            "content": "[XLS Support Requires: pip install xlrd]",
            "metadata": {"type": "xls", "filename": filename, "error": "xlrd not installed"},
            "chunks": [],
            "file_type": "xls",
        }
    
    try:
        wb = xlrd.open_workbook(file_path)
        
        sheets_data = []
        full_content = ""
        
        for sheet_name in wb.sheet_names():
            sheet = wb.sheet_by_name(sheet_name)
            
            # Extract headers (first row)
            headers = []
            rows_data = []
            
            for row_idx in range(sheet.nrows):
                row = [str(sheet.cell_value(row_idx, col_idx)) for col_idx in range(sheet.ncols)]
                if row_idx == 0:
                    headers = row
                else:
                    row_dict = {h: v for h, v in zip(headers, row, strict=False) if v}
                    if any(row_dict.values()):
                        rows_data.append(row_dict)
            
            sheet_content = f"\n=== Sheet: {sheet_name} ===\n"
            sheet_content += f"Headers: {', '.join(headers)}\n"
            sheet_content += f"Rows: {len(rows_data)}\n\n"
            
            for i, row in enumerate(rows_data[:50]):
                sheet_content += f"Row {i+1}: {json.dumps(row)}\n"
            
            sheets_data.append({
                "name": sheet_name,
                "headers": headers,
                "rows": rows_data,
                "content": sheet_content,
            })
            full_content += sheet_content
        
        # Create chunks per sheet
        chunks = []
        for sheet in sheets_data:
            if len(sheet["rows"]) <= 20:
                chunks.append({
                    "content": sheet["content"],
                    "metadata": {
                        "sheet": sheet["name"],
                        "row_count": len(sheet["rows"]),
                        "inheritance": f"sheet:{sheet['name']}",
                    },
                })
            else:
                for i, row in enumerate(sheet["rows"][:100]):
                    chunks.append({
                        "content": json.dumps(row),
                        "metadata": {
                            "sheet": sheet["name"],
                            "row_index": i,
                            "inheritance": f"sheet:{sheet['name']}:row:{i}",
                        },
                    })
        
        return {
            "content": full_content,
            "metadata": {
                "type": "xls",
                "filename": filename,
                "sheets": len(sheets_data),
                "total_rows": sum(len(s["rows"]) for s in sheets_data),
            },
            "chunks": chunks if chunks else chunk_text(full_content, source=filename),
            "file_type": "xls",
        }
        
    except Exception as e:
        logger.error(f"XLS extraction failed: {e}")
        return {
            "content": f"[XLS Error: {str(e)}]",
            "metadata": {"type": "xls", "filename": filename, "error": str(e)},
            "chunks": [],
            "file_type": "xls",
        }


def extract_ppt_legacy(file_path: str, filename: str) -> Dict[str, Any]:
    """
    Extract legacy .ppt files (PowerPoint 97-2003).
    Uses catppt command-line tool or textract as fallback.
    """
    import subprocess
    
    content = ""
    method = "unknown"
    
    # Try catppt first (from catdoc package)
    try:
        result = subprocess.run(
            ["catppt", file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            content = result.stdout
            method = "catppt"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Try textract as fallback
    if not content:
        try:
            import textract
            content = textract.process(file_path).decode('utf-8', errors='ignore')
            method = "textract"
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"textract failed for PPT: {e}")
    
    if not content:
        return {
            "content": "[PPT extraction requires: sudo apt-get install catdoc OR pip install textract]",
            "metadata": {"type": "ppt", "filename": filename, "error": "No .ppt parser available"},
            "chunks": [],
            "file_type": "ppt",
        }
    
    # Parse slides from content (catppt creates slide markers)
    slides = []
    current_slide = {"num": 1, "content": ""}
    
    for line in content.split("\n"):
        if line.startswith("Slide ") and line.strip().endswith(":"):
            if current_slide["content"].strip():
                slides.append(current_slide)
            try:
                slide_num = int(line.replace("Slide ", "").replace(":", "").strip())
                current_slide = {"num": slide_num, "content": ""}
            except ValueError:
                current_slide["content"] += line + "\n"
        else:
            current_slide["content"] += line + "\n"
    
    if current_slide["content"].strip():
        slides.append(current_slide)
    
    # Create chunks per slide
    chunks = []
    for slide in slides:
        if slide["content"].strip():
            chunks.append({
                "content": slide["content"].strip(),
                "metadata": {
                    "slide": slide["num"],
                    "inheritance": f"slide:{slide['num']}",
                },
            })
    
    return {
        "content": content,
        "metadata": {"type": "ppt", "filename": filename, "method": method, "slides": len(slides)},
        "chunks": chunks if chunks else chunk_text(content, source=filename),
        "file_type": "ppt",
    }


# =============================================================================
# OFFICE DOCUMENT EXTRACTORS
# =============================================================================

def extract_docx_file(file_path: str, filename: str) -> Dict[str, Any]:
    """
    Extract DOCX with structure:
    - Paragraphs
    - Tables
    - Headers/Styles
    """
    try:
        from docx import Document
    except ImportError:
        return {
            "content": "[DOCX Support Requires: pip install python-docx]",
            "metadata": {"type": "docx", "filename": filename, "error": "python-docx not installed"},
            "chunks": [],
            "file_type": "docx",
        }
    
    try:
        doc = Document(file_path)
        
        # Extract paragraphs
        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                style = para.style.name if para.style else "Normal"
                paragraphs.append({
                    "text": para.text,
                    "style": style,
                    "is_heading": "Heading" in style,
                })
        
        # Extract tables
        tables_text = []
        for t_idx, table in enumerate(doc.tables):
            table_content = f"\n[Table {t_idx+1}]\n"
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells)
                table_content += row_text + "\n"
            tables_text.append(table_content)
        
        # Build full content
        content = "\n\n".join(p["text"] for p in paragraphs)
        content += "\n" + "\n".join(tables_text)
        
        # Create chunks with inheritance (group by headings)
        chunks = []
        current_section = None
        section_content = []
        
        for p in paragraphs:
            if p["is_heading"]:
                # Save previous section
                if section_content:
                    chunks.append({
                        "content": "\n".join(section_content),
                        "metadata": {
                            "section": current_section or "Introduction",
                            "inheritance": f"section:{current_section or 'intro'}",
                        },
                    })
                current_section = p["text"]
                section_content = [p["text"]]
            else:
                section_content.append(p["text"])
        
        # Don't forget last section
        if section_content:
            chunks.append({
                "content": "\n".join(section_content),
                "metadata": {
                    "section": current_section or "Content",
                    "inheritance": f"section:{current_section or 'content'}",
                },
            })
        
        # Add tables as separate chunks
        for t_idx, table in enumerate(tables_text):
            chunks.append({
                "content": table,
                "metadata": {"table_index": t_idx, "inheritance": f"table:{t_idx}"},
            })
        
        return {
            "content": content,
            "metadata": {
                "type": "docx",
                "filename": filename,
                "paragraphs": len(paragraphs),
                "tables": len(doc.tables),
            },
            "chunks": chunks if chunks else chunk_text(content, source=filename),
            "file_type": "docx",
        }
        
    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        return {
            "content": f"[DOCX Error: {str(e)}]",
            "metadata": {"type": "docx", "filename": filename, "error": str(e)},
            "chunks": [],
            "file_type": "docx",
        }


def extract_xlsx_file(file_path: str, filename: str) -> Dict[str, Any]:
    """
    Extract XLSX with structure:
    - Multiple sheets
    - Cell values
    - Formulas (as text)
    """
    try:
        from openpyxl import load_workbook
    except ImportError:
        return {
            "content": "[XLSX Support Requires: pip install openpyxl]",
            "metadata": {"type": "xlsx", "filename": filename, "error": "openpyxl not installed"},
            "chunks": [],
            "file_type": "xlsx",
        }
    
    try:
        wb = load_workbook(file_path, data_only=True)
        
        sheets_data = []
        full_content = ""
        
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            
            # Extract headers (first row)
            headers = []
            rows_data = []
            
            for row_idx, row in enumerate(sheet.iter_rows(values_only=True)):
                if row_idx == 0:
                    headers = [str(c) if c else f"Col{i}" for i, c in enumerate(row)]
                else:
                    row_dict = {h: str(v) if v else "" for h, v in zip(headers, row, strict=False)}
                    if any(row_dict.values()):  # Skip empty rows
                        rows_data.append(row_dict)
            
            sheet_content = f"\n=== Sheet: {sheet_name} ===\n"
            sheet_content += f"Headers: {', '.join(headers)}\n"
            sheet_content += f"Rows: {len(rows_data)}\n\n"
            
            for i, row in enumerate(rows_data[:50]):  # Limit preview
                sheet_content += f"Row {i+1}: {json.dumps(row)}\n"
            
            sheets_data.append({
                "name": sheet_name,
                "headers": headers,
                "rows": rows_data,
                "content": sheet_content,
            })
            full_content += sheet_content
        
        # Create chunks per sheet (and per row for large sheets)
        chunks = []
        for sheet in sheets_data:
            # Sheet-level chunk
            if len(sheet["rows"]) <= 20:
                chunks.append({
                    "content": sheet["content"],
                    "metadata": {
                        "sheet": sheet["name"],
                        "row_count": len(sheet["rows"]),
                        "inheritance": f"sheet:{sheet['name']}",
                    },
                })
            else:
                # Row-level chunks for large sheets
                for i, row in enumerate(sheet["rows"][:100]):
                    chunks.append({
                        "content": json.dumps(row),
                        "metadata": {
                            "sheet": sheet["name"],
                            "row_index": i,
                            "inheritance": f"sheet:{sheet['name']}:row:{i}",
                        },
                    })
        
        return {
            "content": full_content,
            "metadata": {
                "type": "xlsx",
                "filename": filename,
                "sheets": len(sheets_data),
                "total_rows": sum(len(s["rows"]) for s in sheets_data),
            },
            "chunks": chunks if chunks else chunk_text(full_content, source=filename),
            "file_type": "xlsx",
        }
        
    except Exception as e:
        logger.error(f"XLSX extraction failed: {e}")
        return {
            "content": f"[XLSX Error: {str(e)}]",
            "metadata": {"type": "xlsx", "filename": filename, "error": str(e)},
            "chunks": [],
            "file_type": "xlsx",
        }


def extract_pptx_file(file_path: str, filename: str) -> Dict[str, Any]:
    """
    Extract PPTX with structure:
    - Slides
    - Text content
    - Speaker notes
    - Tables
    """
    try:
        from pptx import Presentation
    except ImportError:
        return {
            "content": "[PPTX Support Requires: pip install python-pptx]",
            "metadata": {"type": "pptx", "filename": filename, "error": "python-pptx not installed"},
            "chunks": [],
            "file_type": "pptx",
        }
    
    try:
        prs = Presentation(file_path)
        
        slides_data = []
        full_content = ""
        
        for slide_idx, slide in enumerate(prs.slides):
            slide_num = slide_idx + 1
            
            # Extract text from shapes
            texts = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    texts.append(shape.text.strip())
                
                # Extract table content
                if shape.has_table:
                    table_text = "[Table]\n"
                    for row in shape.table.rows:
                        row_text = " | ".join(cell.text.strip() for cell in row.cells)
                        table_text += row_text + "\n"
                    texts.append(table_text)
            
            # Extract speaker notes
            notes = ""
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes = slide.notes_slide.notes_text_frame.text.strip()
            
            slide_content = f"\n=== Slide {slide_num} ===\n"
            slide_content += "\n".join(texts)
            if notes:
                slide_content += f"\n[Notes]: {notes}"
            
            slides_data.append({
                "slide": slide_num,
                "content": slide_content,
                "texts": texts,
                "notes": notes,
            })
            full_content += slide_content + "\n"
        
        # Create chunks per slide (FAIM inheritance: slides)
        chunks = []
        for slide in slides_data:
            if slide["content"].strip():
                chunks.append({
                    "content": slide["content"].strip(),
                    "metadata": {
                        "slide": slide["slide"],
                        "has_notes": bool(slide["notes"]),
                        "inheritance": f"slide:{slide['slide']}",
                    },
                })
        
        return {
            "content": full_content,
            "metadata": {
                "type": "pptx",
                "filename": filename,
                "slides": len(slides_data),
            },
            "chunks": chunks if chunks else chunk_text(full_content, source=filename),
            "file_type": "pptx",
        }
        
    except Exception as e:
        logger.error(f"PPTX extraction failed: {e}")
        return {
            "content": f"[PPTX Error: {str(e)}]",
            "metadata": {"type": "pptx", "filename": filename, "error": str(e)},
            "chunks": [],
            "file_type": "pptx",
        }


# =============================================================================
# CODE EXTRACTOR
# =============================================================================

def extract_code_file(file_path: str, filename: str) -> Dict[str, Any]:
    """Extract code file with language awareness."""
    ext = Path(filename).suffix.lower()
    
    lang_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "jsx", ".tsx": "tsx", ".go": "go", ".rs": "rust",
        ".java": "java", ".c": "c", ".cpp": "cpp", ".cs": "csharp",
        ".rb": "ruby", ".php": "php", ".swift": "swift", ".kt": "kotlin",
        ".scala": "scala", ".sh": "bash", ".sql": "sql",
        ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
        ".xml": "xml", ".html": "html", ".css": "css", ".scss": "scss",
        ".vue": "vue", ".svelte": "svelte",
    }
    
    language = lang_map.get(ext, "text")
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    # Extract function/class definitions for FAIM inheritance
    chunks = chunk_code(content, language, filename)
    
    return {
        "content": content,
        "metadata": {
            "type": "code",
            "language": language,
            "filename": filename,
            "line_count": content.count("\n") + 1,
        },
        "chunks": chunks,
        "file_type": f"code:{language}",
    }


# =============================================================================
# CHUNKING UTILITIES (FAIM-OPTIMIZED)
# =============================================================================

def chunk_text(text: str, max_chars: int = 2000, overlap: int = 200, source: str = "") -> List[Dict[str, Any]]:
    """
    Split text into overlapping chunks optimized for FAIM.
    Each chunk gets inheritance metadata.
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    chunk_idx = 0
    
    while start < len(text):
        end = start + max_chars
        
        # Try to break at sentence boundary
        if end < len(text):
            for sep in [". ", ".\n", "\n\n", "\n", " "]:
                pos = text.rfind(sep, start, end)
                if pos > start + max_chars // 2:
                    end = pos + len(sep)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append({
                "content": chunk,
                "metadata": {
                    "chunk_index": chunk_idx,
                    "start_char": start,
                    "end_char": end,
                    "inheritance": f"chunk:{chunk_idx}",
                    "source": source,
                },
            })
            chunk_idx += 1
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks


def chunk_code(content: str, language: str, filename: str) -> List[Dict[str, Any]]:
    """
    Split code into logical chunks (functions, classes).
    Adds language-specific inheritance metadata.
    """
    lines = content.split("\n")
    chunks = []
    current_chunk = []
    current_def = None
    chunk_idx = 0
    
    # Patterns for different languages
    def_patterns = {
        "python": ["def ", "class ", "async def "],
        "javascript": ["function ", "const ", "class ", "async function "],
        "typescript": ["function ", "const ", "class ", "interface ", "type ", "async function "],
        "go": ["func ", "type "],
        "rust": ["fn ", "struct ", "enum ", "impl ", "trait "],
        "java": ["public ", "private ", "protected ", "class ", "interface "],
    }
    
    patterns = def_patterns.get(language, [])
    
    for line in lines:
        stripped = line.strip()
        
        # Check if this is a new definition
        is_new_def = any(stripped.startswith(p) for p in patterns)
        
        if is_new_def and current_chunk:
            # Save previous chunk
            chunks.append({
                "content": "\n".join(current_chunk),
                "metadata": {
                    "chunk_index": chunk_idx,
                    "definition": current_def,
                    "language": language,
                    "inheritance": f"code:{language}:{current_def or chunk_idx}",
                },
            })
            chunk_idx += 1
            current_chunk = [line]
            current_def = stripped.split("(")[0].split(":")[0] if "(" in stripped or ":" in stripped else stripped[:50]
        else:
            current_chunk.append(line)
            
            # Also chunk if getting too large
            if len("\n".join(current_chunk)) > 1500:
                chunks.append({
                    "content": "\n".join(current_chunk),
                    "metadata": {
                        "chunk_index": chunk_idx,
                        "definition": current_def,
                        "language": language,
                        "inheritance": f"code:{language}:{current_def or chunk_idx}",
                    },
                })
                chunk_idx += 1
                current_chunk = []
                current_def = None
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append({
            "content": "\n".join(current_chunk),
            "metadata": {
                "chunk_index": chunk_idx,
                "definition": current_def,
                "language": language,
                "inheritance": f"code:{language}:{current_def or chunk_idx}",
            },
        })
    
    return chunks if chunks else chunk_text(content, source=filename)
