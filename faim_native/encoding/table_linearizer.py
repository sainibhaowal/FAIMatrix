"""Deterministic table linearization helpers."""

from __future__ import annotations

import re
from typing import Iterable, List


_CELL_SPLIT_RE = re.compile(r"\s*\|\s*")


def linearize_table_text(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    normalized: List[str] = []
    for line in lines:
        cells = [cell.strip() for cell in _CELL_SPLIT_RE.split(line) if cell.strip()]
        if cells:
            normalized.append(" ; ".join(cells))
    return "\n".join(normalized)


__all__ = ["linearize_table_text"]
