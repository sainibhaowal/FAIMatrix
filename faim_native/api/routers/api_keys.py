"""FAIM-Native API: API key management router (K4).

Tenant-scoped API key lifecycle routes:
- create
- list
- rotate
- revoke
- audit timeline
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

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


# =============================================================================
# Contracts
# =============================================================================


ALLOWED_KEY_SCOPES = {
    "keys.read",
    "keys.write",
    "memory.read",
    "memory.write",
    "memory.admin",
}


class APIKeyItem(BaseModel):
    tenant_id: str
    key_id: str
    key_prefix: str
    scopes: List[str]
    created_at: Optional[str] = None
    created_by: Optional[str] = None
    expires_at: Optional[str] = None
    revoked_at: Optional[str] = None
    revoked_reason: Optional[str] = None
    rotated_from_key_id: Optional[str] = None
    last_used_at: Optional[str] = None
    is_active: bool


class APIKeyCreateRequest(BaseModel):
    label: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None


class APIKeyCreateResponse(BaseModel):
    key: APIKeyItem
    plaintext_key: str


class APIKeyListResponse(BaseModel):
    items: List[APIKeyItem]
    total: int
    include_revoked: bool


class APIKeyRotateRequest(BaseModel):
    reason: Optional[str] = None
    scopes: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


class APIKeyRotateResponse(BaseModel):
    old_key: APIKeyItem
    new_key: APIKeyItem
    plaintext_key: str


class APIKeyRevokeRequest(BaseModel):
    reason: Optional[str] = None


class APIKeyRevokeResponse(BaseModel):
    key: APIKeyItem


class APIKeyAuditItem(BaseModel):
    id: str
    tenant_id: str
    key_id: str
    action: str
    actor: Optional[str] = None
    request_id: Optional[str] = None
    meta: Dict[str, Any]
    created_at: Optional[str] = None


class APIKeyAuditResponse(BaseModel):
    items: List[APIKeyAuditItem]
    total: int
    limit: int


# =============================================================================
# Helpers
# =============================================================================


def _normalize_expiry(expires_at: Optional[datetime]) -> Optional[datetime]:
    if expires_at is None:
        return None
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at.astimezone(timezone.utc)


def _validate_expiry(expires_at: Optional[datetime]) -> Optional[datetime]:
    normalized = _normalize_expiry(expires_at)
    if normalized is None:
        return None
    if normalized <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="expires_at must be in the future")
    return normalized


def _normalize_scope_list(scopes: Optional[List[str]]) -> List[str]:
    if scopes is None:
        return []

    normalized: List[str] = []
    seen: set[str] = set()
    for scope in scopes:
        value = str(scope or "").strip()
        if not value or value in seen:
            continue
        if value not in ALLOWED_KEY_SCOPES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid scope: {value}",
            )
        normalized.append(value)
        seen.add(value)
    return normalized


def _actor_from_request(request: Request) -> Optional[str]:
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"

    key_id = getattr(request.state, "auth_key_id", None)
    if key_id:
        return f"key:{key_id}"

    auth_method = getattr(request.state, "auth_method", None)
    if auth_method:
        return f"{auth_method}:tenant"
    return None


def _request_id(ctx: FAIMContext, request: Request) -> str:
    return str(
        ctx.request_id
        or getattr(request.state, "request_id", None)
        or "unknown"
    )


def _serialize_key(record) -> APIKeyItem:  # noqa: ANN001
    return APIKeyItem(**record.to_dict())


def _repo_from_ctx(ctx: FAIMContext) -> AuthRepo:
    if not ctx.session:
        raise HTTPException(status_code=500, detail="Database session unavailable")
    return AuthRepo(ctx.session)


# =============================================================================
# Routes
# =============================================================================


@router.post(
    "",
    response_model=APIKeyCreateResponse,
    dependencies=[Depends(require_scopes(["keys.write"]))],
)
async def create_api_key(
    body: APIKeyCreateRequest,
    request: Request,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> APIKeyCreateResponse:
    scopes = _normalize_scope_list(body.scopes)
    if not scopes:
        raise HTTPException(status_code=422, detail="At least one scope is required")

    expires_at = _validate_expiry(body.expires_at)
    actor = _actor_from_request(request)
    request_id = _request_id(ctx, request)
    label = (body.label or "").strip() or None

    repo = _repo_from_ctx(ctx)
    try:
        record, plaintext = repo.create_tenant_key(
            tenant_id=ctx.tenant_id,
            scopes=scopes,
            expires_at=expires_at,
            created_by=actor,
            audit_actor=actor,
            request_id=request_id,
        )
        if label:
            repo.append_key_audit(
                tenant_id=ctx.tenant_id,
                key_id=record.key_id,
                action="labeled",
                actor=actor,
                request_id=request_id,
                meta={"label": label},
            )
        ctx.session.commit()
        return APIKeyCreateResponse(
            key=_serialize_key(record),
            plaintext_key=plaintext,
        )
    except HTTPException:
        ctx.session.rollback()
        raise
    except Exception as exc:
        ctx.session.rollback()
        logger.error("API key create failed for tenant=%s: %s", ctx.tenant_id, exc)
        raise HTTPException(status_code=500, detail="Failed to create API key") from exc


@router.get(
    "",
    response_model=APIKeyListResponse,
    dependencies=[Depends(require_scopes(["keys.read"]))],
)
async def list_api_keys(
    include_revoked: bool = Query(False),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> APIKeyListResponse:
    repo = _repo_from_ctx(ctx)
    try:
        records = repo.list_tenant_keys(
            tenant_id=ctx.tenant_id,
            include_revoked=include_revoked,
        )
        items = [_serialize_key(record) for record in records]
        return APIKeyListResponse(
            items=items,
            total=len(items),
            include_revoked=include_revoked,
        )
    except Exception as exc:
        logger.error("API key list failed for tenant=%s: %s", ctx.tenant_id, exc)
        raise HTTPException(status_code=500, detail="Failed to list API keys") from exc


@router.post(
    "/{key_id}/rotate",
    response_model=APIKeyRotateResponse,
    dependencies=[Depends(require_scopes(["keys.write"]))],
)
async def rotate_api_key(
    key_id: str,
    body: APIKeyRotateRequest,
    request: Request,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> APIKeyRotateResponse:
    target_key_id = str(key_id or "").strip()
    if not target_key_id:
        raise HTTPException(status_code=422, detail="key_id is required")

    expires_at = _validate_expiry(body.expires_at)
    requested_scopes = (
        _normalize_scope_list(body.scopes)
        if body.scopes is not None
        else None
    )
    actor = _actor_from_request(request)
    request_id = _request_id(ctx, request)

    repo = _repo_from_ctx(ctx)
    existing = repo.get_tenant_key(ctx.tenant_id, target_key_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="API key not found")
    if existing.revoked_at is not None:
        raise HTTPException(status_code=409, detail="API key is already revoked")

    try:
        rotated = repo.rotate_tenant_key(
            tenant_id=ctx.tenant_id,
            key_id=target_key_id,
            scopes=requested_scopes,
            expires_at=expires_at,
            reason=(body.reason or "").strip() or None,
            actor=actor,
            request_id=request_id,
        )
        if rotated is None:
            ctx.session.rollback()
            raise HTTPException(status_code=404, detail="API key not found")

        old_record, new_record, plaintext = rotated
        ctx.session.commit()
        return APIKeyRotateResponse(
            old_key=_serialize_key(old_record),
            new_key=_serialize_key(new_record),
            plaintext_key=plaintext,
        )
    except HTTPException:
        raise
    except Exception as exc:
        ctx.session.rollback()
        logger.error("API key rotate failed for tenant=%s: %s", ctx.tenant_id, exc)
        raise HTTPException(status_code=500, detail="Failed to rotate API key") from exc


@router.post(
    "/{key_id}/revoke",
    response_model=APIKeyRevokeResponse,
    dependencies=[Depends(require_scopes(["keys.write"]))],
)
async def revoke_api_key(
    key_id: str,
    body: APIKeyRevokeRequest,
    request: Request,
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> APIKeyRevokeResponse:
    target_key_id = str(key_id or "").strip()
    if not target_key_id:
        raise HTTPException(status_code=422, detail="key_id is required")

    repo = _repo_from_ctx(ctx)
    existing = repo.get_tenant_key(ctx.tenant_id, target_key_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="API key not found")
    if existing.revoked_at is not None:
        raise HTTPException(status_code=409, detail="API key is already revoked")

    actor = _actor_from_request(request)
    request_id = _request_id(ctx, request)
    reason = (body.reason or "").strip() or None

    try:
        record = repo.revoke_tenant_key(
            tenant_id=ctx.tenant_id,
            key_id=target_key_id,
            reason=reason,
            actor=actor,
            request_id=request_id,
        )
        if record is None:
            ctx.session.rollback()
            raise HTTPException(status_code=404, detail="API key not found")

        ctx.session.commit()
        return APIKeyRevokeResponse(key=_serialize_key(record))
    except HTTPException:
        raise
    except Exception as exc:
        ctx.session.rollback()
        logger.error("API key revoke failed for tenant=%s: %s", ctx.tenant_id, exc)
        raise HTTPException(status_code=500, detail="Failed to revoke API key") from exc


@router.get(
    "/audit",
    response_model=APIKeyAuditResponse,
    dependencies=[Depends(require_scopes(["keys.read"]))],
)
async def list_api_key_audit(
    key_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(default=100, ge=1, le=500),
    ctx: FAIMContext = Depends(get_faim_context),  # noqa: B008
) -> APIKeyAuditResponse:
    repo = _repo_from_ctx(ctx)
    try:
        events = repo.list_key_audit(
            tenant_id=ctx.tenant_id,
            key_id=(key_id or "").strip() or None,
            action=(action or "").strip() or None,
            limit=limit,
        )
        items = [APIKeyAuditItem(**event.to_dict()) for event in events]
        return APIKeyAuditResponse(
            items=items,
            total=len(items),
            limit=limit,
        )
    except Exception as exc:
        logger.error("API key audit list failed for tenant=%s: %s", ctx.tenant_id, exc)
        raise HTTPException(status_code=500, detail="Failed to list API key audit") from exc

