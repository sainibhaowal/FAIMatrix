"""Opt-in evidence-block chunking for retrieval-oriented ingestion.

Chunking is deliberately disabled by default so existing packet hashes and
ingestion semantics remain stable.  When enabled, only long text blocks are
split; headings, tables, code, and image stubs remain atomic.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, List

from core.contracts.types import EvidenceBlock


def _windows(text: str, max_chars: int, overlap: int) -> Iterable[tuple[int, int]]:
    start = 0
    length = len(text)
    while start < length:
        hard_end = min(length, start + max_chars)
        end = hard_end
        if hard_end < length:
            boundary = max(
                text.rfind("\n", start + max_chars // 2, hard_end),
                text.rfind(". ", start + max_chars // 2, hard_end),
                text.rfind(" ", start + max_chars // 2, hard_end),
            )
            if boundary > start:
                end = boundary + (2 if text[boundary : boundary + 2] == ". " else 1)
        if end <= start:
            end = hard_end
        yield start, end
        if end >= length:
            break
        start = max(start + 1, end - overlap)


def chunk_evidence_blocks(
    blocks: Iterable[EvidenceBlock],
    *,
    max_chars: int = 1200,
    overlap: int = 120,
) -> List[EvidenceBlock]:
    """Return deterministic retrieval chunks while preserving source anchors."""
    if max_chars < 256:
        raise ValueError("max_chars must be at least 256")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be non-negative and smaller than max_chars")

    result: List[EvidenceBlock] = []
    for block in blocks:
        content = str(getattr(block, "content", "") or "")
        block_type = str(getattr(block, "block_type", "text") or "text")
        if len(content) <= max_chars or block_type in {
            "heading",
            "table",
            "code",
            "image_stub",
        }:
            result.append(block)
            continue

        base_start = block.anchor.char_start or 0
        for part_number, (start, end) in enumerate(
            _windows(content, max_chars, overlap)
        ):
            chunk = content[start:end].strip()
            if not chunk:
                continue
            anchor = replace(
                block.anchor,
                char_start=base_start + start,
                char_end=base_start + end,
            )
            metadata = dict(block.metadata or {})
            metadata.update(
                {
                    "chunked": True,
                    "chunk_index": part_number,
                    "chunk_source_id": str(block.id),
                }
            )
            result.append(
                EvidenceBlock.create(
                    raw_id=block.raw_id,
                    anchor=anchor,
                    content=chunk,
                    block_type=block.block_type,
                    confidence=block.confidence,
                    metadata=metadata,
                )
            )
    return result


__all__ = ["chunk_evidence_blocks"]
