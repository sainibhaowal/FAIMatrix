"""OCR Provider Abstraction Layer.

Provides a unified plug-and-play interface for multiple OCR engines:
- PaddleOCR v6 (default CPU-optimized engine with MKLDNN and multi-threading)
- Tesseract (local LSTM engine)
- EasyOCR (pluggable local engine)
- Custom / Cloud OCR (REST/OpenAI-compatible endpoints)
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models & Errors
# =============================================================================


@dataclass(frozen=True)
class OCRModelInfo:
    """Metadata about an OCR provider / engine."""

    id: str
    name: str
    display_name: str
    provider_type: str  # "local", "cloud", "custom"
    languages: List[str]
    is_free: bool
    description: str
    version: str = "v1"
    is_local: bool = True
    model_path: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OCRResult:
    """Standardized OCR extraction result."""

    text: str
    confidence: float
    metadata: Dict[str, Any]


class OCRUnavailableError(RuntimeError):
    """Raised when OCR is requested but dependencies or engine are unavailable."""


class OCRProcessingError(RuntimeError):
    """Raised when OCR fails during image or PDF page processing."""


# =============================================================================
# Helper Utilities
# =============================================================================


def _normalize_text(text: str) -> str:
    """Normalize extracted text whitespace while preserving paragraph breaks."""
    lines = (text or "").splitlines()
    cleaned = []
    for line in lines:
        line = re.sub(r"[ \t]+", " ", line).strip()
        cleaned.append(line)
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned))
    return result.strip()


def _preprocess_image(
    image: Any,
    max_image_pixels: int = 36_000_000,
    min_target_width: int = 2000,
) -> Any:
    """Preprocess PIL Image for improved OCR recognition."""
    from PIL import Image, ImageFilter, ImageOps

    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    gray = image.convert("L")

    # Upscale small images to preserve character edge clarity
    w, h = gray.size
    if w < min_target_width:
        scale = min_target_width / max(1, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        gray = gray.resize((new_w, new_h), Image.LANCZOS)

    # Downscale if exceeding memory budget
    w2, h2 = gray.size
    if w2 * h2 > max_image_pixels:
        ratio = (max_image_pixels / (w2 * h2)) ** 0.5
        gray = gray.resize((int(w2 * ratio), int(h2 * ratio)), Image.LANCZOS)

    # Contrast normalization & edge sharpening
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = gray.filter(ImageFilter.SHARPEN)
    return gray


# =============================================================================
# Base OCR Provider
# =============================================================================


class OCRProvider(ABC):
    """Abstract base class for plug-and-play OCR providers."""

    @property
    @abstractmethod
    def model_info(self) -> OCRModelInfo:
        """Return provider metadata."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider dependencies/runtime are available."""
        pass

    @abstractmethod
    def extract_image_bytes(
        self,
        image_bytes: bytes,
        *,
        source: str = "image_bytes",
        filename: str = "",
        page_number: Optional[int] = None,
        languages: Optional[str] = None,
        timeout_seconds: int = 30,
        max_image_pixels: int = 36_000_000,
        min_text_chars: int = 6,
        **kwargs: Any,
    ) -> Optional[OCRResult]:
        """Extract text and confidence from raw image bytes."""
        pass

    def extract_pdf_page(
        self,
        page: Any,
        *,
        page_number: int,
        filename: str = "",
        pdf_render_dpi: int = 300,
        languages: Optional[str] = None,
        timeout_seconds: int = 30,
        max_image_pixels: int = 36_000_000,
        min_text_chars: int = 6,
        **kwargs: Any,
    ) -> Optional[OCRResult]:
        """Render a PyMuPDF / fitz page to high-DPI raster image and extract text."""
        try:
            import fitz

            scale = max(1.0, float(pdf_render_dpi) / 72.0)
            matrix = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image_bytes = pix.tobytes("png")
        except Exception as exc:
            raise OCRProcessingError(f"PDF page render failed: {exc}") from exc

        return self.extract_image_bytes(
            image_bytes,
            source="pdf_page_image",
            filename=filename,
            page_number=page_number,
            languages=languages,
            timeout_seconds=timeout_seconds,
            max_image_pixels=max_image_pixels,
            min_text_chars=min_text_chars,
            **kwargs,
        )


