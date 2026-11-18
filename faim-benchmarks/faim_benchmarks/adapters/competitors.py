"""External competitor adapters and local BM25 reference baseline.

Every commercial adapter talks exclusively over its public REST API when its
API key is configured; when unconfigured, `is_configured()` returns `(False, reason)`
so benchmark runs explicitly record `"skipped"` rather than fabricating numbers.
"""

from __future__ import annotations

import math
import os
import re
import time
from collections import Counter
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

import httpx

from faim_benchmarks.adapters.base import IngestOutcome, MemorySystemAdapter, QueryOutcome


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25BaselineAdapter:
    """Transparent local BM25 (Okapi k1=1.5, b=0.75) baseline with zero API cost."""

    name = "BM25-Baseline"
    system_type = "lexical_rag"

    def __init__(self) -> None:
        self._docs: Dict[str, Dict[str, str]] = {}
        self._doc_tfs: Dict[str, Dict[str, Counter[str]]] = {}
        self._doc_lens: Dict[str, Dict[str, int]] = {}

    def is_configured(self) -> tuple[bool, Optional[str]]:
        return True, None

    def prepare_namespace(self, namespace: str) -> None:
        self._docs[namespace] = {}
        self._doc_tfs[namespace] = {}
        self._doc_lens[namespace] = {}

    def ingest_document(self, namespace: str, doc_id: str, title: str, text: str) -> IngestOutcome:
        t0 = time.perf_counter()
        content = f"{title}\n\n{text}".strip() if title else text
        tokens = _tokenize(content)
        self._docs.setdefault(namespace, {})[doc_id] = content
        self._doc_tfs.setdefault(namespace, {})[doc_id] = Counter(tokens)
        self._doc_lens.setdefault(namespace, {})[doc_id] = len(tokens)
        return IngestOutcome(doc_id=doc_id, latency_ms=(time.perf_counter() - t0) * 1000.0, ok=True)

    def write_memory(self, namespace: str, memory_id: str, text: str, timestamp: Optional[str] = None) -> IngestOutcome:
        body = f"[{timestamp}] {text}" if timestamp else text
        return self.ingest_document(namespace, memory_id, "", body)

    def query(self, namespace: str, query_id: str, query_text: str, k: int = 20) -> QueryOutcome:
        t0 = time.perf_counter()
        tfs = self._doc_tfs.get(namespace, {})
        lens = self._doc_lens.get(namespace, {})
        docs = self._docs.get(namespace, {})
        n_docs = len(tfs)
        if n_docs == 0:
            return QueryOutcome(query_id=query_id, retrieved_doc_ids=[], latency_ms=0.0)

        avgdl = sum(lens.values()) / max(1, n_docs)
        q_terms = _tokenize(query_text)
        df: Dict[str, int] = {
            term: sum(1 for tf in tfs.values() if term in tf) for term in set(q_terms)
        }
        k1, b = 1.5, 0.75
        scored: List[Tuple[float, str]] = []
        for doc_id, tf_map in tfs.items():
            dl = lens[doc_id]
            score = 0.0
            for term in q_terms:
                f = tf_map.get(term, 0)
                if f == 0:
                    continue
                n_q = df.get(term, 0)
                idf = math.log((n_docs - n_q + 0.5) / (n_q + 0.5) + 1.0)
                denom = f + k1 * (1.0 - b + b * (dl / max(1e-9, avgdl)))
                score += idf * ((f * (k1 + 1.0)) / max(1e-9, denom))
            if score > 0:
                scored.append((score, doc_id))
        scored.sort(key=lambda item: (-item[0], item[1]))
        top_ids = [doc_id for _, doc_id in scored[:k]]
        top_texts = [docs[doc_id] for doc_id in top_ids]
        return QueryOutcome(
            query_id=query_id,
            retrieved_doc_ids=top_ids,
            retrieved_texts=top_texts,
            answer_text="\n".join(top_texts[:3]),
            latency_ms=(time.perf_counter() - t0) * 1000.0,
        )

    def close(self) -> None:
        return None


