"""Phase K5 unit tests: memory router contract guardrails."""

from __future__ import annotations

import inspect


def test_k5_memory_router_exports_expected_handlers():
    from api.routers import memory as memory_router_module

    assert callable(memory_router_module.memory_search)
    assert callable(memory_router_module.get_memory_item)
    assert callable(memory_router_module.get_memory_provenance)
    assert callable(memory_router_module.write_memory)
    assert callable(memory_router_module.patch_memory_item)


def test_k5_write_endpoint_supports_idempotency_header():
    from api.routers.memory import write_memory

    signature = inspect.signature(write_memory)
    assert "idempotency_key_header" in signature.parameters


def test_k5_patch_endpoint_uses_expected_updated_at_guard():
    from api.routers.memory import patch_memory_item

    source = inspect.getsource(patch_memory_item)
    assert "expected_updated_at" in source
    assert "status_code=409" in source
