"""OCR service for image and scanned PDF extraction.

Unified plug-and-play OCR integration with:
- PaddleOCR v6 (default CPU-optimized engine with MKLDNN and multi-threading)
- Tesseract OCR (LSTM neural engine)
- EasyOCR & Custom REST endpoints via OCRProviderRegistry
"""

from __future__ import annotations

import io
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from perception.extract.ocr_providers import (
    OCRProcessingError,
    OCRProvider,
    OCRProviderRegistry,
    OCRResult,
    OCRUnavailableError,
    get_active_ocr_provider,
    get_ocr_registry,
    reset_ocr_registry,
)

logger = logging.getLogger(__name__)


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class OCRSettings:
    enabled: bool
    engine: str
    fail_closed: bool
    languages: str
    timeout_seconds: int
    max_image_pixels: int
    pdf_render_dpi: int
    min_text_chars: int
    tesseract_config: str


@dataclass(frozen=True)
class OCRTextResult:
    text: str
    confidence: float
    metadata: Dict[str, Any]


def get_ocr_settings() -> OCRSettings:
    registry = get_ocr_registry()
    active_engine = registry.get_active_id() if registry else "paddleocr_v6"
    active_available = registry.get_active().is_available() if (registry and registry.get_active()) else False
    default_enabled = True if active_available else False
    return OCRSettings(
        enabled=_bool_env("FAIM_OCR_ENABLED", default_enabled),
        engine=os.getenv("FAIM_OCR_ENGINE", active_engine).strip().lower() or active_engine,
        fail_closed=_bool_env("FAIM_OCR_FAIL_CLOSED", False),
        languages=os.getenv("FAIM_OCR_LANGS", "eng").strip() or "eng",
        timeout_seconds=max(1, _int_env("FAIM_OCR_TIMEOUT_SECONDS", 30)),
        max_image_pixels=max(1, _int_env("FAIM_OCR_MAX_IMAGE_PIXELS", 36_000_000)),
        pdf_render_dpi=max(72, _int_env("FAIM_OCR_PDF_RENDER_DPI", 300)),
        min_text_chars=max(0, _int_env("FAIM_OCR_MIN_TEXT_CHARS", 6)),
        tesseract_config=(
            os.getenv("FAIM_OCR_TESSERACT_CONFIG", "--oem 1 --psm 3").strip()
            or "--oem 1 --psm 3"
        ),
    )



def extract_text_from_image_bytes(
    image_bytes: bytes,
    *,
    source: str,
    filename: str = "",
    page_number: Optional[int] = None,
    settings: Optional[OCRSettings] = None,
) -> Optional[OCRTextResult]:
    """Extract OCR text from image bytes via the active or requested OCR provider.

    Returns None when OCR is disabled or no usable text is detected.
    """
    settings = settings or get_ocr_settings()
    if not settings.enabled:
        return None

    registry = get_ocr_registry()
    provider = registry.get(settings.engine) if settings.engine else registry.get_active()
    if provider is None:
        raise OCRUnavailableError(f"Unsupported or unregistered OCR engine: {settings.engine}")

    result: Optional[OCRResult] = provider.extract_image_bytes(
        image_bytes,
        source=source,
        filename=filename,
        page_number=page_number,
        languages=settings.languages,
        timeout_seconds=settings.timeout_seconds,
        max_image_pixels=settings.max_image_pixels,
        min_text_chars=settings.min_text_chars,
        tesseract_config=settings.tesseract_config,
    )

    if result is None:
        return None

    meta = dict(result.metadata)
    meta["ocr_dpi_equivalent"] = settings.pdf_render_dpi

    return OCRTextResult(text=result.text, confidence=result.confidence, metadata=meta)


def extract_text_from_pdf_page(
    page: Any,
    *,
    page_number: int,
    filename: str = "",
    settings: Optional[OCRSettings] = None,
) -> Optional[OCRTextResult]:
    """Render a PDF page at high DPI (300 default) and run OCR over the rasterized image."""
    settings = settings or get_ocr_settings()
    if not settings.enabled:
        return None

    registry = get_ocr_registry()
    provider = registry.get(settings.engine) if settings.engine else registry.get_active()
    if provider is None:
        raise OCRUnavailableError(f"Unsupported or unregistered OCR engine: {settings.engine}")

    result: Optional[OCRResult] = provider.extract_pdf_page(
        page,
        page_number=page_number,
        filename=filename,
        pdf_render_dpi=settings.pdf_render_dpi,
        languages=settings.languages,
        timeout_seconds=settings.timeout_seconds,
        max_image_pixels=settings.max_image_pixels,
        min_text_chars=settings.min_text_chars,
        tesseract_config=settings.tesseract_config,
    )

    if result is None:
        return None

    meta = dict(result.metadata)
    meta["ocr_dpi_equivalent"] = settings.pdf_render_dpi

    return OCRTextResult(text=result.text, confidence=result.confidence, metadata=meta)


__all__ = [
    "OCRProcessingError",
    "OCRProvider",
    "OCRProviderRegistry",
    "OCRResult",
    "OCRSettings",
    "OCRTextResult",
    "OCRUnavailableError",
    "extract_text_from_image_bytes",
    "extract_text_from_pdf_page",
    "get_active_ocr_provider",
    "get_ocr_registry",
    "get_ocr_settings",
    "reset_ocr_registry",
]
