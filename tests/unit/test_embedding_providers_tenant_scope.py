"""Unit tests: tenant-scoped embedding provider registry isolation."""

from __future__ import annotations

import pytest


def _make_dummy_provider():
    from types import SimpleNamespace

    class _P:
        is_available = lambda self: True  # noqa: E731

        @property
        def model_info(self):
            return SimpleNamespace(
                name="dummy",
                display_name="Dummy",
                provider_type="custom",
                dimension=8,
                max_tokens=512,
                is_free=True,
                description="test provider",
                languages=["en"],
                model_path=None,
            )

        def encode(self, texts):
            return None

        def encode_single(self, text):
            return [0.0] * 8

    return _P()


def test_tenant_registries_isolate_registration():
    from encoding.embedding_providers import (
        get_tenant_embedding_registry,
        reset_tenant_embedding_registries,
    )

    reset_tenant_embedding_registries()
    try:
        reg_a = get_tenant_embedding_registry("tenant-a")
        reg_b = get_tenant_embedding_registry("tenant-b")

        reg_a.register("custom-a", _make_dummy_provider())

        assert reg_a.get("custom-a") is not None
        assert reg_b.get("custom-a") is None
    finally:
        reset_tenant_embedding_registries()


def test_tenant_active_selection_is_isolated():
    from encoding.embedding_providers import (
        get_tenant_embedding_registry,
        reset_tenant_embedding_registries,
    )

    reset_tenant_embedding_registries()
    try:
        reg_a = get_tenant_embedding_registry("tenant-a")
        reg_b = get_tenant_embedding_registry("tenant-b")

        reg_a.register("custom-a", _make_dummy_provider())
        assert reg_a.set_active("custom-a") is True
        assert reg_b.set_active("custom-a") is False  # invisible to tenant B

        assert reg_a.get_active_id() == "custom-a"
        assert reg_b.get_active_id() != "custom-a"

        # Tenant B's list does not include tenant A's provider.
        ids_b = {p["provider_id"] for p in reg_b.list_providers()}
        assert "custom-a" not in ids_b
    finally:
        reset_tenant_embedding_registries()


def test_tenant_unregister_does_not_affect_shared():
    from encoding.embedding_providers import (
        get_tenant_embedding_registry,
        reset_tenant_embedding_registries,
    )

    reset_tenant_embedding_registries()
    try:
        reg_a = get_tenant_embedding_registry("tenant-a")
        reg_b = get_tenant_embedding_registry("tenant-b")

        reg_a.register("custom-a", _make_dummy_provider())
        assert reg_a.unregister("custom-a") is True
        assert reg_b.get("custom-a") is None
        # Shared defaults cannot be removed by a tenant.
        assert reg_a.unregister("bge-m3-local") is False
    finally:
        reset_tenant_embedding_registries()