"""OCR Feature Stubs for FAIM-Native Encoding.

Produces stable feature vectors for IMAGE_STUB blocks.

NO ML MODELS. NO RANDOMNESS.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import BlockAnchor, EvidenceBlock
    from faim.Faim_Native.encoding.vector_schema import VECTOR_DIMENSION
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import BlockAnchor, EvidenceBlock
    from encoding.vector_schema import VECTOR_DIMENSION


# OCR confidence for stub blocks
OCR_STUB_CONFIDENCE = 0.2


def is_image_stub(block: EvidenceBlock) -> bool:
    """Check if block is an IMAGE_STUB requiring OCR."""
    return block.block_type == "image_stub" or "[IMAGE_STUB" in block.content


def extract_ocr_stub_vector(
    anchor: BlockAnchor,
    content: str = "",
) -> List[float]:
    """Generate stable feature vector for IMAGE_STUB blocks.

    Since OCR is not implemented, this produces deterministic
    zero-based features with anchor flags.

    Args:
        anchor: BlockAnchor for position info.
        content: Block content (usually stub message).

    Returns:
        Zero vector with anchor-based flags at the end.
    """
    # Start with zeros
    vector = [0.0] * VECTOR_DIMENSION

    # Add anchor-based flags in last 16 positions
    # These provide minimal positional information

    # Page flag (index -16)
    if anchor.page is not None:
        vector[-16] = min(anchor.page / 100.0, 1.0)

    # Slide flag (index -15)
    if anchor.slide is not None:
        vector[-15] = min(anchor.slide / 50.0, 1.0)

    # Doc type flag (index -14)
    doc_type_flags = {
        "pdf": 0.1,
        "docx": 0.2,
        "pptx": 0.3,
        "xlsx": 0.4,
        "image": 0.6,
    }
    vector[-14] = doc_type_flags.get(anchor.doc_type, 0.0)

    # Image stub marker (index -13)
    vector[-13] = 1.0  # Always 1.0 for image stubs

    # OCR pending flag (index -12)
    vector[-12] = 1.0  # Indicates OCR processing needed

    return vector


def extract_ocr_stub_signature(anchor: BlockAnchor) -> Dict[str, float]:
    """Generate opposition signature for IMAGE_STUB blocks.

    Args:
        anchor: BlockAnchor for position info.

    Returns:
        Opposition signature indicating stub status.
    """
    return {
        "norm": 0.0,  # Zero norm (sparse)
        "density": 0.0,  # No content
        "max_val": 0.0,
        "mean_val": 0.0,
        "length": 0.0,
        "entropy": 0.0,
        "top_0": 0.0,
        "top_1": 0.0,
        "top_2": 0.0,
        "is_stub": 1.0,  # Mark as stub
        "ocr_pending": 1.0,  # OCR needed
    }


# Exports
__all__ = [
    "OCR_STUB_CONFIDENCE",
    "is_image_stub",
    "extract_ocr_stub_vector",
    "extract_ocr_stub_signature",
]