class Mem0Adapter:
    """Mem0 REST API adapter (`MEM0_API_KEY`)."""

    name = "Mem0"
    system_type = "commercial_memory"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: str = "https://api.mem0.ai",
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("MEM0_API_KEY", "").strip()
        self._client = httpx.Client(base_url=base_url, timeout=60.0, transport=transport)

    def is_configured(self) -> tuple[bool, Optional[str]]:
        return (True, None) if self.api_key else (False, "MEM0_API_KEY not set")

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Token {self.api_key}", "Content-Type": "application/json"}

    def prepare_namespace(self, namespace: str) -> None:
        return None

    def ingest_document(self, namespace: str, doc_id: str, title: str, text: str) -> IngestOutcome:
        content = f"{title}\n\n{text}".strip() if title else text
        return self.write_memory(namespace, doc_id, content)

    def write_memory(self, namespace: str, memory_id: str, text: str, timestamp: Optional[str] = None) -> IngestOutcome:
        payload = {
            "messages": [{"role": "user", "content": text}],
            "user_id": namespace,
            "metadata": {"doc_id": memory_id, **({"timestamp": timestamp} if timestamp else {})},
            "infer": False,
        }
        t0 = time.perf_counter()
        resp = self._client.post("/v1/memories/", json=payload, headers=self._headers())
        ms = (time.perf_counter() - t0) * 1000.0
        if resp.status_code >= 400:
            return IngestOutcome(doc_id=memory_id, latency_ms=ms, ok=False, error=f"HTTP {resp.status_code}")
        return IngestOutcome(doc_id=memory_id, latency_ms=ms, ok=True)

    def query(self, namespace: str, query_id: str, query_text: str, k: int = 20) -> QueryOutcome:
        payload = {"query": query_text, "user_id": namespace, "limit": k}
        t0 = time.perf_counter()
        resp = self._client.post("/v1/memories/search/", json=payload, headers=self._headers())
        ms = (time.perf_counter() - t0) * 1000.0
        resp.raise_for_status()
        data = resp.json()
        items = data if isinstance(data, list) else data.get("results", [])
        doc_ids: List[str] = []
        texts: List[str] = []
        for item in items:
            meta = item.get("metadata") or {}
            did = str(meta.get("doc_id") or item.get("id") or "")
            if did and did not in doc_ids:
                doc_ids.append(did)
            if item.get("memory"):
                texts.append(str(item["memory"]))
        return QueryOutcome(
            query_id=query_id,
            retrieved_doc_ids=doc_ids[:k],
            retrieved_texts=texts[:k],
            answer_text="\n".join(texts[:3]),
            latency_ms=ms,
        )

    def close(self) -> None:
        self._client.close()


