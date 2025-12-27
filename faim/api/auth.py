from __future__ import annotations

import os
import secrets
from fastapi import HTTPException, Request

from faim.config import FaimSettings
settings = FaimSettings.from_env()


def _api_key_required() -> bool:
    flag = (os.getenv("FAIM_REQUIRE_API_KEY") or "").strip().lower()
    if flag in ("1", "true", "yes", "y", "on"):
        return True
    mode = str(getattr(settings, "mode", "")).strip().lower()
    return mode in ("production", "prod")


def _extract_key(request: Request) -> str:
    header = (request.headers.get("X-FAIM-KEY") or "").strip()
    if header:
        return header
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def _admin_key_value() -> str:
    return (os.getenv("FAIM_ADMIN_KEY") or "").strip()


def _admin_key_valid(request: Request) -> bool:
    admin = _admin_key_value()
    if not admin:
        return False
    supplied = (request.headers.get("X-FAIM-ADMIN-KEY") or "").strip()
    if not supplied:
        return False
    return secrets.compare_digest(supplied, admin)


def require_api_key(request: Request) -> None:
    if not _api_key_required():
        return
    key = _extract_key(request)
    if not key:
        raise HTTPException(status_code=401, detail="Missing FAIM API key")
    from faim.api.keys import verify_key, _user_id

    uid = _user_id(request)
    if not verify_key(uid, key):
        raise HTTPException(status_code=403, detail="Invalid FAIM API key")


def require_admin_or_api_key(request: Request) -> None:
    if not _api_key_required():
        return
    if _allow_key_bootstrap(request):
        return
    admin = _admin_key_value()
    if admin:
        if _admin_key_valid(request):
            return
        raise HTTPException(status_code=401, detail="Missing or invalid FAIM admin key")
    require_api_key(request)


def _allow_key_bootstrap(request: Request) -> bool:
    flag = (os.getenv("FAIM_ALLOW_KEY_BOOTSTRAP") or "").strip().lower()
    if flag not in ("1", "true", "yes", "y", "on"):
        return False
    if request.method.upper() != "POST":
        return False
    if not request.url.path.endswith("/keys"):
        return False
    if _admin_key_value():
        return False
    try:
        from faim.api import keys as keymod

        data = keymod._load_store()
        users = data.get("users", {})
        for items in users.values():
            if items:
                return False
        return True
    except Exception:
        return False