# =============================================================================
# Concrete Provider: PaddleOCR v6 (Default CPU-Optimized)
# =============================================================================


class PaddleOCRv6Provider(OCRProvider):
    """PaddleOCR v6 CPU-optimized provider with MKLDNN and multi-threading."""

    def __init__(
        self,
        default_lang: str = "en",
        use_gpu: bool = False,
        enable_mkldnn: bool = True,
        cpu_threads: Optional[int] = None,
    ):
        self._default_lang = default_lang
        self._use_gpu = use_gpu
        self._enable_mkldnn = enable_mkldnn
        self._cpu_threads = cpu_threads or max(1, os.cpu_count() or 4)
        self._instances: Dict[str, Any] = {}

    @property
    def model_info(self) -> OCRModelInfo:
        return OCRModelInfo(
            id="paddleocr_v6",
            name="paddleocr_v6",
            display_name="PaddleOCR v6 (CPU Ultra / MKLDNN)",
            provider_type="local",
            languages=["eng", "ch", "fr", "german", "korean", "japan", "80+ langs"],
            is_free=True,
            description="Ultra-fast CPU-optimized PaddleOCR v6 with MKLDNN vector acceleration & angle classification.",
            version="v6",
            is_local=True,
            config={
                "use_gpu": self._use_gpu,
                "enable_mkldnn": self._enable_mkldnn,
                "cpu_threads": self._cpu_threads,
            },
        )

    def is_available(self) -> bool:
        try:
            import numpy  # noqa: F401
            import paddleocr  # noqa: F401
            return True
        except Exception:
            return False

    def _get_engine(self, lang_code: str) -> Any:
        target_lang = "en" if (not lang_code or lang_code.startswith("eng")) else lang_code
        if target_lang not in self._instances:
            import os
            # Avoid slow remote connectivity checks on startup
            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
            from paddleocr import PaddleOCR

            engine = None
            # Modern PaddleX / PaddleOCR 3.x configuration optimized for CPU
            try:
                engine = PaddleOCR(
                    lang=target_lang,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                    enable_mkldnn=False,
                )
            except Exception:
                pass

            if engine is None:
                try:
                    engine = PaddleOCR(
                        use_angle_cls=True,
                        lang=target_lang,
                        show_log=False,
                        use_gpu=self._use_gpu,
                        enable_mkldnn=False,
                        cpu_threads=self._cpu_threads,
                    )
                except Exception:
                    engine = PaddleOCR(lang=target_lang)

            self._instances[target_lang] = engine
        return self._instances[target_lang]

    def extract_image_bytes(
        self,
        image_bytes: bytes,
        *,
        source: str = "image_bytes",
        filename: str = "",
        page_number: Optional[int] = None,
        languages: Optional[str] = None,
        timeout_seconds: int = 30,
        max_image_pixels: int = 36_000_000,
        min_text_chars: int = 6,
        **kwargs: Any,
    ) -> Optional[OCRResult]:
        if not self.is_available():
            raise OCRUnavailableError("PaddleOCR dependencies (paddleocr, numpy) are not installed")

        if not image_bytes:
            raise OCRProcessingError("Empty image payload")

        try:
            from PIL import Image
            import numpy as np
        except Exception as exc:
            raise OCRUnavailableError(f"Required imaging packages missing: {exc}") from exc

        try:
            with Image.open(io.BytesIO(image_bytes)) as raw:
                image = raw.convert("RGB")
        except Exception as exc:
            raise OCRProcessingError("Invalid image payload") from exc

        width, height = image.size
        if width <= 0 or height <= 0:
            raise OCRProcessingError("Invalid image dimensions")

        # Native resolution processing (no forced 2000px upscaling for modern deep nets)
        prepared = _preprocess_image(image, max_image_pixels=max_image_pixels, min_target_width=0)
        pw, ph = prepared.size
        if pw * ph > max_image_pixels:
            raise OCRProcessingError(f"Image exceeds pixel limit ({pw}x{ph})")

        # PaddleOCR expects 3-channel RGB numpy array

        prepared_rgb = prepared.convert("RGB")

        lang = languages or self._default_lang
        try:
            engine = self._get_engine(lang)
            img_np = np.array(prepared_rgb)
            
            # Support both predict() (PaddleOCR 3.x) and ocr() (PaddleOCR 2.x)
            if hasattr(engine, "predict"):
                res = engine.predict(img_np)
            else:
                try:
                    res = engine.ocr(img_np)
                except Exception:
                    res = engine.ocr(img_np, cls=True)

            texts: List[str] = []
            scores: List[float] = []
            if res:
                for item in res:
                    if not item:
                        continue
                    if isinstance(item, dict):
                        # PaddleOCR 3.x / PaddleX dict output
                        rec_texts = item.get("rec_texts") or item.get("text") or []
                        rec_scores = item.get("rec_scores") or item.get("score") or []
                        if isinstance(rec_texts, list):
                            for idx, t in enumerate(rec_texts):
                                if t and str(t).strip():
                                    texts.append(str(t).strip())
                                    if idx < len(rec_scores):
                                        try:
                                            scores.append(float(rec_scores[idx]))
                                        except (TypeError, ValueError):
                                            pass
                        elif isinstance(rec_texts, str) and rec_texts.strip():
                            texts.append(rec_texts.strip())
                            if rec_scores:
                                try:
                                    scores.append(float(rec_scores))
                                except (TypeError, ValueError):
                                    pass
                    elif isinstance(item, list):
                        # PaddleOCR 2.x list of lines
                        for line in item:
                            if line and len(line) >= 2 and isinstance(line[1], (tuple, list)):
                                txt, score = line[1]
                                if txt and str(txt).strip():
                                    texts.append(str(txt).strip())
                                    try:
                                        scores.append(float(score))
                                    except (TypeError, ValueError):
                                        pass
                            elif isinstance(line, dict):
                                txt = line.get("text") or line.get("transcription") or ""
                                score = line.get("score") or line.get("confidence") or 0.8
                                if txt and str(txt).strip():
                                    texts.append(str(txt).strip())
                                    scores.append(float(score))

            raw_text = "\n".join(texts)
            confidence = (sum(scores) / len(scores)) if scores else 0.55
        except Exception as exc:
            raise OCRProcessingError(f"PaddleOCR execution failed: {exc}") from exc



        text = _normalize_text(raw_text)
        if len(text) < min_text_chars:
            return None

        metadata: Dict[str, Any] = {
            "ocr": True,
            "ocr_engine": "paddleocr_v6",
            "ocr_provider_id": "paddleocr_v6",
            "ocr_langs": lang,
            "ocr_source": source,
            "ocr_image_width": int(width),
            "ocr_image_height": int(height),
        }
        if filename:
            metadata["filename"] = filename
        if page_number is not None:
            metadata["ocr_page"] = int(page_number)

        return OCRResult(text=text, confidence=confidence, metadata=metadata)


