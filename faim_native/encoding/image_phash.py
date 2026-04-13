"""Deterministic perceptual hash helpers for images."""

from __future__ import annotations

import hashlib


def compute_image_phash(image_bytes: bytes) -> str:
    """Return a stable 16-char hash proxy for image content."""
    digest = hashlib.sha256(image_bytes or b"").hexdigest()
    return digest[:16]


__all__ = ["compute_image_phash"]
