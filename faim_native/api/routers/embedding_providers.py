"""FAIM-Native API: Embedding Provider Management Router.

Tenant-scoped embedding provider lifecycle routes:
- list providers
- add provider (local, openai, custom)
- remove provider
- set active provider
- get active provider status
- test provider connection
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

# Flexible imports
_parent = Path(__file__).parent.parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from api.deps import FAIMContext, get_faim_context, require_scopes  # noqa: E402
from store.pg.repos.auth_repo import AuthRepo  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/embedding-providers", tags=["embedding-providers"])


# =============================================================================
# Contracts
# =============================================================================


class EmbeddingProviderItem(BaseModel):
    tenant_id: Optional[str] = "default"
    provider_id: Optional[str] = None
    id: Optional[str] = None
    name: str
    display_name: str
    provider_type: str
    dimension: int
    max_tokens: int
    is_free: bool
    description: str
    languages: List[str]
    is_active: bool
    is_available: bool
    model_path: Optional[str] = None
    status: Optional[str] = "online"
    last_checked: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.provider_id:
            self.provider_id = self.id or "unknown"
        if not self.id:
            self.id = self.provider_id


class EmbeddingProviderListResponse(BaseModel):
    items: List[EmbeddingProviderItem]
    total: int
    active_provider_id: Optional[str] = None


class EmbeddingProviderCreateRequest(BaseModel):
    name: str
    provider_type: str  # "local", "openai", "custom"
    # For local: no additional config needed (uses bge-m3 in faim_native/models)
    # For openai: api_key required
    # For custom: base_url required, api_key optional
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    dimension: Optional[int] = None


class EmbeddingProviderCreateResponse(BaseModel):
    provider: EmbeddingProviderItem


class EmbeddingProviderTestRequest(BaseModel):
    provider_id: Optional[str] = None
    # Optional: test with a specific text
    test_text: Optional[str] = "FAIM embedding test"


class EmbeddingProviderTestResponse(BaseModel):
    success: bool
    message: str
    dimension: Optional[int] = None
    latency_ms: Optional[int] = None


class EmbeddingProviderSwitchRequest(BaseModel):
    provider_id: str


class EmbeddingProviderSwitchResponse(BaseModel):
    success: bool
    active_provider_id: str


# =============================================================================
# Helpers
# =============================================================================


def _get_registry(ctx: FAIMContext):
    """Get tenant-scoped embedding provider registry."""
    from encoding.embedding_providers import get_tenant_embedding_registry
    return get_tenant_embedding_registry(ctx.tenant_id)


# =============================================================================
# Routes
# =============================================================================


@router.get("", response_model=EmbeddingProviderListResponse)
async def list_embedding_providers(
    ctx: FAIMContext = Depends(get_faim_context),
):
    """List all embedding providers for the tenant."""
    from encoding.embedding_providers import get_tenant_embedding_registry

    registry = get_tenant_embedding_registry(ctx.tenant_id)
    providers = registry.list_providers()

    return EmbeddingProviderListResponse(
        items=[EmbeddingProviderItem(**p) for p in providers],
        total=len(providers),
        active_provider_id=registry.get_active_id(),
    )


@router.get("/active", response_model=Optional[EmbeddingProviderItem])
async def get_active_embedding_provider(
    ctx: FAIMContext = Depends(get_faim_context),
):
    """Get the currently active embedding provider."""
    from encoding.embedding_providers import get_tenant_embedding_registry

    registry = get_tenant_embedding_registry(ctx.tenant_id)
    active = registry.get_active()
    
    if active is None:
        return None
    
    info = active.model_info
    return EmbeddingProviderItem(
        tenant_id=ctx.tenant_id,
        provider_id=registry.get_active_id() or "",
        name=info.name,
        display_name=info.display_name,
        provider_type=info.provider_type,
        dimension=info.dimension,
        max_tokens=info.max_tokens,
        is_free=info.is_free,
        description=info.description,
        languages=info.languages,
        is_active=True,
        is_available=active.is_available(),
        model_path=info.model_path,
        status="online" if active.is_available() else "offline",
    )


@router.post("", response_model=EmbeddingProviderCreateResponse)
async def create_embedding_provider(
    req: EmbeddingProviderCreateRequest,
    ctx: FAIMContext = Depends(get_faim_context),
):
    """Add a new embedding provider."""
    from encoding.embedding_providers import (
        BgeM3LocalProvider,
        CustomEmbeddingProvider,
        OpenAIEmbeddingProvider,
        get_tenant_embedding_registry,
    )

    registry = get_tenant_embedding_registry(ctx.tenant_id)
    
    if req.provider_type == "local":
        from encoding.embedding_providers import (
            discover_local_models,
            LocalEmbeddingProvider,
            LOCAL_MODELS_DIR,
        )
        # If a specific model is requested, resolve it to a discovered local path
        if req.model:
            for model_path in discover_local_models():
                if model_path.name == req.model or model_path.name.endswith(req.model):
                    provider = LocalEmbeddingProvider(str(model_path))
                    provider_id = f"local-{model_path.name}"
                    break
            else:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Local model '{req.model}' not found in {LOCAL_MODELS_DIR}. "
                        f"Downloaded models: {[p.name for p in discover_local_models()]}"
                    ),
                )
        else:
            provider = BgeM3LocalProvider()
            provider_id = "bge-m3-local"
    elif req.provider_type == "openai":
        if not req.api_key:
            raise HTTPException(status_code=400, detail="OpenAI provider requires api_key")
        model = req.model or "text-embedding-3-small"
        provider = OpenAIEmbeddingProvider(api_key=req.api_key, model=model)
        provider_id = f"openai-{model}"
    elif req.provider_type == "custom":
        if not req.base_url:
            raise HTTPException(status_code=400, detail="Custom provider requires base_url")
        model = req.model or "custom"
        dimension = req.dimension or 1024
        provider = CustomEmbeddingProvider(
            base_url=req.base_url,
            api_key=req.api_key,
            model=model,
            dimension=dimension,
        )
        provider_id = f"custom-{model}"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider type: {req.provider_type}")
    
    # Register with custom ID
    registry.register(provider_id, provider)
    
    info = provider.model_info
    return EmbeddingProviderCreateResponse(
        provider=EmbeddingProviderItem(
            tenant_id=ctx.tenant_id,
            provider_id=provider_id,
            name=req.name,
            display_name=info.display_name,
            provider_type=info.provider_type,
            dimension=info.dimension,
            max_tokens=info.max_tokens,
            is_free=info.is_free,
            description=info.description,
            languages=info.languages,
            is_active=registry.get_active_id() == provider_id,
            is_available=provider.is_available(),
            model_path=info.model_path,
            status="online" if provider.is_available() else "offline",
        )
    )


@router.delete("/{provider_id}")
async def delete_embedding_provider(
    provider_id: str,
    ctx: FAIMContext = Depends(get_faim_context),
):
    """Remove an embedding provider."""
    from encoding.embedding_providers import get_tenant_embedding_registry

    registry = get_tenant_embedding_registry(ctx.tenant_id)
    success = registry.unregister(provider_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return {"success": True, "message": f"Provider {provider_id} removed"}


@router.post("/switch", response_model=EmbeddingProviderSwitchResponse)
async def switch_embedding_provider(
    req: EmbeddingProviderSwitchRequest,
    ctx: FAIMContext = Depends(get_faim_context),
):
    """Set the active embedding provider."""
    from encoding.embedding_providers import get_tenant_embedding_registry

    registry = get_tenant_embedding_registry(ctx.tenant_id)
    success = registry.set_active(req.provider_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return EmbeddingProviderSwitchResponse(
        success=True,
        active_provider_id=req.provider_id,
    )


@router.post("/{provider_id}/test", response_model=EmbeddingProviderTestResponse)
async def test_embedding_provider(
    provider_id: str,
    req: EmbeddingProviderTestRequest,
    ctx: FAIMContext = Depends(get_faim_context),
):
    """Test an embedding provider connection and encoding."""
    from encoding.embedding_providers import get_tenant_embedding_registry
    import time

    registry = get_tenant_embedding_registry(ctx.tenant_id)
    provider = registry.get(provider_id)
    
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    if not provider.is_available():
        return EmbeddingProviderTestResponse(
            success=False,
            message="Provider not available (model not loaded or API key missing)",
        )
    try:
        from starlette.concurrency import run_in_threadpool
        start = time.perf_counter()
        result = await run_in_threadpool(provider.encode, [req.test_text])
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        return EmbeddingProviderTestResponse(
            success=True,
            message=f"Successfully encoded test text ({len(result.vectors[0])} dimensions)",
            dimension=result.dimension,
            latency_ms=latency_ms,
        )
    except Exception as e:
        logger.error(f"Embedding test failed for {provider_id}: {e}")
        return EmbeddingProviderTestResponse(
            success=False,
            message=f"Encoding failed: {str(e)}",
        )