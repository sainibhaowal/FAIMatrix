"""Provider-management route contracts with deterministic provider doubles."""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace

import pytest


def _ctx():
    return SimpleNamespace(tenant_id="tenant-1")


class _Registry:
    def __init__(self, providers=None, active_id=None):
        self.providers = dict(providers or {})
        self.active_id = active_id

    def list_providers(self):
        return list(self.providers.values())

    def get_active_id(self):
        return self.active_id

    def get_active(self):
        return self.providers.get(self.active_id)

    def get(self, provider_id):
        return self.providers.get(provider_id)

    def register(self, provider_id, provider):
        self.providers[provider_id] = provider
        self.active_id = self.active_id or provider_id

    def unregister(self, provider_id):
        return self.providers.pop(provider_id, None) is not None

    def set_active(self, provider_id):
        if provider_id not in self.providers:
            return False
        self.active_id = provider_id
        return True


def _embedding_info(name="local"):
    return SimpleNamespace(
        name=name,
        display_name=name.title(),
        provider_type="local",
        dimension=3,
        max_tokens=128,
        is_free=True,
        description="test provider",
        languages=["en"],
        model_path="/models/test",
    )


def test_embedding_provider_contract_defaults_and_registry_helper(monkeypatch):
    import encoding.embedding_providers as providers
    from api.routers import embedding_providers as router

    item = router.EmbeddingProviderItem(
        id="provider-1",
        name="Provider",
        display_name="Provider",
        provider_type="local",
        dimension=3,
        max_tokens=10,
        is_free=True,
        description="test",
        languages=["en"],
        is_active=False,
        is_available=True,
    )
    assert item.provider_id == "provider-1"
    registry = object()
    monkeypatch.setattr(
        providers, "get_tenant_embedding_registry", lambda tenant: registry
    )
    assert router._get_registry(_ctx()) is registry


def test_provider_router_import_path_bootstrap(monkeypatch):
    import api.routers.embedding_providers as embedding
    import api.routers.ocr_providers as ocr

    for module in (embedding, ocr):
        native_root = str(module._parent)
        original = list(sys.path)
        monkeypatch.setattr(
            sys, "path", [entry for entry in original if entry != native_root]
        )
        importlib.reload(module)
        assert native_root in sys.path


class _EmbeddingProvider:
    def __init__(self, available=True, error=False):
        self.model_info = _embedding_info()
        self.available = available
        self.error = error

    def is_available(self):
        return self.available

    def encode(self, texts):
        if self.error:
            raise RuntimeError("encoder failed")
        return SimpleNamespace(vectors=[[0.1, 0.2, 0.3] for _ in texts], dimension=3)


@pytest.mark.asyncio
async def test_embedding_provider_routes_all_lifecycle_branches(monkeypatch):
    import encoding.embedding_providers as providers
    from api.routers import embedding_providers as router

    registry = _Registry()
    monkeypatch.setattr(
        providers, "get_tenant_embedding_registry", lambda _tenant: registry
    )
    listing = await router.list_embedding_providers(_ctx())
    assert listing.total == 0
    assert await router.get_active_embedding_provider(_ctx()) is None

    local = _EmbeddingProvider()
    monkeypatch.setattr(providers, "BgeM3LocalProvider", lambda: local)
    created = await router.create_embedding_provider(
        router.EmbeddingProviderCreateRequest(name="Local", provider_type="local"),
        _ctx(),
    )
    assert created.provider.provider_id == "bge-m3-local"
    active = await router.get_active_embedding_provider(_ctx())
    assert active.provider_id == "bge-m3-local"

    openai = _EmbeddingProvider()
    custom = _EmbeddingProvider()
    monkeypatch.setattr(providers, "OpenAIEmbeddingProvider", lambda **kwargs: openai)
    monkeypatch.setattr(providers, "CustomEmbeddingProvider", lambda **kwargs: custom)
    with pytest.raises(router.HTTPException) as exc:
        await router.create_embedding_provider(
            router.EmbeddingProviderCreateRequest(name="O", provider_type="openai"),
            _ctx(),
        )
    assert exc.value.status_code == 400
    result = await router.create_embedding_provider(
        router.EmbeddingProviderCreateRequest(
            name="O", provider_type="openai", api_key="secret"
        ),
        _ctx(),
    )
    assert result.provider.provider_id.startswith("openai-")
    with pytest.raises(router.HTTPException):
        await router.create_embedding_provider(
            router.EmbeddingProviderCreateRequest(name="C", provider_type="custom"),
            _ctx(),
        )
    result = await router.create_embedding_provider(
        router.EmbeddingProviderCreateRequest(
            name="C", provider_type="custom", base_url="http://provider"
        ),
        _ctx(),
    )
    assert result.provider.provider_id == "custom-custom"
    with pytest.raises(router.HTTPException):
        await router.create_embedding_provider(
            router.EmbeddingProviderCreateRequest(name="X", provider_type="unknown"),
            _ctx(),
        )

    assert (await router.delete_embedding_provider("bge-m3-local", _ctx()))[
        "success"
    ] is True
    with pytest.raises(router.HTTPException):
        await router.delete_embedding_provider("missing", _ctx())
    with pytest.raises(router.HTTPException):
        await router.switch_embedding_provider(
            router.EmbeddingProviderSwitchRequest(provider_id="missing"), _ctx()
        )
    switch = await router.switch_embedding_provider(
        router.EmbeddingProviderSwitchRequest(
            provider_id="openai-text-embedding-3-small"
        ),
        _ctx(),
    )
    assert switch.success is True


