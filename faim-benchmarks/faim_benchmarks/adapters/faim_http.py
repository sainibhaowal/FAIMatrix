"""Black-box HTTP adapter for FAIM (`/api/v1/ingest`, `/api/v1/memory`, `/api/v1/query`)."""

from __future__ import annotations

import base64
import os
import time
import uuid
from typing import Dict, List, Optional, Sequence

import httpx

from faim_benchmarks.adapters.base import IngestOutcome, QueryOutcome


def _deterministic_uuid(namespace: str, doc_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"faim-bench:{namespace}:{doc_id}"))


class FaimHttpAdapter:
    """Calls a live FAIM API instance strictly over HTTP."""

    name = "FAIM-Native"
    system_type = "fractal_graph_memory"

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        bearer_token: Optional[str] = None,
        profile: Optional[str] = None,
        persist_mode: Optional[str] = None,
        graph_max_hops: Optional[int] = None,
        transport: Optional[httpx.BaseTransport] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("FAIM_BASE_URL", "http://localhost:8000")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("FAIM_API_KEY", "").strip()
        self.tenant_id = tenant_id if tenant_id is not None else os.getenv("FAIM_TENANT_ID", "").strip()
        self.bearer_token = bearer_token if bearer_token is not None else os.getenv("FAIM_BEARER_TOKEN", "").strip()
        self.profile = profile or os.getenv("FAIM_PROFILE", "strict")
        self.persist_mode = persist_mode or os.getenv("FAIM_PERSIST_MODE", "strict")
        self.write_mode = os.getenv("FAIM_BENCH_FAIM_WRITE_MODE", "ingest").strip().lower()
        if self.write_mode not in {"ingest", "memory"}:
            raise ValueError("FAIM_BENCH_FAIM_WRITE_MODE must be 'ingest' or 'memory'")
        self.graph_max_hops = int(graph_max_hops or os.getenv("FAIM_GRAPH_MAX_HOPS", "2"))
        self.batch_size = max(0, int(os.getenv("FAIM_BENCH_FAIM_BATCH_SIZE", "0")))
        configured_timeout = (
            float(timeout)
            if timeout is not None
            else float(os.getenv("FAIM_BENCH_FAIM_QUERY_TIMEOUT_SECONDS", "300"))
        )
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=max(1.0, configured_timeout),
            transport=transport,
        )
        self._raw_to_doc: Dict[str, Dict[str, str]] = {}
        self._filename_to_doc: Dict[str, Dict[str, str]] = {}
        self._synced_namespaces: set[str] = set()

    def is_configured(self) -> tuple[bool, Optional[str]]:
        if self.bearer_token:
            return True, None
        if self.api_key and self.tenant_id:
            return True, None
        return False, "Set FAIM_API_KEY + FAIM_TENANT_ID (or FAIM_BEARER_TOKEN)"

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        if self.tenant_id:
            headers["X-Tenant-Id"] = self.tenant_id
        return headers

    def _auth_headers(self) -> Dict[str, str]:
        headers = self._headers()
        headers.pop("Content-Type", None)
        return headers

    def prepare_namespace(self, namespace: str) -> None:
        self._raw_to_doc[namespace] = {}
        self._filename_to_doc[namespace] = {}
        self._synced_namespaces.discard(namespace)

    def _sync_storage_raw_ids(self, namespace: str) -> None:
        if namespace in self._synced_namespaces:
            return
        self._synced_namespaces.add(namespace)
        fn_map = self._filename_to_doc.get(namespace, {})
        if not fn_map:
            return
        raw_map = self._raw_to_doc.setdefault(namespace, {})
        offset = 0
        limit = 100
        while True:
            resp = self._client.get(
                "/api/v1/storage/files",
                params={"graph_id": namespace, "limit": limit, "offset": offset},
                headers=self._headers(),
            )
            if resp.status_code >= 400:
                break
            payload = resp.json()
            items = payload.get("items") or []
            for item in items:
                fn = str(item.get("filename") or "")
                rid = str(item.get("raw_id") or "")
                if fn in fn_map and rid:
                    raw_map[rid] = fn_map[fn]
            total = int(payload.get("total") or 0)
            offset += len(items)
            if not items or offset >= total:
                break

    def ingest_document(self, namespace: str, doc_id: str, title: str, text: str) -> IngestOutcome:
        if self.write_mode == "memory":
            content = f"{title}\n\n{text}".strip() if title else text
            return self.write_memory(namespace, doc_id, content)
        content = f"{title}\n\n{text}".strip() if title else text
        raw_uuid = _deterministic_uuid(namespace, doc_id)
        filename = f"bench_{doc_id}.txt"
        self._raw_to_doc.setdefault(namespace, {})[raw_uuid] = doc_id
        self._filename_to_doc.setdefault(namespace, {})[filename] = doc_id
        self._synced_namespaces.discard(namespace)
        payload = {
            "graph_id": namespace,
            "raw_id": raw_uuid,
            "filename": filename,
            "bytes_base64": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "content_type": "text/plain",
            "profile": self.profile,
            "persist_mode": self.persist_mode,
        }
        t0 = time.perf_counter()
        resp = self._client.post("/api/v1/ingest", json=payload, headers=self._headers())
        latency_ms = (time.perf_counter() - t0) * 1000.0
        if resp.status_code >= 400:
            return IngestOutcome(doc_id=doc_id, latency_ms=latency_ms, ok=False, error=f"HTTP {resp.status_code}: {resp.text[:200]}")
        resp_raw_id = str(resp.json().get("raw_id") or "")
        if resp_raw_id:
            self._raw_to_doc[namespace][resp_raw_id] = doc_id
        return IngestOutcome(doc_id=doc_id, latency_ms=latency_ms, ok=True)

    def ingest_documents_batch(
        self,
        namespace: str,
        items: Sequence[tuple[str, Dict[str, str]]],
    ) -> List[IngestOutcome]:
        """Ingest a bounded batch through the public multipart upload API.

        This is still a black-box HTTP benchmark: the API performs the same
        canonical ingest path, but one request amortizes connection, auth,
        and response overhead across multiple documents.
        """
        if self.write_mode != "ingest" or self.batch_size <= 1:
            return [
                self.ingest_document(namespace, doc_id, doc.get("title", ""), doc.get("text", ""))
                for doc_id, doc in items
            ]

        item_list = list(items)
        if not item_list:
            return []
        filename_to_doc: Dict[str, str] = {}
        files = []
        for doc_id, doc in item_list:
            filename = f"bench_{doc_id}.txt"
            filename_to_doc[filename] = doc_id
            content = f"{doc.get('title', '')}\n\n{doc.get('text', '')}".strip()
            files.append(("files", (filename, content.encode("utf-8"), "text/plain")))

        t0 = time.perf_counter()
        resp = self._client.post(
            "/api/v1/storage/uploads",
            data={
                "graph_id": namespace,
                "profile": self.profile,
                "persist_mode": self.persist_mode,
                "extractor_mode": "faim_native",
            },
            files=files,
            headers=self._auth_headers(),
            timeout=max(60.0, 30.0 * len(item_list)),
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        if resp.status_code >= 400:
            error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            return [IngestOutcome(doc_id=doc_id, latency_ms=elapsed_ms, ok=False, error=error) for doc_id, _ in item_list]

        payload = resp.json()
        if str(payload.get("status") or "").lower() in {"queued", "processing", "ingesting"}:
            job_id = str(payload.get("job_id") or "")
            deadline = time.monotonic() + max(
                60.0, float(os.getenv("FAIM_BENCH_FAIM_JOB_TIMEOUT_SECONDS", "3600"))
            )
            poll_timeout = max(
                60.0,
                float(os.getenv("FAIM_BENCH_FAIM_JOB_POLL_TIMEOUT_SECONDS", "300")),
            )
            last_poll_error: Optional[str] = None
            while job_id and time.monotonic() < deadline:
                time.sleep(max(0.1, float(os.getenv("FAIM_BENCH_FAIM_JOB_POLL_SECONDS", "1"))))
                try:
                    status_resp = self._client.get(
                        f"/api/v1/storage/uploads/{job_id}",
                        headers=self._auth_headers(),
                        timeout=poll_timeout,
                    )
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    # A long-running production worker or a transient API
                    # restart must not turn every file in an otherwise valid
                    # batch into an ingest failure.  Keep polling until the
                    # explicit job deadline; the terminal status remains the
                    # source of truth.
                    last_poll_error = f"{type(exc).__name__}: {exc}"
                    continue
                if status_resp.status_code >= 400:
                    payload = {
                        "status": "failed",
                        "files": [],
                        "error": f"HTTP {status_resp.status_code}: {status_resp.text[:200]}",
                    }
                    break
                payload = status_resp.json()
                if str(payload.get("status") or "").lower() in {
                    "done", "completed", "partial_failed", "failed", "cancelled"
                }:
                    break
            else:
                payload = {
                    "status": "failed",
                    "files": [],
                    "error": (
                        f"FAIM storage job {job_id or '<missing>'} timed out"
                        + (f"; last poll error: {last_poll_error}" if last_poll_error else "")
                    ),
                }
        results = {str(row.get("filename")): row for row in (payload.get("files") or [])}
        per_doc_ms = elapsed_ms / max(1, len(item_list))
        outcomes: List[IngestOutcome] = []
        for doc_id, _ in item_list:
            filename = f"bench_{doc_id}.txt"
            row = results.get(filename)
            if not row:
                outcomes.append(IngestOutcome(doc_id=doc_id, latency_ms=per_doc_ms, ok=False, error="Batch response omitted document"))
                continue
            raw_id = str(row.get("raw_id") or "")
            if raw_id:
                self._raw_to_doc.setdefault(namespace, {})[raw_id] = doc_id
            status = str(row.get("status") or "")
            ok = status in {"ingested", "dedup_hit"}
            outcomes.append(
                IngestOutcome(
                    doc_id=doc_id,
                    latency_ms=per_doc_ms,
                    ok=ok,
                    error=None if ok else str(row.get("error") or f"Batch status: {status or 'unknown'}"),
                )
            )
        return outcomes

    def write_memory(self, namespace: str, memory_id: str, text: str, timestamp: Optional[str] = None) -> IngestOutcome:
        body_text = f"[{timestamp}] {text}" if timestamp else text
        payload = {
            "graph_id": namespace,
            "text": body_text,
            "profile": self.profile,
            "persist_mode": self.persist_mode,
            "idempotency_key": f"{namespace}:{memory_id}",
        }
        t0 = time.perf_counter()
        resp = self._client.post("/api/v1/memory/write", json=payload, headers=self._headers())
        latency_ms = (time.perf_counter() - t0) * 1000.0
        if resp.status_code >= 400:
            return IngestOutcome(doc_id=memory_id, latency_ms=latency_ms, ok=False, error=f"HTTP {resp.status_code}: {resp.text[:200]}")
        raw_id = str(resp.json().get("raw_id") or "")
        if raw_id:
            self._raw_to_doc.setdefault(namespace, {})[raw_id] = memory_id
        return IngestOutcome(doc_id=memory_id, latency_ms=latency_ms, ok=True)

    def query(self, namespace: str, query_id: str, query_text: str, k: int = 20) -> QueryOutcome:
        self._sync_storage_raw_ids(namespace)
        payload = {
            "graph_id": namespace,
            "query_text": query_text,
            "profile": self.profile.upper(),
            "k": k,
            "graph_max_hops": self.graph_max_hops,
            "return_explain": False,
        }
        t0 = time.perf_counter()
        resp = self._client.post("/api/v1/query", json=payload, headers=self._headers())
        latency_ms = (time.perf_counter() - t0) * 1000.0
        resp.raise_for_status()
        data = resp.json()

        raw_map = self._raw_to_doc.get(namespace, {})
        seen: set[str] = set()
        retrieved_ids: List[str] = []
        for item in data.get("results", []):
            raw_id = str((item.get("evidence") or {}).get("raw_id") or "")
            mapped = raw_map.get(raw_id, raw_id)
            if mapped and mapped not in seen:
                seen.add(mapped)
                retrieved_ids.append(mapped)

        answer = data.get("answer") or {}
        spans = [str(s.get("text") or "") for s in answer.get("supporting_spans", []) if s.get("text")]
        answer_text = str(answer.get("direct_answer") or "") or "\n".join(spans)
        return QueryOutcome(
            query_id=query_id,
            retrieved_doc_ids=retrieved_ids,
            retrieved_texts=spans,
            answer_text=answer_text,
            latency_ms=latency_ms,
        )

    def close(self) -> None:
        self._client.close()