class ZepAdapter:
    """Zep Cloud v4 REST API adapter (`ZEP_API_KEY`)."""

    name = "Zep"
    system_type = "commercial_memory"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("ZEP_API_KEY", "").strip()
        self.base_url = (base_url or os.getenv("ZEP_BASE_URL", "https://api.getzep.com")).rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=60.0, transport=transport)
        self._graph_ids: Dict[str, str] = {}
        self._episode_to_doc: Dict[str, Dict[str, str]] = {}

    def is_configured(self) -> tuple[bool, Optional[str]]:
        return (True, None) if self.api_key else (False, "ZEP_API_KEY not set")

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Api-Key {self.api_key}", "Content-Type": "application/json"}

    def prepare_namespace(self, namespace: str) -> None:
        resp = self._client.post("/api/v4/users", json={"user_id": namespace}, headers=self._headers())
        resp.raise_for_status()
        payload = resp.json()
        graph_uuid = str(payload.get("uuid") or payload.get("graph_uuid") or "")
        if not graph_uuid:
            raise RuntimeError("Zep user creation returned no graph UUID")
        self._graph_ids[namespace] = graph_uuid
        self._episode_to_doc[namespace] = {}

    def ingest_document(self, namespace: str, doc_id: str, title: str, text: str) -> IngestOutcome:
        content = f"{title}\n\n{text}".strip() if title else text
        return self.write_memory(namespace, doc_id, content)

    def write_memory(self, namespace: str, memory_id: str, text: str, timestamp: Optional[str] = None) -> IngestOutcome:
        graph_uuid = self._graph_ids.get(namespace, namespace)
        payload = {
            "type": "text",
            "data": text,
            "document_id": memory_id,
            "metadata": {"doc_id": memory_id},
            **({"reference_time": timestamp} if timestamp else {}),
        }
        t0 = time.perf_counter()
        resp = self._client.post(f"/api/v4/graphs/{graph_uuid}/episodes", json=payload, headers=self._headers())
        ms = (time.perf_counter() - t0) * 1000.0
        if resp.status_code >= 400:
            return IngestOutcome(doc_id=memory_id, latency_ms=ms, ok=False, error=f"HTTP {resp.status_code}")
        data = resp.json()
        episode = data.get("episode") if isinstance(data, dict) else None
        episode_uuid = str((episode or {}).get("uuid") or data.get("uuid") or "")
        if episode_uuid:
            self._episode_to_doc.setdefault(namespace, {})[episode_uuid] = memory_id
        return IngestOutcome(doc_id=memory_id, latency_ms=ms, ok=True)

    def query(self, namespace: str, query_id: str, query_text: str, k: int = 20) -> QueryOutcome:
        graph_uuid = self._graph_ids.get(namespace, namespace)
        payload = {"query": query_text, "page_size": min(k, 50)}
        t0 = time.perf_counter()
        resp = self._client.post(f"/api/v4/graphs/{graph_uuid}/search/edges", json=payload, headers=self._headers())
        ms = (time.perf_counter() - t0) * 1000.0
        resp.raise_for_status()
        data = resp.json()
        doc_ids: List[str] = []
        texts: List[str] = []
        episode_map = self._episode_to_doc.get(namespace, {})
        for edge in data.get("items", []):
            txt = str(edge.get("fact") or edge.get("summary") or edge.get("content") or "")
            candidate_ids = [episode_map.get(str(ep), "") for ep in edge.get("episode_uuids", [])]
            m = re.search(r"\[doc_id=([^\]]+)\]", txt)
            candidate_ids.append(m.group(1) if m else str(edge.get("uuid") or ""))
            for did in candidate_ids:
                if did and did not in doc_ids:
                    doc_ids.append(did)
            if txt:
                texts.append(txt)
        return QueryOutcome(
            query_id=query_id,
            retrieved_doc_ids=doc_ids[:k],
            retrieved_texts=texts[:k],
            answer_text="\n".join(texts[:3]),
            latency_ms=ms,
        )

    def close(self) -> None:
        self._client.close()


