"""Embedding Provider Abstraction Layer.

Provides a unified interface for multiple embedding models (local, cloud, custom).
Supports BAAI/bge-m3 as the primary local model, with OpenAI and custom endpoints.
"""

from __future__ import annotations

import logging
import os
import site
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

_user_site = site.getusersitepackages()
if _user_site and _user_site not in sys.path and Path(_user_site).exists():
    sys.path.append(_user_site)

logger = logging.getLogger(__name__)

# Directory where pre-downloaded local embedding models live.
# e.g. models/embeddings/BAAI-bge-small-en-v1.5, models/embeddings/bge-m3, ...
LOCAL_MODELS_DIR = Path(__file__).parent.parent / "models" / "embeddings"


@dataclass(frozen=True)
class EmbeddingModelInfo:
    """Metadata about an embedding model."""
    name: str
    display_name: str
    provider_type: str
    dimension: int
    max_tokens: int
    is_free: bool
    description: str
    languages: List[str]
    model_path: Optional[str] = None


@dataclass(frozen=True)
class EmbeddingResult:
    """Result of embedding generation."""
    vectors: List[List[float]]
    dimension: int
    model_name: str
    token_count: int


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @property
    @abstractmethod
    def model_info(self) -> EmbeddingModelInfo:
        """Return model metadata."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is ready (model loaded, API reachable)."""
        pass

    @abstractmethod
    def encode(self, texts: List[str]) -> EmbeddingResult:
        """Generate embeddings for a list of texts."""
        pass

    @abstractmethod
    def encode_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass


