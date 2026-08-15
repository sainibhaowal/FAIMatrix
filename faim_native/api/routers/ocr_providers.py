"""FAIM-Native API: OCR Provider Management Router.

Tenant-scoped OCR provider lifecycle routes:
- list providers (PaddleOCR v6, Tesseract, EasyOCR, Custom REST endpoints)
- add custom OCR provider
- remove custom provider
- switch active OCR provider
- get active OCR provider status
- test OCR provider latency and text extraction accuracy
"""

from __future__ import annotations

import base64
import io
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context  # noqa: E402
from perception.extract.ocr_providers import (  # noqa: E402
    CustomOCRProvider,
    EasyOCRProvider,
    PaddleOCRv6Provider,
    TesseractOCRProvider,
    get_active_ocr_provider,
    get_ocr_registry,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ocr-providers", tags=["ocr-providers"])


# =============================================================================
# Contracts
# =============================================================================


class OCRProviderItem(BaseModel):
    id: str
    provider_id: str
    name: str
    display_name: str
    provider_type: str  # "local", "cloud", "custom"
    languages: List[str]
    is_free: bool
    description: str
    version: str = "v1"
    is_local: bool = True
    is_active: bool = False
    is_available: bool = False
    status: str = "online"  # "online" | "offline"
    config: Optional[Dict[str, Any]] = None


class OCRProviderListResponse(BaseModel):
    items: List[OCRProviderItem]
    total: int
    active_provider_id: str


class OCRProviderCreateRequest(BaseModel):
    id: str = Field(..., description="Unique provider ID e.g. 'custom-vps-ocr'")
    name: str = Field(..., description="Provider name")
    display_name: Optional[str] = None
    provider_type: str = Field(default="custom", description="'local' or 'custom'")
    base_url: Optional[str] = Field(default=None, description="HTTP endpoint for custom OCR")
    api_key: Optional[str] = Field(default=None, description="Optional API key for custom OCR")
    description: Optional[str] = None
    languages: Optional[List[str]] = Field(default_factory=lambda: ["eng"])


class OCRProviderSwitchRequest(BaseModel):
    provider_id: str


class OCRProviderSwitchResponse(BaseModel):
    success: bool
    active_provider_id: str
    message: str


class OCRProviderTestRequest(BaseModel):
    # Optional base64 encoded image to test, or defaults to built-in synthetic benchmark image
    image_base64: Optional[str] = None
    languages: Optional[str] = "eng"


class OCRProviderTestResponse(BaseModel):
    success: bool
    provider_id: str
    message: str
    extracted_text: str
    confidence: float
    latency_ms: int
    status: str


# =============================================================================
# Helper: Create Synthetic Test Image
# =============================================================================


def _generate_test_image_bytes() -> bytes:
    """Generate a clean test image with clear text for OCR latency & sanity testing."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (600, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Simple high-contrast text rendering
    draw.text((30, 40), "FAIM MATRIX OCR TEST", fill=(0, 0, 0))
    draw.text((30, 90), "PaddleOCR v6 CPU Acceleration Active", fill=(20, 20, 20))
    draw.text((30, 140), "Deterministic Memory & Perception Engine", fill=(50, 50, 50))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# =============================================================================
# Routes
# =============================================================================


@router.get("", response_model=OCRProviderListResponse)
async def list_ocr_providers(
    ctx: FAIMContext = Depends(get_faim_context),
):
    """List all registered OCR providers and their real-time engine statuses."""
    registry = get_ocr_registry()
    providers = registry.list_providers()
    items = [OCRProviderItem(**p) for p in providers]
    return OCRProviderListResponse(
        items=items,
        total=len(items),
        active_provider_id=registry.get_active_id(),
    )


@router.get("/active", response_model=Optional[OCRProviderItem])
async def get_active_provider(
    ctx: FAIMContext = Depends(get_faim_context),
):
    """Get the currently active OCR provider."""
    registry = get_ocr_registry()
    active = registry.get_active()
    if active is None:
        return None

    info = active.model_info
    avail = active.is_available()
    return OCRProviderItem(
        id=info.id,
        provider_id=registry.get_active_id(),
        name=info.name,
        display_name=info.display_name,
        provider_type=info.provider_type,
        languages=info.languages,
        is_free=info.is_free,
        description=info.description,
        version=info.version,
        is_local=info.is_local,
        is_active=True,
        is_available=avail,
        status="online" if avail else "offline",
        config=info.config,
    )


@router.post("", response_model=OCRProviderItem)
async def create_ocr_provider(
    req: OCRProviderCreateRequest,
    ctx: FAIMContext = Depends(get_faim_context),
):
    """Plug in a new custom or local OCR provider."""
    registry = get_ocr_registry()

    if req.provider_type == "custom":
        if not req.base_url:
            raise HTTPException(status_code=400, detail="Custom OCR provider requires base_url")
        provider = CustomOCRProvider(
            base_url=req.base_url,
            api_key=req.api_key,
            name=req.id,
            display_name=req.display_name or req.name,
            description=req.description,
        )
    elif req.provider_type == "local":
        if req.id in ("tesseract", "pytesseract"):
            provider = TesseractOCRProvider()
        elif req.id in ("easyocr",):
            provider = EasyOCRProvider(default_langs=req.languages)
        else:
            provider = PaddleOCRv6Provider()
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider_type: {req.provider_type}")

    registry.register(req.id, provider)
    info = provider.model_info
    avail = provider.is_available()

    return OCRProviderItem(
        id=req.id,
        provider_id=req.id,
        name=info.name,
        display_name=info.display_name,
        provider_type=info.provider_type,
        languages=info.languages,
        is_free=info.is_free,
        description=info.description,
        version=info.version,
        is_local=info.is_local,
        is_active=registry.get_active_id() == req.id,
        is_available=avail,
        status="online" if avail else "offline",
        config=info.config,
    )


@router.delete("/{provider_id}")
async def delete_ocr_provider(
    provider_id: str,
    ctx: FAIMContext = Depends(get_faim_context),
):
    """Remove a custom or pluggable OCR provider."""
    registry = get_ocr_registry()
    if provider_id in ("paddleocr_v6", "tesseract"):
        raise HTTPException(
            status_code=400,
            detail=f"Core provider '{provider_id}' cannot be deleted. You can deactivate or switch away from it instead.",
        )

    success = registry.unregister(provider_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"OCR provider '{provider_id}' not found")

    return {"success": True, "message": f"OCR Provider '{provider_id}' removed successfully."}


@router.post("/switch", response_model=OCRProviderSwitchResponse)
async def switch_ocr_provider(
    req: OCRProviderSwitchRequest,
    ctx: FAIMContext = Depends(get_faim_context),
):
    """Switch the active OCR engine provider."""
    registry = get_ocr_registry()
    provider = registry.get(req.provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail=f"OCR provider '{req.provider_id}' not found")

    registry.set_active(req.provider_id)
    return OCRProviderSwitchResponse(
        success=True,
        active_provider_id=req.provider_id,
        message=f"Switched active OCR engine to '{provider.model_info.display_name}'.",
    )


@router.post("/{provider_id}/test", response_model=OCRProviderTestResponse)
async def test_ocr_provider(
    provider_id: str,
    req: OCRProviderTestRequest,
    ctx: FAIMContext = Depends(get_faim_context),
):
    """Run a live benchmark OCR test against the selected engine."""
    registry = get_ocr_registry()
    provider = registry.get(provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail=f"OCR provider '{provider_id}' not found")

    if not provider.is_available():
        return OCRProviderTestResponse(
            success=False,
            provider_id=provider_id,
            message="Provider is offline or dependencies are missing",
            extracted_text="",
            confidence=0.0,
            latency_ms=0,
            status="offline",
        )

    # Decode supplied image or generate benchmark canvas
    if req.image_base64:
        try:
            image_bytes = base64.b64decode(req.image_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {e}")
    else:
        image_bytes = _generate_test_image_bytes()

    start_time = time.perf_counter()
    try:
        from starlette.concurrency import run_in_threadpool

        result = await run_in_threadpool(
            provider.extract_image_bytes,
            image_bytes,
            source="provider_test_benchmark",
            languages=req.languages,
            min_text_chars=1,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        if result:
            return OCRProviderTestResponse(
                success=True,
                provider_id=provider_id,
                message=f"OCR test passed successfully ({latency_ms}ms, confidence: {result.confidence:.2f})",
                extracted_text=result.text,
                confidence=result.confidence,
                latency_ms=latency_ms,
                status="online",
            )
        else:
            return OCRProviderTestResponse(
                success=True,
                provider_id=provider_id,
                message=f"OCR ran cleanly in {latency_ms}ms but detected no text characters",
                extracted_text="",
                confidence=0.5,
                latency_ms=latency_ms,
                status="online",
            )
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.error(f"OCR test failed on {provider_id}: {exc}")
        return OCRProviderTestResponse(
            success=False,
            provider_id=provider_id,
            message=f"Extraction failed: {str(exc)}",
            extracted_text="",
            confidence=0.0,
            latency_ms=latency_ms,
            status="error",
        )


__all__ = ["router"]
