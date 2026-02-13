"""OCR service for image and scanned PDF extraction."""

from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional


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
        value = int(raw)
    except ValueError:
        return default
    return value


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


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


class OCRUnavailableError(RuntimeError):
    """Raised when OCR is requested but dependencies/engine are unavailable."""


class OCRProcessingError(RuntimeError):
    """Raised when OCR fails for an input payload."""


def get_ocr_settings() -> OCRSettings:
    return OCRSettings(
        enabled=_bool_env("FAIM_OCR_ENABLED", False),
        engine=os.getenv("FAIM_OCR_ENGINE", "tesseract").strip().lower() or "tesseract",
        fail_closed=_bool_env("FAIM_OCR_FAIL_CLOSED", False),
        languages=os.getenv("FAIM_OCR_LANGS", "eng").strip() or "eng",
        timeout_seconds=max(1, _int_env("FAIM_OCR_TIMEOUT_SECONDS", 20)),
        max_image_pixels=max(1, _int_env("FAIM_OCR_MAX_IMAGE_PIXELS", 24_000_000)),
        pdf_render_dpi=max(72, _int_env("FAIM_OCR_PDF_RENDER_DPI", 180)),
        min_text_chars=max(0, _int_env("FAIM_OCR_MIN_TEXT_CHARS", 6)),
        tesseract_config=(
            os.getenv("FAIM_OCR_TESSERACT_CONFIG", "--oem 1 --psm 6").strip()
            or "--oem 1 --psm 6"
        ),
    )


def _estimate_confidence(pytesseract: Any, image: Any, *, settings: OCRSettings) -> float:
    try:
        data = pytesseract.image_to_data(
            image,
            lang=settings.languages,
            timeout=settings.timeout_seconds,
            output_type=pytesseract.Output.DICT,
            config=settings.tesseract_config,
        )
        raw_conf = data.get("conf") or []
        values = []
        for item in raw_conf:
            try:
                c = float(item)
            except (TypeError, ValueError):
                continue
            if c >= 0:
                values.append(c)
        if values:
            mean = sum(values) / len(values)
            return max(0.05, min(1.0, mean / 100.0))
    except Exception:
        pass
    return 0.55


def extract_text_from_image_bytes(
    image_bytes: bytes,
    *,
    source: str,
    filename: str = "",
    page_number: Optional[int] = None,
    settings: Optional[OCRSettings] = None,
) -> Optional[OCRTextResult]:
    """Extract OCR text from image bytes.

    Returns None when OCR is disabled or no usable text is detected.
    """
    settings = settings or get_ocr_settings()
    if not settings.enabled:
        return None
    if settings.engine != "tesseract":
        raise OCRUnavailableError(f"Unsupported OCR engine: {settings.engine}")

    try:
        import pytesseract
        from PIL import Image, ImageOps
    except Exception as exc:  # pragma: no cover - environment dependent
        raise OCRUnavailableError("OCR dependencies are not installed") from exc

    if not image_bytes:
        raise OCRProcessingError("Empty image payload")

    try:
        with Image.open(io.BytesIO(image_bytes)) as raw:
            image = raw.convert("RGB")
    except Exception as exc:
        raise OCRProcessingError("Invalid image payload") from exc

    width, height = image.size
    if width <= 0 or height <= 0:
        raise OCRProcessingError("Invalid image dimensions")
    if width * height > settings.max_image_pixels:
        raise OCRProcessingError(
            f"Image exceeds OCR pixel limit ({width}x{height} > {settings.max_image_pixels})"
        )

    prepared = ImageOps.autocontrast(ImageOps.grayscale(image))
    try:
        raw_text = pytesseract.image_to_string(
            prepared,
            lang=settings.languages,
            timeout=settings.timeout_seconds,
            config=settings.tesseract_config,
        )
    except Exception as exc:
        raise OCRProcessingError(f"OCR execution failed: {exc}") from exc

    text = _normalize_text(raw_text)
    if len(text) < settings.min_text_chars:
        return None

    confidence = _estimate_confidence(pytesseract, prepared, settings=settings)
    metadata: Dict[str, Any] = {
        "ocr": True,
        "ocr_engine": settings.engine,
        "ocr_langs": settings.languages,
        "ocr_source": source,
        "ocr_image_width": int(width),
        "ocr_image_height": int(height),
    }
    if filename:
        metadata["filename"] = filename
    if page_number is not None:
        metadata["ocr_page"] = int(page_number)

    return OCRTextResult(text=text, confidence=confidence, metadata=metadata)


def extract_text_from_pdf_page(
    page: Any,
    *,
    page_number: int,
    filename: str = "",
    settings: Optional[OCRSettings] = None,
) -> Optional[OCRTextResult]:
    """Render a PDF page and run OCR over the rendered image."""
    settings = settings or get_ocr_settings()
    if not settings.enabled:
        return None

    try:
        scale = max(1.0, float(settings.pdf_render_dpi) / 72.0)
        import fitz

        matrix = fitz.Matrix(scale, scale)
    except Exception:
        # Fallback if fitz import is unavailable.
        matrix = None

    try:
        pix = page.get_pixmap(matrix=matrix, alpha=False) if matrix else page.get_pixmap(alpha=False)
        image_bytes = pix.tobytes("png")
    except Exception as exc:
        raise OCRProcessingError(f"PDF page render failed: {exc}") from exc

    return extract_text_from_image_bytes(
        image_bytes,
        source="pdf_page_image",
        filename=filename,
        page_number=page_number,
        settings=settings,
    )


__all__ = [
    "OCRProcessingError",
    "OCRSettings",
    "OCRTextResult",
    "OCRUnavailableError",
    "extract_text_from_image_bytes",
    "extract_text_from_pdf_page",
    "get_ocr_settings",
]