class SuperMemoryAdapter:
    """Supermemory v5 REST API adapter (`SUPERMEMORY_API_KEY`)."""

    name = "SuperMemory"
    system_type = "commercial_memory"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("SUPERMEMORY_API_KEY", "").strip()
        self.base_url = (base_url or os.getenv("SUPERMEMORY_BASE_URL", "https://api.supermemory.ai")).rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=60.0, transport=transport)

    def is_configured(self) -> tuple[bool, Optional[str]]:
        return (True, None) if self.api_key else (False, "SUPERMEMORY_API_KEY not set")

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def prepare_namespace(self, namespace: str) -> None:
        return None

    def ingest_document(self, namespace: str, doc_id: str, title: str, text: str) -> IngestOutcome:
        content = f"{title}\n\n{text}".strip() if title else text
        return self.write_memory(namespace, doc_id, content)

    def write_memory(self, namespace: str, memory_id: str, text: str, timestamp: Optional[str] = None) -> IngestOutcome:
        payload = {
            "content": text,
            "id": memory_id,
            "metadata": {"doc_id": memory_id},
            "dreaming": "instant",
            "taskType": "memory",
            **({"date": timestamp} if timestamp else {}),
        }
        t0 = time.perf_counter()
        path = f"/ns/{quote(namespace, safe='')}/document"
        resp = self._client.post(path, json=payload, headers=self._headers())
        ms = (time.perf_counter() - t0) * 1000.0
        if resp.status_code >= 400:
            return IngestOutcome(doc_id=memory_id, latency_ms=ms, ok=False, error=f"HTTP {resp.status_code}")
        return IngestOutcome(doc_id=memory_id, latency_ms=ms, ok=True)

    def query(self, namespace: str, query_id: str, query_text: str, k: int = 20) -> QueryOutcome:
        payload = {"q": query_text, "limit": k, "searchMode": "hybrid"}
        t0 = time.perf_counter()
        path = f"/ns/{quote(namespace, safe='')}/search"
        resp = self._client.post(path, json=payload, headers=self._headers())
        ms = (time.perf_counter() - t0) * 1000.0
        resp.raise_for_status()
        data = resp.json()
        doc_ids: List[str] = []
        texts: List[str] = []
        items = data if isinstance(data, list) else data.get("results", data.get("memories", []))
        for item in items:
            meta = item.get("metadata") or {}
            did = str(meta.get("doc_id") or item.get("documentId") or item.get("document_id") or item.get("id") or "")
            if did and did not in doc_ids:
                doc_ids.append(did)
            chunks = item.get("chunks") or item.get("content") and [{"content": item.get("content")}] or []
            for ch in chunks:
                if ch.get("content"):
                    texts.append(str(ch["content"]))
        return QueryOutcome(
            query_id=query_id,
            retrieved_doc_ids=doc_ids[:k],
            retrieved_texts=texts[:k],
            answer_text="\n".join(texts[:3]),
            latency_ms=ms,
        )

    def close(self) -> None:
        self._client.close()


class LettaAdapter:
    """Letta / MemGPT REST API adapter (`LETTA_BASE_URL`)."""

    name = "Letta"
    system_type = "commercial_memory"

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.base_url = (base_url if base_url is not None else os.getenv("LETTA_BASE_URL", "")).strip().rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("LETTA_API_KEY", "").strip()
        self._client = httpx.Client(base_url=self.base_url or "http://localhost:8283", timeout=60.0, transport=transport)
        self._agent_ids: Dict[str, str] = {}

    def is_configured(self) -> tuple[bool, Optional[str]]:
        return (True, None) if self.base_url else (False, "LETTA_BASE_URL not set")

    def _headers(self) -> Dict[str, str]:
        hdrs = {"Content-Type": "application/json"}
        if self.api_key:
            hdrs["Authorization"] = f"Bearer {self.api_key}"
        return hdrs

    def prepare_namespace(self, namespace: str) -> None:
        resp = self._client.post("/v1/agents/", json={"name": namespace}, headers=self._headers())
        if resp.status_code < 400:
            self._agent_ids[namespace] = str(resp.json().get("id") or namespace)

    def ingest_document(self, namespace: str, doc_id: str, title: str, text: str) -> IngestOutcome:
        content = f"{title}\n\n{text}".strip() if title else text
        return self.write_memory(namespace, doc_id, content)

    def write_memory(self, namespace: str, memory_id: str, text: str, timestamp: Optional[str] = None) -> IngestOutcome:
        agent_id = self._agent_ids.get(namespace, namespace)
        t0 = time.perf_counter()
        resp = self._client.post(
            f"/v1/agents/{agent_id}/archival-memory",
            json={"text": f"[doc_id={memory_id}] {text}"},
            headers=self._headers(),
        )
        ms = (time.perf_counter() - t0) * 1000.0
        if resp.status_code >= 400:
            return IngestOutcome(doc_id=memory_id, latency_ms=ms, ok=False, error=f"HTTP {resp.status_code}")
        return IngestOutcome(doc_id=memory_id, latency_ms=ms, ok=True)

    def query(self, namespace: str, query_id: str, query_text: str, k: int = 20) -> QueryOutcome:
        agent_id = self._agent_ids.get(namespace, namespace)
        t0 = time.perf_counter()
        resp = self._client.get(
            f"/v1/agents/{agent_id}/archival-memory",
            params={"search": query_text, "limit": k},
            headers=self._headers(),
        )
        ms = (time.perf_counter() - t0) * 1000.0
        resp.raise_for_status()
        doc_ids: List[str] = []
        texts: List[str] = []
        for item in resp.json():
            txt = str(item.get("text") or "")
            m = re.search(r"\[doc_id=([^\]]+)\]", txt)
            did = m.group(1) if m else str(item.get("id") or "")
            if did and did not in doc_ids:
                doc_ids.append(did)
            if txt:
                texts.append(txt)
        return QueryOutcome(
            query_id=query_id,
            retrieved_doc_ids=doc_ids[:k],
            retrieved_texts=texts[:k],
            answer_text="\n".join(texts[:3]),
            latency_ms=ms,
        )

    def close(self) -> None:
        self._client.close()


