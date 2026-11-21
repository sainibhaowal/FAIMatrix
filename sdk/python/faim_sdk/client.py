"""Thin synchronous/async Python client for FAIM-Native API (SaaS & Offline)."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

DEFAULT_CREDENTIALS_PATH = Path.home() / ".faim" / "credentials.json"


def load_saved_credentials(path: Path = DEFAULT_CREDENTIALS_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


class FAIMClient:
    """Client for FAIM /api/v1/* endpoints using OAuth Bearer token or API key."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        bearer_token: Optional[str] = None,
        api_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        saved = load_saved_credentials()
        self.base_url = (
            base_url
            or os.getenv("FAIM_BASE_URL")
            or saved.get("base_url")
            or "http://localhost:8000"
        ).rstrip("/")
        self.bearer_token = (
            bearer_token or os.getenv("FAIM_BEARER_TOKEN") or saved.get("access_token")
        )
        self.api_key = api_key or os.getenv("FAIM_API_KEY")
        self.tenant_id = tenant_id or os.getenv("FAIM_TENANT_ID") or "default"
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.api_key:
            headers["X-Api-Key"] = self.api_key
            headers["X-Tenant-Id"] = self.tenant_id
        return headers

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._client.post(path, json=payload, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def _get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        resp = self._client.get(path, params=params, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def memory_write(
        self,
        graph_id: str,
        text: str,
        *,
        filename: Optional[str] = None,
        profile: str = "strict",
        persist_mode: str = "relaxed",
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "graph_id": graph_id,
            "text": text,
            "profile": profile,
            "persist_mode": persist_mode,
        }
        if filename:
            payload["filename"] = filename
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        return self._post("/api/v1/memory/write", payload)

    def memory_search(
        self,
        graph_id: str,
        query_text: str,
        *,
        k: int = 10,
        profile: str = "strict",
        graph_max_hops: Optional[int] = None,
        return_explain: bool = False,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "graph_id": graph_id,
            "query_text": query_text,
            "k": k,
            "profile": profile,
            "return_explain": return_explain,
        }
        if graph_max_hops is not None:
            payload["graph_max_hops"] = graph_max_hops
        return self._post("/api/v1/memory/search", payload)

    def query(
        self,
        graph_id: str,
        query_text: str,
        *,
        k: int = 10,
        profile: str = "STRICT",
        graph_max_hops: Optional[int] = None,
        include_historical: bool = True,
        as_of: Optional[str] = None,
        return_explain: bool = False,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "graph_id": graph_id,
            "query_text": query_text,
            "k": k,
            "profile": profile,
            "include_historical": include_historical,
            "return_explain": return_explain,
        }
        if graph_max_hops is not None:
            payload["graph_max_hops"] = graph_max_hops
        if as_of is not None:
            payload["as_of"] = as_of
        return self._post("/api/v1/query", payload)

    def ingest_text(
        self,
        graph_id: str,
        text: str,
        *,
        filename: str = "ingest.txt",
        content_type: str = "text/plain",
        profile: str = "strict",
        persist_mode: str = "relaxed",
    ) -> Dict[str, Any]:
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        return self._post(
            "/api/v1/ingest",
            {
                "graph_id": graph_id,
                "filename": filename,
                "bytes_base64": encoded,
                "content_type": content_type,
                "profile": profile,
                "persist_mode": persist_mode,
            },
        )

    def memory_get(self, memory_id: str) -> Dict[str, Any]:
        return self._get(f"/api/v1/memory/{memory_id}")

    def graph_surface(self, graph_id: str, *, limit: int = 50) -> Dict[str, Any]:
        return self._get(
            "/api/v1/graph/surface", params={"graph_id": graph_id, "limit": limit}
        )

    def mcp_rpc(
        self, method: str, params: Optional[Dict[str, Any]] = None, req_id: int = 1
    ) -> Dict[str, Any]:
        return self._post(
            "/mcp",
            {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}},
        )

    def close(self) -> None:
        self._client.close()