# =============================================================================
# Concrete Provider: Tesseract OCR
# =============================================================================


class TesseractOCRProvider(OCRProvider):
    """Tesseract OCR Provider using pytesseract with PSM 3 auto layout."""

    def __init__(
        self,
        default_lang: str = "eng",
        default_config: str = "--oem 1 --psm 3",
    ):
        self._default_lang = default_lang
        self._default_config = default_config

    @property
    def model_info(self) -> OCRModelInfo:
        return OCRModelInfo(
            id="tesseract",
            name="tesseract",
            display_name="Tesseract OCR (LSTM / PSM 3)",
            provider_type="local",
            languages=["eng", "osd", "multilingual"],
            is_free=True,
            description="Classic Tesseract LSTM engine with PSM 3 multi-column automatic page layout detection.",
            version="v5",
            is_local=True,
            config={"config": self._default_config},
        )

    def is_available(self) -> bool:
        try:
            import pytesseract  # noqa: F401
            return True
        except Exception:
            return False

    def extract_image_bytes(
        self,
        image_bytes: bytes,
        *,
        source: str = "image_bytes",
        filename: str = "",
        page_number: Optional[int] = None,
        languages: Optional[str] = None,
        timeout_seconds: int = 30,
        max_image_pixels: int = 36_000_000,
        min_text_chars: int = 6,
        **kwargs: Any,
    ) -> Optional[OCRResult]:
        if not self.is_available():
            raise OCRUnavailableError("Tesseract dependency (pytesseract) is not installed")

        if not image_bytes:
            raise OCRProcessingError("Empty image payload")

        try:
            import pytesseract
            from PIL import Image
        except Exception as exc:
            raise OCRUnavailableError(f"Required imaging packages missing: {exc}") from exc

        try:
            with Image.open(io.BytesIO(image_bytes)) as raw:
                image = raw.convert("RGB")
        except Exception as exc:
            raise OCRProcessingError("Invalid image payload") from exc

        width, height = image.size
        if width <= 0 or height <= 0:
            raise OCRProcessingError("Invalid image dimensions")

        prepared = _preprocess_image(image, max_image_pixels=max_image_pixels)
        pw, ph = prepared.size
        if pw * ph > max_image_pixels:
            raise OCRProcessingError(f"Image exceeds pixel limit ({pw}x{ph})")

        lang = languages or self._default_lang
        config = kwargs.get("tesseract_config", self._default_config)

        try:
            raw_text = pytesseract.image_to_string(
                prepared,
                lang=lang,
                timeout=timeout_seconds,
                config=config,
            )
            # Estimate confidence
            confidence = 0.55
            try:
                data = pytesseract.image_to_data(
                    prepared,
                    lang=lang,
                    timeout=timeout_seconds,
                    output_type=pytesseract.Output.DICT,
                    config=config,
                )
                raw_conf = data.get("conf") or []
                values = [float(c) for c in raw_conf if c not in (-1, "-1", None)]
                if values:
                    mean = sum(values) / len(values)
                    confidence = max(0.05, min(1.0, mean / 100.0))
            except Exception:
                pass
        except Exception as exc:
            raise OCRProcessingError(f"Tesseract execution failed: {exc}") from exc

        text = _normalize_text(raw_text)
        if len(text) < min_text_chars:
            return None

        metadata: Dict[str, Any] = {
            "ocr": True,
            "ocr_engine": "tesseract",
            "ocr_provider_id": "tesseract",
            "ocr_langs": lang,
            "ocr_source": source,
            "ocr_image_width": int(width),
            "ocr_image_height": int(height),
        }
        if filename:
            metadata["filename"] = filename
        if page_number is not None:
            metadata["ocr_page"] = int(page_number)

        return OCRResult(text=text, confidence=confidence, metadata=metadata)


