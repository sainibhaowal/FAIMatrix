"""OCR service for image and scanned PDF extraction.

Improvements over v1:
- Default DPI raised to 300 (was 180) for scanned document accuracy
- Enhanced image preprocessing: grayscale + autocontrast + sharpen + upscale
- Tesseract PSM 3 (auto layout detection) for unknown page structures
- Scanned PDF pages rendered at 300 DPI for clean rasterization
- Confidence estimation uses word-level data for accuracy
"""

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
        return int(raw)
    except ValueError:
        return default


def _normalize_text(text: str) -> str:
    # Collapse whitespace but preserve paragraph breaks
    lines = (text or "").splitlines()
    cleaned = []
    for line in lines:
        line = re.sub(r"[ \t]+", " ", line).strip()
        cleaned.append(line)
    # Collapse more than 2 consecutive blank lines to 1
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned))
    return result.strip()


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
        timeout_seconds=max(1, _int_env("FAIM_OCR_TIMEOUT_SECONDS", 30)),
        max_image_pixels=max(1, _int_env("FAIM_OCR_MAX_IMAGE_PIXELS", 36_000_000)),
        # 300 DPI: crisp rasterization for scanned documents (was 180)
        pdf_render_dpi=max(72, _int_env("FAIM_OCR_PDF_RENDER_DPI", 300)),
        min_text_chars=max(0, _int_env("FAIM_OCR_MIN_TEXT_CHARS", 6)),
        # PSM 3 = auto page segmentation (handles multi-column, mixed layouts)
        # OEM 1 = LSTM neural engine only
        tesseract_config=(
            os.getenv("FAIM_OCR_TESSERACT_CONFIG", "--oem 1 --psm 3").strip()
            or "--oem 1 --psm 3"
        ),
    )


def _preprocess_image_for_ocr(image: Any, settings: OCRSettings) -> Any:
    """Enhance image quality before OCR using Pillow only (no cv2/scipy).

    Pipeline:
    1. Convert to RGB then grayscale
    2. Upscale small images to minimum 1500px wide (prevents tesseract blur)
    3. Autocontrast with 1% cutoff (normalises brightness/contrast)
    4. Sharpen edges (improves character boundary detection)
    """
    from PIL import Image, ImageFilter, ImageOps

    # Ensure consistent color space
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    gray = image.convert("L")

    # Upscale if too small — Tesseract works best at ~300 DPI equivalent
    # 1500px wide ≈ an A4 page at 175 DPI; 2400px ≈ 300 DPI
    w, h = gray.size
    target_min_width = 2000
    if w < target_min_width:
        scale = target_min_width / w
        new_w = int(w * scale)
        new_h = int(h * scale)
        gray = gray.resize((new_w, new_h), Image.LANCZOS)

    # Cap at pixel limit to avoid memory issues
    w2, h2 = gray.size
    if w2 * h2 > settings.max_image_pixels:
        # Scale down proportionally
        ratio = (settings.max_image_pixels / (w2 * h2)) ** 0.5
        gray = gray.resize((int(w2 * ratio), int(h2 * ratio)), Image.LANCZOS)

    # Autocontrast: stretch histogram to full 0-255 range, ignore 1% extremes
    gray = ImageOps.autocontrast(gray, cutoff=1)

    # Sharpen: improves OCR on slightly blurry scans
    gray = gray.filter(ImageFilter.SHARPEN)

    return gray


def _estimate_confidence(
    pytesseract: Any, image: Any, *, settings: OCRSettings
) -> float:
    """Compute mean word-level confidence from Tesseract data output."""
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
        from PIL import Image
    except Exception as exc:
        raise OCRUnavailableError(
            "OCR dependencies (pytesseract, Pillow) are not installed"
        ) from exc

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

    # Preprocess for better OCR accuracy
    prepared = _preprocess_image_for_ocr(image, settings)

    # Post-preprocess size check
    pw, ph = prepared.size
    if pw * ph > settings.max_image_pixels:
        raise OCRProcessingError(
            f"Image exceeds OCR pixel limit after preprocessing ({pw}x{ph})"
        )

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
        "ocr_dpi_equivalent": settings.pdf_render_dpi,
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
    """Render a PDF page at high DPI and run OCR over the rasterized image.

    Uses 300 DPI by default for clean rasterization of scanned documents.
    """
    settings = settings or get_ocr_settings()
    if not settings.enabled:
        return None

    try:
        import fitz

        # Scale factor: DPI / 72 (PDF native DPI)
        scale = max(1.0, float(settings.pdf_render_dpi) / 72.0)
        matrix = fitz.Matrix(scale, scale)
    except Exception:
        matrix = None

    try:
        if matrix is not None:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
        else:
            pix = page.get_pixmap(alpha=False)
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
