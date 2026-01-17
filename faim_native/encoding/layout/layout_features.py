"""Layout Features for FAIM-Native Encoding.

Extracts deterministic features from BlockAnchor for layout-aware encoding.

NO ML MODELS. NO RANDOMNESS.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

# Flexible imports
try:
    from faim.Faim_Native.core.contracts.types import BlockAnchor
except (ImportError, RuntimeError):
    _parent = Path(__file__).parent.parent.parent
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from core.contracts.types import BlockAnchor


# Layout feature dimension
LAYOUT_FEATURE_DIM = 12


def extract_layout_features(anchor: BlockAnchor) -> List[float]:
    """Extract deterministic layout features from anchor.

    Features are normalized to 0-1 range where possible.

    Args:
        anchor: BlockAnchor with position information.

    Returns:
        Fixed-dimension list of layout features.
    """
    features = []

    # Page features (0-3)
    if anchor.page is not None:
        features.append(min(anchor.page / 100.0, 1.0))  # Normalized page
        features.append(1.0 if anchor.page == 1 else 0.0)  # Is first page
        features.append(1.0 if anchor.page <= 3 else 0.0)  # Early page (1-3)
    else:
        features.extend([0.0, 0.0, 0.0])

    # Slide features (3-5)
    if anchor.slide is not None:
        features.append(min(anchor.slide / 50.0, 1.0))  # Normalized slide
        features.append(1.0 if anchor.slide == 1 else 0.0)  # Is title slide
    else:
        features.extend([0.0, 0.0])

    # Sheet features (5-7)
    if anchor.sheet is not None:
        features.append(1.0)  # Has sheet
        # Hash sheet name for consistent feature
        sheet_hash = hash(anchor.sheet) % 1000 / 1000.0
        features.append(sheet_hash)
    else:
        features.extend([0.0, 0.0])

    # Row features (7-9)
    if anchor.row_start is not None:
        features.append(min(anchor.row_start / 1000.0, 1.0))  # Start row
        row_span = (anchor.row_end or anchor.row_start) - anchor.row_start + 1
        features.append(min(row_span / 100.0, 1.0))  # Row span
    else:
        features.extend([0.0, 0.0])

    # Char offset features (9-11)
    if anchor.char_start is not None:
        features.append(min(anchor.char_start / 10000.0, 1.0))  # Start offset
        char_span = (anchor.char_end or anchor.char_start) - anchor.char_start
        features.append(min(char_span / 5000.0, 1.0))  # Char span
    else:
        features.extend([0.0, 0.0])

    # Doc type flag (11)
    doc_type_map = {
        "pdf": 0.1,
        "docx": 0.2,
        "pptx": 0.3,
        "xlsx": 0.4,
        "text": 0.5,
        "image": 0.6,
    }
    features.append(doc_type_map.get(anchor.doc_type, 0.0))

    # Ensure fixed dimension
    assert (
        len(features) == LAYOUT_FEATURE_DIM
    ), f"Expected {LAYOUT_FEATURE_DIM}, got {len(features)}"

    return features


def layout_features_to_dict(features: List[float]) -> Dict[str, float]:
    """Convert layout features to named dictionary."""
    keys = [
        "page_norm",
        "is_first_page",
        "is_early_page",
        "slide_norm",
        "is_title_slide",
        "has_sheet",
        "sheet_hash",
        "row_start_norm",
        "row_span_norm",
        "char_start_norm",
        "char_span_norm",
        "doc_type_flag",
    ]
    return dict(zip(keys, features, strict=False))


# Exports
__all__ = [
    "LAYOUT_FEATURE_DIM",
    "extract_layout_features",
    "layout_features_to_dict",
]
