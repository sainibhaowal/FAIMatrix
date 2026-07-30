"""Deterministic multimodal sidecar features."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

try:
    from faim.Faim_Native.core.contracts.types import EvidenceBlock
except (ImportError, RuntimeError):
    from core.contracts.types import EvidenceBlock

from encoding.image_phash import compute_image_phash
from encoding.table_linearizer import linearize_table_text

_WORD_RE = re.compile(r"[a-z0-9]+(?:[._:/-][a-z0-9]+)*")


@dataclass(frozen=True)
class ModalityFeatures:
    modality_hash: str
    ocr_text: str
    table_text: str
    layout_tokens: Tuple[str, ...]
    image_phash: str
    filename_tokens: Tuple[str, ...]
    caption_tokens: Tuple[str, ...]
    metadata_tokens: Tuple[str, ...]


def _tokenize(value: str) -> Tuple[str, ...]:
    return tuple(sorted(set(_WORD_RE.findall((value or "").lower()))))


def _compute_hash(payload: Dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_modality_features(
    *,
    blocks: Sequence[EvidenceBlock],
    filename: str,
    file_bytes: bytes,
    caption: str = "",
    metadata: Optional[Dict[str, object]] = None,
) -> ModalityFeatures:
    ocr_lines: List[str] = []
    table_lines: List[str] = []
    layout_tokens = set()

    for block in blocks:
        if block.block_type == "table":
            table_lines.append(linearize_table_text(block.content))
        elif block.block_type in {"image_stub", "ocr"}:
            ocr_lines.append(block.content.strip())
        if block.anchor.page is not None:
            layout_tokens.add(f"page:{block.anchor.page}")
        if block.anchor.slide is not None:
            layout_tokens.add(f"slide:{block.anchor.slide}")
        if block.anchor.section:
            layout_tokens.add(f"section:{str(block.anchor.section).lower()}")
        layout_tokens.add(f"block_type:{block.block_type.lower()}")

    filename_tokens = _tokenize(Path(filename).stem)
    caption_tokens = _tokenize(caption)
    metadata_tokens = _tokenize(
        " ".join(f"{k} {v}" for k, v in sorted((metadata or {}).items()))
    )
    payload = {
        "ocr_text": "\n".join(ocr_lines).strip(),
        "table_text": "\n".join(table_lines).strip(),
        "layout_tokens": sorted(layout_tokens),
        "image_phash": compute_image_phash(file_bytes),
        "filename_tokens": list(filename_tokens),
        "caption_tokens": list(caption_tokens),
        "metadata_tokens": list(metadata_tokens),
    }
    return ModalityFeatures(
        modality_hash=_compute_hash(payload),
        ocr_text=str(payload["ocr_text"]),
        table_text=str(payload["table_text"]),
        layout_tokens=tuple(payload["layout_tokens"]),
        image_phash=str(payload["image_phash"]),
        filename_tokens=filename_tokens,
        caption_tokens=caption_tokens,
        metadata_tokens=metadata_tokens,
    )


__all__ = ["ModalityFeatures", "build_modality_features"]
