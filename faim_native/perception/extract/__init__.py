"""Perception extraction package: text, document, and OCR extractors."""

from perception.extract.ocr_providers import (
    CustomOCRProvider,
    EasyOCRProvider,
    OCRModelInfo,
    OCRProcessingError,
    OCRProvider,
    OCRProviderRegistry,
    OCRResult,
    OCRUnavailableError,
    PaddleOCRv6Provider,
    TesseractOCRProvider,
    get_active_ocr_provider,
    get_ocr_registry,
    reset_ocr_registry,
)
from perception.extract.ocr_service import (
    OCRSettings,
    OCRTextResult,
    extract_text_from_image_bytes,
    extract_text_from_pdf_page,
    get_ocr_settings,
)

__all__ = [
    "CustomOCRProvider",
    "EasyOCRProvider",
    "OCRModelInfo",
    "OCRProcessingError",
    "OCRProvider",
    "OCRProviderRegistry",
    "OCRResult",
    "OCRSettings",
    "OCRTextResult",
    "OCRUnavailableError",
    "PaddleOCRv6Provider",
    "TesseractOCRProvider",
    "extract_text_from_image_bytes",
    "extract_text_from_pdf_page",
    "get_active_ocr_provider",
    "get_ocr_registry",
    "get_ocr_settings",
    "reset_ocr_registry",
]