# =============================================================================
# Concrete Provider: EasyOCR (Pluggable Local Provider)
# =============================================================================


class EasyOCRProvider(OCRProvider):
    """EasyOCR pluggable provider for PyTorch-based OCR."""

    def __init__(
        self,
        default_langs: Optional[List[str]] = None,
        gpu: bool = False,
    ):
        self._langs = default_langs or ["en"]
        self._gpu = gpu
        self._reader = None

    @property
    def model_info(self) -> OCRModelInfo:
        return OCRModelInfo(
            id="easyocr",
            name="easyocr",
            display_name="EasyOCR (PyTorch Engine)",
            provider_type="local",
            languages=self._langs,
            is_free=True,
            description="Deep learning OCR powered by PyTorch and CRAFT text detection.",
            version="v1.7",
            is_local=True,
            config={"gpu": self._gpu},
        )

    def is_available(self) -> bool:
        try:
            import easyocr  # noqa: F401
            return True
        except Exception:
            return False

    def _get_reader(self) -> Any:
        if self._reader is None:
            import easyocr

            self._reader = easyocr.Reader(self._langs, gpu=self._gpu)
        return self._reader

    def extract_image_bytes(
        self,
        image_bytes: bytes,
        *,
        source: str = "image_bytes",
        filename: str = "",
        page_number: Optional[int] = None,
        languages: Optional[str] = None,
        timeout_seconds: int = 30,
        max_image_pixels: int = 36_000_000,
        min_text_chars: int = 6,
        **kwargs: Any,
    ) -> Optional[OCRResult]:
        if not self.is_available():
            raise OCRUnavailableError("EasyOCR is not installed (pip install easyocr)")

        try:
            reader = self._get_reader()
            results = reader.readtext(image_bytes)
            texts = [r[1] for r in results if r and len(r) >= 2 and r[1]]
            confidences = [float(r[2]) for r in results if r and len(r) >= 3 and r[2] is not None]

            raw_text = "\n".join(texts)
            confidence = (sum(confidences) / len(confidences)) if confidences else 0.55
        except Exception as exc:
            raise OCRProcessingError(f"EasyOCR execution failed: {exc}") from exc

        text = _normalize_text(raw_text)
        if len(text) < min_text_chars:
            return None

        metadata: Dict[str, Any] = {
            "ocr": True,
            "ocr_engine": "easyocr",
            "ocr_provider_id": "easyocr",
            "ocr_source": source,
        }
        if filename:
            metadata["filename"] = filename
        if page_number is not None:
            metadata["ocr_page"] = int(page_number)

        return OCRResult(text=text, confidence=confidence, metadata=metadata)