def _read_model_dimension(model_path: Path) -> Optional[int]:
    """Read embedding dimension from a model's config.json (hidden_size)."""
    try:
        config_file = model_path / "config.json"
        if not config_file.exists():
            return None
        import json
        with open(config_file, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        return int(cfg.get("hidden_size") or 0) or None
    except Exception as e:
        logger.warning(f"Failed to read dimension from {model_path}: {e}")
        return None


def _read_model_name(model_path: Path) -> str:
    """Derive a clean model id from a model directory name."""
    return model_path.name


def discover_local_models(models_dir: Optional[Path] = None) -> List[Path]:
    """Scan the local models directory and return paths of usable model folders.

    A folder is considered a usable sentence-transformers model when it contains
    a config.json and either modules.json or a tokenizer file.
    """
    base = Path(models_dir) if models_dir is not None else LOCAL_MODELS_DIR
    if not base.exists():
        return []
    found: List[Path] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name.startswith("_"):
            continue
        has_config = (child / "config.json").exists()
        has_modules = (child / "modules.json").exists()
        has_tokenizer = (
            (child / "tokenizer.json").exists()
            or (child / "tokenizer_config.json").exists()
            or (child / "vocab.txt").exists()
            or (child / "sentencepiece.bpe.model").exists()
        )
        if has_config and (has_modules or has_tokenizer):
            found.append(child)
    return found


class LocalEmbeddingProvider(EmbeddingProvider):
    """A local sentence-transformers embedding model loaded from a directory.

    Pre-downloaded models are auto-discovered and pre-registered so they can be
    used directly with no API key or server required.
    """

    def __init__(self, model_dir: str, display_name: Optional[str] = None, device: Optional[str] = None):
        self._model_path = Path(model_dir)
        self._display_name = display_name or self._model_path.name
        self._dimension = _read_model_dimension(self._model_path) or 384
        self._device = device or os.environ.get("FAIM_EMBEDDING_DEVICE", "cpu")
        self._model = None
        self._model_loaded = False

    @property
    def model_info(self) -> EmbeddingModelInfo:
        return EmbeddingModelInfo(
            name=self._model_path.name,
            display_name=self._display_name,
            provider_type="local",
            dimension=self._dimension,
            max_tokens=8192,
            is_free=True,
            description=f"Local model from {self._model_path}",
            languages=["100+ languages"],
            model_path=str(self._model_path) if self._model_path.exists() else None,
        )

    def is_available(self) -> bool:
        if not self._model_path.exists():
            return False
        # Fast availability check: model files present. Weights load lazily on encode().
        return True

    def _load_model(self) -> None:
        if self._model_loaded:
            return
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading local model from {self._model_path} on device={self._device}")
            self._model = SentenceTransformer(str(self._model_path), device=self._device)
            self._model_loaded = True
            logger.info(f"Local model {self._model_path.name} loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load local model {self._model_path}: {e}")
            self._model = None
            self._model_loaded = True

    def encode(self, texts: List[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(
                vectors=[],
                dimension=self._dimension,
                model_name=self._model_path.name,
                token_count=0,
            )
        if not self.is_available():
            raise RuntimeError(
                f"Local model {self._model_path.name} not available. "
                f"Expected model files at {self._model_path}."
            )
        if not self._model_loaded:
            self._load_model()
        if self._model is None:
            raise RuntimeError(
                f"Local model {self._model_path.name} failed to load from {self._model_path}."
            )
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return EmbeddingResult(
            vectors=embeddings.tolist(),
            dimension=self._dimension,
            model_name=self._model_path.name,
            token_count=sum(len(t.split()) for t in texts),
        )

    def encode_single(self, text: str) -> List[float]:
        result = self.encode([text])
        return result.vectors[0] if result.vectors else [0.0] * self._dimension


class BgeM3LocalProvider(EmbeddingProvider):
    """BAAI/bge-m3 local provider (multilingual, 1024-dim, 8192 tokens)."""

    def __init__(self, model_dir: Optional[str] = None, device: Optional[str] = None):
        self._model_dir = model_dir or os.environ.get(
            "FAIM_EMBEDDING_MODEL_DIR",
            str(Path(__file__).parent.parent / "models")
        )
        self._device = device or os.environ.get("FAIM_EMBEDDING_DEVICE", "cpu")
        candidates = [
            Path(self._model_dir) / "bge-m3",
            LOCAL_MODELS_DIR / "bge-m3",
            LOCAL_MODELS_DIR / "BAAI-bge-m3",
            Path(self._model_dir) / "BAAI-bge-m3",
        ]
        existing = next((c for c in candidates if c.exists()), None)
        if existing:
            self._model_name_or_path = str(existing)
            self._dimension = _read_model_dimension(existing) or 1024
        else:
            self._model_name_or_path = "BAAI/bge-m3"
            self._dimension = 1024

        self._model = None
        self._model_loaded = False

    @property
    def model_info(self) -> EmbeddingModelInfo:
        return EmbeddingModelInfo(
            name="bge-m3",
            display_name="BAAI/bge-m3 (Local)",
            provider_type="local",
            dimension=1024,
            max_tokens=8192,
            is_free=True,
            description=f"BAAI/bge-m3 1024-dim local embedding model ({self._model_name_or_path})",
            languages=["100+ languages"],
            model_path=self._model_name_or_path if Path(self._model_name_or_path).exists() else None,
        )

    def is_available(self) -> bool:
        return True

    def _load_model(self) -> None:
        """Lazy load the sentence-transformers model."""
        if self._model_loaded:
            return
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading BAAI/bge-m3 from {self._model_name_or_path} on device={self._device}")
            self._model = SentenceTransformer(self._model_name_or_path, device=self._device)
            self._model_loaded = True
            logger.info("BAAI/bge-m3 loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load BAAI/bge-m3: {e}")
            self._model = None
            self._model_loaded = True

    def encode(self, texts: List[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(
                vectors=[],
                dimension=1024,
                model_name="bge-m3",
                token_count=0,
            )
        if not self._model_loaded:
            self._load_model()
        if self._model is None:
            raise RuntimeError(f"BAAI/bge-m3 model failed to load from {self._model_name_or_path}.")

        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return EmbeddingResult(
            vectors=embeddings.tolist(),
            dimension=embeddings.shape[1] if hasattr(embeddings, "shape") and len(embeddings.shape) > 1 else 1024,
            model_name="bge-m3",
            token_count=sum(len(t.split()) for t in texts),
        )

    def encode_single(self, text: str) -> List[float]:
        result = self.encode([text])
        return result.vectors[0] if result.vectors else [0.0] * 1024


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider (text-embedding-3-small/large)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"):
        self._api_key = api_key or os.environ.get("FAIM_OPENAI_EMBEDDING_KEY")
        self._model = model
        self._dimension = 1536 if "large" in model else 1536
        self._client = None

    @property
    def model_info(self) -> EmbeddingModelInfo:
        return EmbeddingModelInfo(
            name=self._model,
            display_name=f"OpenAI {self._model}",
            provider_type="openai",
            dimension=self._dimension,
            max_tokens=8192,
            is_free=False,
            description=f"OpenAI {self._model} embedding API",
            languages=["100+ languages"],
        )

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _get_client(self):
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self._api_key)
            except Exception as e:
                logger.error(f"Failed to init OpenAI client: {e}")
                raise
        return self._client

    def encode(self, texts: List[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(vectors=[], dimension=self._dimension, model_name=self._model, token_count=0)
        if not self.is_available():
            raise RuntimeError("OpenAI API key not configured")

        client = self._get_client()
        response = client.embeddings.create(model=self._model, input=texts)
        embeddings = [d.embedding for d in response.data]
        return EmbeddingResult(
            vectors=embeddings,
            dimension=self._dimension,
            model_name=self._model,
            token_count=response.usage.total_tokens if response.usage else 0,
        )

    def encode_single(self, text: str) -> List[float]:
        result = self.encode([text])
        return result.vectors[0] if result.vectors else [0.0] * self._dimension


class CustomEmbeddingProvider(EmbeddingProvider):
    """Custom OpenAI-compatible embedding endpoint."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        model: str = "custom",
        dimension: int = 1024,
    ):
        self._base_url = base_url.rstrip("/")
        if not self._base_url.endswith("/v1"):
            self._base_url += "/v1"
        self._api_key = api_key
        self._model = model
        self._dimension = dimension

    @property
    def model_info(self) -> EmbeddingModelInfo:
        return EmbeddingModelInfo(
            name=self._model,
            display_name=f"Custom: {self._model}",
            provider_type="custom",
            dimension=self._dimension,
            max_tokens=8192,
            is_free=True,
            description=f"Custom OpenAI-compatible endpoint at {self._base_url}",
            languages=["Depends on model"],
        )

    def is_available(self) -> bool:
        return True

    def _make_request(self, texts: List[str]) -> List[List[float]]:
        import urllib.request
        import json

        url = f"{self._base_url}/embeddings"
        data = {"model": self._model, "input": texts}
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode(),
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}),
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return [d["embedding"] for d in result["data"]]

    def encode(self, texts: List[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(vectors=[], dimension=self._dimension, model_name=self._model, token_count=0)
        embeddings = self._make_request(texts)
        return EmbeddingResult(
            vectors=embeddings,
            dimension=self._dimension,
            model_name=self._model,
            token_count=sum(len(t.split()) for t in texts),
        )

    def encode_single(self, text: str) -> List[float]:
        result = self.encode([text])
        return result.vectors[0] if result.vectors else [0.0] * self._dimension


class EmbeddingProviderRegistry:
    """Registry for managing multiple embedding providers."""

    def __init__(self):
        self._providers: Dict[str, EmbeddingProvider] = {}
        self._active_provider_id: Optional[str] = None
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register built-in providers: all pre-downloaded local models."""
        # Always try bge-m3 first (kept for backwards compatibility)
        self.register("bge-m3-local", BgeM3LocalProvider())

        # Auto-register every pre-downloaded model in models/embeddings/
        first_local: Optional[str] = None
        for model_path in discover_local_models():
            name = model_path.name
            provider_id = f"local-{name}"
            if provider_id in self._providers:
                continue
            display = name
            if name.startswith("BAAI-"):
                display = f"BAAI/{name.replace('BAAI-', '')}"
            elif name.startswith("intfloat-"):
                display = name.replace("intfloat-", "intfloat/")
            logger.info(f"Pre-registered local embedding model: {provider_id} ({display})")
            self.register(provider_id, LocalEmbeddingProvider(str(model_path), display_name=display))
            if first_local is None:
                first_local = provider_id

        # Prefer an actually downloaded local model over the default bge-m3 slot
        self._active_provider_id = first_local or "bge-m3-local"

    def register(self, provider_id: str, provider: EmbeddingProvider) -> None:
        self._providers[provider_id] = provider

    def unregister(self, provider_id: str) -> bool:
        if provider_id in self._providers:
            del self._providers[provider_id]
            if self._active_provider_id == provider_id:
                self._active_provider_id = next(iter(self._providers), None)
            return True
        return False

    def get(self, provider_id: str) -> Optional[EmbeddingProvider]:
        return self._providers.get(provider_id)

    def list_providers(self) -> List[Dict[str, Any]]:
        result = []
        for pid, provider in self._providers.items():
            info = provider.model_info
            result.append({
                "id": pid,
                "provider_id": pid,
                "tenant_id": "default",
                "name": info.name,
                "display_name": info.display_name,
                "provider_type": info.provider_type,
                "dimension": info.dimension,
                "max_tokens": info.max_tokens,
                "is_free": info.is_free,
                "description": info.description,
                "languages": info.languages,
                "is_active": pid == self._active_provider_id,
                "is_available": provider.is_available(),
                "model_path": info.model_path,
                "status": "online" if provider.is_available() else "offline",
            })
        return result

    def set_active(self, provider_id: str) -> bool:
        if provider_id in self._providers:
            self._active_provider_id = provider_id
            return True
        return False

    def get_active(self) -> Optional[EmbeddingProvider]:
        if self._active_provider_id:
            return self._providers.get(self._active_provider_id)
        return next(iter(self._providers.values()), None)

    def get_active_id(self) -> Optional[str]:
        return self._active_provider_id


_global_registry: Optional[EmbeddingProviderRegistry] = None


def get_embedding_registry() -> EmbeddingProviderRegistry:
    """Get the global embedding provider registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = EmbeddingProviderRegistry()
    return _global_registry


def reset_embedding_registry() -> None:
    """Reset registry (for testing)."""
    global _global_registry
    _global_registry = None


# -----------------------------------------------------------------------------
# Tenant-scoped registry (Stage-14: multi-tenant provider isolation)
# -----------------------------------------------------------------------------
#
# Embedding providers must never leak across tenants: tenant A's API keys,
# custom endpoints, or active-provider selection must be invisible to tenant B.
# We keep one lazily-instantiated shared registry (cheap to build: only model
# metadata is loaded eagerly) and give each tenant an isolated facade that
# shadows provider registrations, active selection, and provider state.
#
# The per-tenant facade shares the underlying default local providers (model
# files are expensive to reload) but isolates anything a tenant mutates:
#   - registered providers added via the API
#   - the active provider id
#   - provider availability overrides

_TENANT_REGISTRIES: Dict[str, EmbeddingProviderRegistry] = {}


class TenantEmbeddingRegistry:
    """Tenant-isolated embedding provider registry facade."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        # Per-tenant overrides only; defaults resolve through the shared registry.
        self._overrides: Dict[str, EmbeddingProvider] = {}
        self._active_override: Optional[str] = None

    # --- underlying provider lookup -----------------------------------------
    def _shared(self) -> EmbeddingProviderRegistry:
        return get_embedding_registry()

    def get(self, provider_id: str) -> Optional[EmbeddingProvider]:
        if provider_id in self._overrides:
            return self._overrides[provider_id]
        return self._shared().get(provider_id)

    def list_providers(self) -> List[Dict[str, Any]]:
        shared = self._shared()
        items = {}
        for pid, provider in shared._providers.items():
            info = provider.model_info
            items[pid] = {
                "id": pid,
                "provider_id": pid,
                "tenant_id": self.tenant_id,
                "name": info.name,
                "display_name": info.display_name,
                "provider_type": info.provider_type,
                "dimension": info.dimension,
                "max_tokens": info.max_tokens,
                "is_free": info.is_free,
                "description": info.description,
                "languages": info.languages,
                "is_active": pid == self.get_active_id(),
                "is_available": provider.is_available(),
                "model_path": info.model_path,
                "status": "online" if provider.is_available() else "offline",
            }
        for pid, provider in self._overrides.items():
            info = provider.model_info
            items[pid] = {
                "id": pid,
                "provider_id": pid,
                "tenant_id": self.tenant_id,
                "name": info.name,
                "display_name": info.display_name,
                "provider_type": info.provider_type,
                "dimension": info.dimension,
                "max_tokens": info.max_tokens,
                "is_free": info.is_free,
                "description": info.description,
                "languages": info.languages,
                "is_active": pid == self.get_active_id(),
                "is_available": provider.is_available(),
                "model_path": info.model_path,
                "status": "online" if provider.is_available() else "offline",
            }
        return list(items.values())

    def register(self, provider_id: str, provider: EmbeddingProvider) -> None:
        self._overrides[provider_id] = provider

    def unregister(self, provider_id: str) -> bool:
        if provider_id in self._overrides:
            del self._overrides[provider_id]
            if self._active_override == provider_id:
                self._active_override = None
            return True
        # Fall back to shared: a tenant cannot unregister shared defaults.
        if provider_id in self._shared()._providers:
            return False
        return False

    def set_active(self, provider_id: str) -> bool:
        if self.get(provider_id) is not None:
            self._active_override = provider_id
            return True
        return False

    def get_active_id(self) -> Optional[str]:
        if self._active_override:
            return self._active_override
        return self._shared().get_active_id()

    def get_active(self) -> Optional[EmbeddingProvider]:
        active_id = self.get_active_id()
        if active_id:
            return self.get(active_id)
        return None


def get_tenant_embedding_registry(tenant_id: str) -> TenantEmbeddingRegistry:
    """Get (and cache) the tenant-isolated embedding provider registry."""
    global _TENANT_REGISTRIES
    if tenant_id not in _TENANT_REGISTRIES:
        _TENANT_REGISTRIES[tenant_id] = TenantEmbeddingRegistry(tenant_id)
    return _TENANT_REGISTRIES[tenant_id]


def reset_tenant_embedding_registries() -> None:
    """Reset tenant-scoped registries (for testing)."""
    global _TENANT_REGISTRIES
    _TENANT_REGISTRIES = {}


def get_active_embedding_provider() -> Optional[EmbeddingProvider]:
    """Get the currently active embedding provider (shared default)."""
    return get_embedding_registry().get_active()


def encode_texts(texts: List[str]) -> EmbeddingResult:
    """Encode texts using the active embedding provider."""
    provider = get_active_embedding_provider()
    if provider is None:
        raise RuntimeError("No embedding provider available")
    return provider.encode(texts)


def encode_single(text: str) -> List[float]:
    """Encode single text using the active embedding provider."""
    provider = get_active_embedding_provider()
    if provider is None:
        raise RuntimeError("No embedding provider available")
    return provider.encode_single(text)