# FAIM-Native Perception Layer Documentation

FAIM-native extraction with EvidenceBlocks and MemoryPackets.

## Quick Start

```bash
# Extract blocks from file
python scripts/extract_packet.py my_raw_id --file document.pdf --output packet.json --validate

# Validate existing packet
python scripts/packet_validate.py packet.json
```

## Core Types

### BlockAnchor

Location anchor within source document.

```python
from core.contracts.types import BlockAnchor

anchor = BlockAnchor(
    doc_type="pdf",   # "pdf" | "docx" | "pptx" | "xlsx" | "text" | "image"
    page=1,           # PDF page (1-indexed)
    slide=None,       # PPTX slide
    sheet=None,       # XLSX sheet name
    row_start=None,   # Row range start
    row_end=None,     # Row range end
    char_start=None,  # Char offset start
    char_end=None,    # Char offset end
    section=None,     # Section name (markdown)
)
```

### EvidenceBlock

Single extracted evidence with anchor.

```python
from core.contracts.types import EvidenceBlock

block = EvidenceBlock.create(
    raw_id="raw_abc123",
    anchor=anchor,
    content="Extracted text content",
    block_type="text",  # "text" | "table" | "heading" | "code" | "image_stub"
    confidence=1.0,     # 0.0-1.0 (OCR=0.2)
)
```

### MemoryPacket

Deterministic packet of blocks.

```python
from core.contracts.types import MemoryPacket
from perception.packetize import create_packet

packet = create_packet("raw_abc123", blocks)
# packet.packet_hash = sha256 of canonical JSON
```

## Usage

### Extract Blocks

```python
from perception.router import route_extraction

file_bytes = Path("document.pdf").read_bytes()
blocks = route_extraction(file_bytes, "document.pdf", "raw_id_123")
```

### Create Packet

```python
from perception.packetize import create_packet, packet_to_json

packet = create_packet("raw_id_123", blocks)
output = packet_to_json(packet, blocks)
```

### Validate

```python
from perception.validate import validate_all, assert_valid

errors = validate_all(packet, blocks)
# Or raise on error:
assert_valid(packet, blocks)
```

## FAIM-Native Rules

| Rule                   | Implementation              |
| ---------------------- | --------------------------- |
| No token chunking      | EvidenceBlocks, not chunks  |
| Anchors mandatory      | Every block has BlockAnchor |
| Deterministic ordering | `sort_blocks()` by anchor   |
| Deterministic hashes   | `compute_packet_hash()`     |
| Clean text only        | No HTML, no base64          |

## File Types Supported

| Type      | Anchor               | Extraction                   |
| --------- | -------------------- | ---------------------------- |
| PDF       | page                 | PyMuPDF/pdfplumber           |
| DOCX      | char_start/end       | python-docx                  |
| PPTX      | slide                | python-pptx                  |
| XLSX/CSV  | sheet, row_start/end | openpyxl                     |
| Text/Code | char_start/end       | UTF-8 decode                 |
| Images    | page=1               | IMAGE_STUB (OCR placeholder) |
