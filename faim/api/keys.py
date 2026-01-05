from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from faim.api.auth import allow_dev_mode
from faim.config import FaimSettings

settings = FaimSettings.from_env()
_lock = threading.Lock()


def _store_path() -> Path:
    root = settings.root
    p = root / "Runtime" / "Keys" / "faim_api_keys.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_store() -> Dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {"users": {}}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {"users": {}}
    except Exception:
        return {"users": {}}


def _save_store(data: Dict[str, Any]) -> None:
    path = _store_path()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _user_id(request: Request) -> str:
    uid = (request.headers.get("X-FAIM-USER") or request.headers.get("X-User-Id") or "").strip()
    return uid if uid else "local"


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _new_key() -> str:
    token = secrets.token_hex(24)
    return f"faim_live_{token}"


def verify_key(user_id: str, key: str) -> bool:
    key = (key or "").strip()
    if not key:
        return False
    h = _hash_key(key)
    with _lock:
        data = _load_store()
        items = data.get("users", {}).get(user_id, [])
        for item in items:
            if item.get("hash") == h and item.get("revoked_at") is None:
                return True
    return False


@dataclass
class KeyRecord:
    id: str
    prefix: str
    last4: str
    hash: str
    created_at: float
    revoked_at: Optional[float] = None
    label: Optional[str] = None

    def to_public(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("hash", None)
        d["active"] = self.revoked_at is None
        return d


class KeyCreatePayload(BaseModel):
    label: Optional[str] = None


router = APIRouter(prefix="/keys", tags=["Keys"], dependencies=[Depends(allow_dev_mode)])


@router.get("")
def list_keys(request: Request):
    uid = _user_id(request)
    with _lock:
        data = _load_store()
        items = data.get("users", {}).get(uid, [])
        keys = [KeyRecord(**item).to_public() for item in items]
        return {"keys": keys}


@router.post("")
def create_key(request: Request, payload: KeyCreatePayload | None = None):
    uid = _user_id(request)
    key = _new_key()
    record = KeyRecord(
        id=secrets.token_hex(8),
        prefix="faim_live_",
        last4=key[-4:],
        hash=_hash_key(key),
        created_at=time.time(),
        revoked_at=None,
        label=payload.label if payload else None,
    )
    with _lock:
        data = _load_store()
        users = data.setdefault("users", {})
        items = users.setdefault(uid, [])
        items.append(asdict(record))
        _save_store(data)
    return {"key": key, "record": record.to_public()}


@router.delete("/{key_id}")
def revoke_key(request: Request, key_id: str, hard: bool = Query(False)):
    uid = _user_id(request)
    with _lock:
        data = _load_store()
        items = data.get("users", {}).get(uid, [])
        for idx, item in enumerate(items):
            if item.get("id") == key_id:
                if hard:
                    items.pop(idx)
                    _save_store(data)
                    return {"revoked": True, "deleted": True}
                if item.get("revoked_at") is None:
                    item["revoked_at"] = time.time()
                _save_store(data)
                return {"revoked": True, "deleted": False, "record": KeyRecord(**item).to_public()}
    raise HTTPException(status_code=404, detail="Key not found")