@pytest.mark.asyncio
async def test_embedding_provider_discovery_and_test_paths(monkeypatch):
    import encoding.embedding_providers as providers
    from api.routers import embedding_providers as router

    registry = _Registry()
    found = _EmbeddingProvider()
    registry.register("found", found)
    monkeypatch.setattr(
        providers, "get_tenant_embedding_registry", lambda _tenant: registry
    )
    monkeypatch.setattr(
        providers,
        "discover_local_models",
        lambda: [SimpleNamespace(name="model.bin")],
    )
    monkeypatch.setattr(providers, "LocalEmbeddingProvider", lambda _path: found)
    result = await router.create_embedding_provider(
        router.EmbeddingProviderCreateRequest(
            name="Found", provider_type="local", model="model.bin"
        ),
        _ctx(),
    )
    assert result.provider.provider_id == "local-model.bin"
    with pytest.raises(router.HTTPException) as exc:
        await router.create_embedding_provider(
            router.EmbeddingProviderCreateRequest(
                name="Missing", provider_type="local", model="not-here"
            ),
            _ctx(),
        )
    assert exc.value.status_code == 404

    with pytest.raises(router.HTTPException):
        await router.test_embedding_provider(
            "missing", router.EmbeddingProviderTestRequest(), _ctx()
        )
    registry.providers["offline"] = _EmbeddingProvider(available=False)
    offline = await router.test_embedding_provider(
        "offline", router.EmbeddingProviderTestRequest(), _ctx()
    )
    assert offline.success is False
    success = await router.test_embedding_provider(
        "found", router.EmbeddingProviderTestRequest(test_text="hello"), _ctx()
    )
    assert success.success is True and success.dimension == 3
    registry.providers["error"] = _EmbeddingProvider(error=True)
    failed = await router.test_embedding_provider(
        "error", router.EmbeddingProviderTestRequest(), _ctx()
    )
    assert failed.success is False and "failed" in failed.message


def _ocr_info(provider_id="custom"):
    return SimpleNamespace(
        id=provider_id,
        name=provider_id,
        display_name=provider_id.title(),
        provider_type="custom",
        languages=["eng"],
        is_free=True,
        description="ocr test",
        version="v1",
        is_local=True,
        config={},
    )


class _OCRProvider:
    def __init__(self, available=True, result="text", error=False):
        self.model_info = _ocr_info()
        self.available = available
        self.result = result
        self.error = error

    def is_available(self):
        return self.available

    def extract_image_bytes(self, *args, **kwargs):
        if self.error:
            raise RuntimeError("ocr failed")
        if self.result is None:
            return None
        return SimpleNamespace(text=self.result, confidence=0.9)


