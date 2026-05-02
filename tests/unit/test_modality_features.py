from __future__ import annotations

from faim_native.core.contracts.types import BlockAnchor, EvidenceBlock
from faim_native.encoding.modality_features import build_modality_features


def test_build_modality_features_deterministic():
    blocks = [
        EvidenceBlock.create(
            raw_id="raw-1",
            anchor=BlockAnchor(doc_type="pdf", page=1),
            content="OCR extracted invoice text",
            block_type="ocr",
        ),
        EvidenceBlock.create(
            raw_id="raw-1",
            anchor=BlockAnchor(doc_type="pdf", page=1),
            content="name | amount\nalice | 10",
            block_type="table",
        ),
    ]
    first = build_modality_features(
        blocks=blocks,
        filename="invoice.pdf",
        file_bytes=b"image-bytes",
        metadata={"mime_type": "application/pdf"},
    )
    second = build_modality_features(
        blocks=blocks,
        filename="invoice.pdf",
        file_bytes=b"image-bytes",
        metadata={"mime_type": "application/pdf"},
    )
    assert first == second
    assert first.image_phash
    assert first.table_text

