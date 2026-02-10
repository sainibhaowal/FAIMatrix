"""Phase A: Storage contract freeze regression tests."""

from __future__ import annotations


def test_storage_contract_validator_passes_current_router():
    from api.contracts.storage_contract import validate_storage_router_contract
    from api.routers.storage import router

    result = validate_storage_router_contract(router.routes)
    assert result.ok, f"Contract violations: {result.errors}"


def test_storage_router_has_all_required_methods_and_paths():
    from api.contracts.storage_contract import REQUIRED_STORAGE_ROUTES
    from api.routers.storage import router
    from fastapi.routing import APIRoute

    observed = set()
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in sorted(route.methods or []):
            if method in {"HEAD", "OPTIONS"}:
                continue
            observed.add((method, route.path))

    missing = REQUIRED_STORAGE_ROUTES - observed
    assert not missing, f"Missing storage routes: {sorted(missing)}"


def test_storage_response_models_contain_minimum_required_fields():
    from api.contracts.storage_contract import REQUIRED_MODEL_FIELDS
    from api.routers import storage as storage_router_module

    models = {
        "StorageFileItem": storage_router_module.StorageFileItem,
        "StorageUploadBatchResponse": storage_router_module.StorageUploadBatchResponse,
        "StorageUploadStatusResponse": storage_router_module.StorageUploadStatusResponse,
        "StorageJobEventsResponse": storage_router_module.StorageJobEventsResponse,
        "StorageFileListResponse": storage_router_module.StorageFileListResponse,
        "StorageSummaryResponse": storage_router_module.StorageSummaryResponse,
        "StorageBackendsHealth": storage_router_module.StorageBackendsHealth,
        "StorageIngestActionResponse": storage_router_module.StorageIngestActionResponse,
    }

    for model_name, required_fields in REQUIRED_MODEL_FIELDS.items():
        model = models[model_name]
        fields = set(model.model_fields.keys())
        missing = required_fields - fields
        assert not missing, f"{model_name} missing required fields: {sorted(missing)}"