class _OCRRegistry(_Registry):
    def list_providers(self):
        rows = []
        for provider_id, provider in self.providers.items():
            info = provider.model_info
            rows.append(
                {
                    "id": provider_id,
                    "provider_id": provider_id,
                    "name": info.name,
                    "display_name": info.display_name,
                    "provider_type": info.provider_type,
                    "languages": info.languages,
                    "is_free": info.is_free,
                    "description": info.description,
                    "version": info.version,
                    "is_local": info.is_local,
                    "is_active": provider_id == self.active_id,
                    "is_available": provider.is_available(),
                    "status": "online" if provider.is_available() else "offline",
                    "config": info.config,
                }
            )
        return rows


@pytest.mark.asyncio
async def test_ocr_provider_routes_and_benchmark_paths(monkeypatch):
    from api.routers import ocr_providers as router

    registry = _OCRRegistry({"custom": _OCRProvider()}, "custom")
    monkeypatch.setattr(router, "get_ocr_registry", lambda: registry)
    listing = await router.list_ocr_providers(_ctx())
    assert listing.total == 1
    assert (await router.get_active_provider(_ctx())).provider_id == "custom"
    registry.active_id = None
    assert await router.get_active_provider(_ctx()) is None
    registry.active_id = "custom"

    with pytest.raises(router.HTTPException):
        await router.create_ocr_provider(
            router.OCRProviderCreateRequest(id="c", name="C"), _ctx()
        )
    custom = _OCRProvider()
    monkeypatch.setattr(router, "CustomOCRProvider", lambda **kwargs: custom)
    result = await router.create_ocr_provider(
        router.OCRProviderCreateRequest(
            id="c", name="C", base_url="http://ocr", provider_type="custom"
        ),
        _ctx(),
    )
    assert result.provider_id == "c"

    for provider_id, cls in (
        ("tesseract", lambda: _OCRProvider()),
        ("easyocr", lambda default_langs=None: _OCRProvider()),
        ("paddle", lambda: _OCRProvider()),
    ):
        if provider_id == "tesseract":
            monkeypatch.setattr(router, "TesseractOCRProvider", cls)
        elif provider_id == "easyocr":
            monkeypatch.setattr(router, "EasyOCRProvider", cls)
        else:
            monkeypatch.setattr(router, "PaddleOCRv6Provider", cls)
        made = await router.create_ocr_provider(
            router.OCRProviderCreateRequest(
                id=provider_id, name=provider_id, provider_type="local"
            ),
            _ctx(),
        )
        assert made.provider_id == provider_id
    with pytest.raises(router.HTTPException):
        await router.create_ocr_provider(
            router.OCRProviderCreateRequest(id="x", name="X", provider_type="cloud"),
            _ctx(),
        )

    with pytest.raises(router.HTTPException):
        await router.delete_ocr_provider("paddleocr_v6", _ctx())
    with pytest.raises(router.HTTPException):
        await router.delete_ocr_provider("missing", _ctx())
    assert (await router.delete_ocr_provider("c", _ctx()))["success"] is True
    with pytest.raises(router.HTTPException):
        await router.switch_ocr_provider(
            router.OCRProviderSwitchRequest(provider_id="missing"), _ctx()
        )
    switched = await router.switch_ocr_provider(
        router.OCRProviderSwitchRequest(provider_id="custom"), _ctx()
    )
    assert switched.success is True

    with pytest.raises(router.HTTPException):
        await router.test_ocr_provider(
            "missing", router.OCRProviderTestRequest(), _ctx()
        )
    registry.providers["offline"] = _OCRProvider(available=False)
    assert (
        await router.test_ocr_provider(
            "offline", router.OCRProviderTestRequest(), _ctx()
        )
    ).status == "offline"
    with pytest.raises(router.HTTPException):
        await router.test_ocr_provider(
            "custom", router.OCRProviderTestRequest(image_base64="A"), _ctx()
        )
    success = await router.test_ocr_provider(
        "custom", router.OCRProviderTestRequest(), _ctx()
    )
    assert success.success and success.extracted_text == "text"
    registry.providers["empty"] = _OCRProvider(result=None)
    assert (
        await router.test_ocr_provider("empty", router.OCRProviderTestRequest(), _ctx())
    ).success
    registry.providers["error"] = _OCRProvider(error=True)
    failed = await router.test_ocr_provider(
        "error", router.OCRProviderTestRequest(), _ctx()
    )
    assert failed.status == "error"
