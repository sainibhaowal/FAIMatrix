"""Local open-source baseline adapters for FAIM benchmarks (zero external API keys)."""

from __future__ import annotations

import math
import re
import time
from collections import Counter
from typing import Dict, List, Optional, Tuple

from faim_benchmarks.adapters.base import (
    IngestOutcome,
    MemorySystemAdapter,
    QueryOutcome,
)


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

    def ingest_document(
        self, namespace: str, doc_id: str, title: str, text: str
    ) -> IngestOutcome:
        t0 = time.perf_counter()
        content = f"{title}\n\n{text}".strip() if title else text
        tokens = _tokenize(content)
        self._docs.setdefault(namespace, {})[doc_id] = content
        self._doc_tfs.setdefault(namespace, {})[doc_id] = Counter(tokens)
        self._doc_lens.setdefault(namespace, {})[doc_id] = len(tokens)
        return IngestOutcome(
            doc_id=doc_id, latency_ms=(time.perf_counter() - t0) * 1000.0, ok=True
        )

    def write_memory(
        self, namespace: str, memory_id: str, text: str, timestamp: Optional[str] = None
    ) -> IngestOutcome:
        body = f"[{timestamp}] {text}" if timestamp else text
        return self.ingest_document(namespace, memory_id, "", body)

    def query(
        self, namespace: str, query_id: str, query_text: str, k: int = 20
    ) -> QueryOutcome:
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


def build_all_adapters() -> List[MemorySystemAdapter]:
    from faim_benchmarks.adapters.faim_http import FaimHttpAdapter

    return [
        FaimHttpAdapter(),
        BM25BaselineAdapter(),
    ]