class OpenAIFullContextAdapter:
    """OpenAI-compatible full-context baseline (`OPENAI_API_KEY`)."""

    name = "Full-Context-LLM"
    system_type = "no_external_memory"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "").strip()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._client = httpx.Client(base_url=base_url, timeout=90.0, transport=transport)
        self._buffers: Dict[str, List[Tuple[str, str]]] = {}

    def is_configured(self) -> tuple[bool, Optional[str]]:
        return (True, None) if self.api_key else (False, "OPENAI_API_KEY not set")

    def prepare_namespace(self, namespace: str) -> None:
        self._buffers[namespace] = []

    def ingest_document(self, namespace: str, doc_id: str, title: str, text: str) -> IngestOutcome:
        content = f"[{doc_id}] {title}\n{text}".strip() if title else f"[{doc_id}] {text}"
        self._buffers.setdefault(namespace, []).append((doc_id, content))
        return IngestOutcome(doc_id=doc_id, latency_ms=0.0, ok=True)

    def write_memory(self, namespace: str, memory_id: str, text: str, timestamp: Optional[str] = None) -> IngestOutcome:
        body = f"[{memory_id}] ({timestamp}) {text}" if timestamp else f"[{memory_id}] {text}"
        self._buffers.setdefault(namespace, []).append((memory_id, body))
        return IngestOutcome(doc_id=memory_id, latency_ms=0.0, ok=True)

    def query(self, namespace: str, query_id: str, query_text: str, k: int = 20) -> QueryOutcome:
        context = "\n\n".join(txt for _, txt in self._buffers.get(namespace, []))[:120000]
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": "Answer the question using only the provided records. Cite matching record IDs in brackets like [id].",
                },
                {"role": "user", "content": f"Records:\n{context}\n\nQuestion: {query_text}"},
            ],
        }
        t0 = time.perf_counter()
        resp = self._client.post(
            "/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        ms = (time.perf_counter() - t0) * 1000.0
        resp.raise_for_status()
        answer = str(resp.json()["choices"][0]["message"]["content"])
        cited = re.findall(r"\[([^\]]+)\]", answer)
        return QueryOutcome(
            query_id=query_id,
            retrieved_doc_ids=list(dict.fromkeys(cited))[:k],
            retrieved_texts=[answer],
            answer_text=answer,
            latency_ms=ms,
        )

    def close(self) -> None:
        self._client.close()


def build_all_adapters() -> List[MemorySystemAdapter]:
    from faim_benchmarks.adapters.faim_http import FaimHttpAdapter

    return [
        FaimHttpAdapter(),
        BM25BaselineAdapter(),
        Mem0Adapter(),
        ZepAdapter(),
        SuperMemoryAdapter(),
        LettaAdapter(),
        OpenAIFullContextAdapter(),
    ]