# =============================================================================
# Concrete Provider: Custom / Remote REST OCR Provider
# =============================================================================


class CustomOCRProvider(OCRProvider):
    """Custom HTTP REST / OpenAI-compatible OCR Endpoint provider."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        name: str = "custom-ocr",
        display_name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._name = name
        self._display_name = display_name or f"Custom OCR ({name})"
        self._description = description or f"Remote OCR endpoint at {self._base_url}"

    @property
    def model_info(self) -> OCRModelInfo:
        return OCRModelInfo(
            id=self._name,
            name=self._name,
            display_name=self._display_name,
            provider_type="custom",
            languages=["multilingual"],
            is_free=False,
            description=self._description,
            version="custom",
            is_local=False,
            config={"base_url": self._base_url},
        )

    def is_available(self) -> bool:
        return bool(self._base_url)

    def extract_image_bytes(
        self,
        image_bytes: bytes,
        *,
        source: str = "image_bytes",
        filename: str = "",
        page_number: Optional[int] = None,
        languages: Optional[str] = None,
        timeout_seconds: int = 30,
        max_image_pixels: int = 36_000_000,
        min_text_chars: int = 6,
        **kwargs: Any,
    ) -> Optional[OCRResult]:
        import base64
        import urllib.request

        if not self.is_available():
            raise OCRUnavailableError(f"Custom endpoint URL not configured for {self._name}")

        b64_data = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "image_base64": b64_data,
            "filename": filename,
            "page_number": page_number,
            "languages": languages,
        }

        url = f"{self._base_url}/ocr"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}),
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_text = data.get("text", "")
                confidence = float(data.get("confidence", 0.9))
        except Exception as exc:
            raise OCRProcessingError(f"Custom OCR endpoint error: {exc}") from exc

        text = _normalize_text(raw_text)
        if len(text) < min_text_chars:
            return None

        metadata = {
            "ocr": True,
            "ocr_engine": self._name,
            "ocr_provider_id": self._name,
            "ocr_source": source,
        }
        if filename:
            metadata["filename"] = filename
        if page_number is not None:
            metadata["ocr_page"] = int(page_number)

        return OCRResult(text=text, confidence=confidence, metadata=metadata)


# =============================================================================
# OCR Provider Registry
# =============================================================================


class OCRProviderRegistry:
    """Central registry managing multiple plug-and-play OCR engines."""

    def __init__(self):
        self._providers: Dict[str, OCRProvider] = {}
        self._active_provider_id: str = "paddleocr_v6"
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register built-in OCR engines."""
        # 1. PaddleOCR v6 (Default CPU-optimized engine)
        self.register("paddleocr_v6", PaddleOCRv6Provider())
        self.register("paddleocr", PaddleOCRv6Provider())
        self.register("paddle", PaddleOCRv6Provider())

        # 2. Tesseract OCR
        self.register("tesseract", TesseractOCRProvider())

        # 3. EasyOCR (Pluggable)
        self.register("easyocr", EasyOCRProvider())

        # Preferred default active provider
        env_engine = os.getenv("FAIM_OCR_ENGINE", "paddleocr_v6").strip().lower()
        if env_engine in self._providers:
            self._active_provider_id = env_engine
        else:
            self._active_provider_id = "paddleocr_v6"

    def register(self, provider_id: str, provider: OCRProvider) -> None:
        """Register a new OCR engine provider."""
        self._providers[provider_id] = provider
        logger.info(f"Registered OCR provider: {provider_id} ({provider.model_info.display_name})")

    def unregister(self, provider_id: str) -> bool:
        """Remove a registered OCR provider."""
        if provider_id in self._providers:
            del self._providers[provider_id]
            if self._active_provider_id == provider_id:
                self._active_provider_id = next(iter(self._providers), "paddleocr_v6")
            return True
        return False

    def get(self, provider_id: str) -> Optional[OCRProvider]:
        """Retrieve provider by ID."""
        return self._providers.get(provider_id)

    def list_providers(self) -> List[Dict[str, Any]]:
        """List all registered OCR providers with live status."""
        result = []
        for pid, provider in self._providers.items():
            # Skip alias ids in listing to avoid duplicates (e.g. paddle vs paddleocr_v6)
            info = provider.model_info
            if pid != info.id and pid in ("paddleocr", "paddle"):
                continue

            available = provider.is_available()
            result.append(
                {
                    "id": pid,
                    "provider_id": pid,
                    "name": info.name,
                    "display_name": info.display_name,
                    "provider_type": info.provider_type,
                    "languages": info.languages,
                    "is_free": info.is_free,
                    "description": info.description,
                    "version": info.version,
                    "is_local": info.is_local,
                    "is_active": pid == self._active_provider_id or info.id == self._active_provider_id,
                    "is_available": available,
                    "status": "online" if available else "offline",
                    "config": info.config,
                }
            )
        return result

    def set_active(self, provider_id: str) -> bool:
        """Set the active OCR engine provider."""
        if provider_id in self._providers:
            self._active_provider_id = provider_id
            return True
        return False

    def get_active(self) -> Optional[OCRProvider]:
        """Get the currently active OCR provider instance."""
        if self._active_provider_id in self._providers:
            return self._providers[self._active_provider_id]
        return next(iter(self._providers.values()), None)

    def get_active_id(self) -> str:
        """Get the active OCR provider ID."""
        return self._active_provider_id


# =============================================================================
# Global Singleton
# =============================================================================

_global_ocr_registry: Optional[OCRProviderRegistry] = None


def get_ocr_registry() -> OCRProviderRegistry:
    """Get the global OCR Provider Registry."""
    global _global_ocr_registry
    if _global_ocr_registry is None:
        _global_ocr_registry = OCRProviderRegistry()
    return _global_ocr_registry


def reset_ocr_registry() -> None:
    """Reset the global OCR registry (for tests)."""
    global _global_ocr_registry
    _global_ocr_registry = None


def get_active_ocr_provider() -> Optional[OCRProvider]:
    """Get currently active OCR provider."""
    return get_ocr_registry().get_active()


__all__ = [
    "CustomOCRProvider",
    "EasyOCRProvider",
    "OCRModelInfo",
    "OCRProcessingError",
    "OCRProvider",
    "OCRProviderRegistry",
    "OCRResult",
    "OCRUnavailableError",
    "PaddleOCRv6Provider",
    "TesseractOCRProvider",
    "get_active_ocr_provider",
    "get_ocr_registry",
    "reset_ocr_registry",
]
