"""Unit tests verifying bidirectional GPU/CPU and Granite/Pure-FAIM fallbacks."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from faim_native.encoding.embedding_providers import (
    _encode_sentence_transformer_with_fallback,
    _resolve_embedding_device,
)


def test_resolve_embedding_device_falls_back_to_cpu_when_vram_low() -> None:
    """When CUDA free VRAM is below FAIM_MIN_CUDA_FREE_MIB, auto resolves to cpu."""
    fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: True))
    with (
        patch.dict(sys.modules, {"torch": fake_torch}),
        patch(
            "faim_native.encoding.embedding_providers._has_sufficient_cuda_vram",
            return_value=False,
        ),
    ):
        assert _resolve_embedding_device("auto") == "cpu"


def test_resolve_embedding_device_uses_cuda_when_vram_sufficient() -> None:
    """When CUDA free VRAM meets FAIM_MIN_CUDA_FREE_MIB, auto resolves to cuda."""
    fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: True))
    with (
        patch.dict(sys.modules, {"torch": fake_torch}),
        patch(
            "faim_native.encoding.embedding_providers._has_sufficient_cuda_vram",
            return_value=True,
        ),
    ):
        assert _resolve_embedding_device("auto") == "cuda"


def test_resolve_embedding_device_falls_back_to_cpu_when_no_gpu() -> None:
    """When CUDA is unavailable, auto resolves cleanly to cpu."""
    fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
    with patch.dict(sys.modules, {"torch": fake_torch}):
        assert _resolve_embedding_device("auto") == "cpu"


def test_cuda_encode_error_falls_back_to_cpu_cleanly() -> None:
    """If CUDA encode fails at runtime, Granite transparently falls back to CPU."""
    cuda_model = MagicMock()
    cuda_model.encode.side_effect = RuntimeError("CUDA out of memory")
    cpu_model = MagicMock()
    cpu_model.encode.return_value = [[0.1, 0.2]]

    with patch(
        "faim_native.encoding.embedding_providers._load_sentence_transformer_on_device",
        return_value=(cpu_model, "cpu"),
    ):
        emb, used_model, used_device = _encode_sentence_transformer_with_fallback(
            cuda_model,
            "ibm-granite/granite-embedding-97m-multilingual-r2",
            "cuda",
            ["hello world"],
        )

    assert emb == [[0.1, 0.2]]
    assert used_model is cpu_model
    assert used_device == "cpu"
