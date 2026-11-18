"""Adapter protocol and normalized benchmark response structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol


class AdapterConfigError(RuntimeError):
    """Raised when a system adapter is missing required credentials or config."""


@dataclass
class IngestOutcome:
    doc_id: str
    latency_ms: float
    ok: bool = True
    error: Optional[str] = None
    tokens_estimated: int = 0


@dataclass
class QueryOutcome:
    query_id: str
    retrieved_doc_ids: List[str]
    retrieved_texts: List[str] = field(default_factory=list)
    answer_text: str = ""
    latency_ms: float = 0.0
    metadata: Dict[str, str] = field(default_factory=dict)


class MemorySystemAdapter(Protocol):
    name: str
    system_type: str

    def is_configured(self) -> tuple[bool, Optional[str]]:
        ...

    def prepare_namespace(self, namespace: str) -> None:
        ...

    def ingest_document(self, namespace: str, doc_id: str, title: str, text: str) -> IngestOutcome:
        ...

    def write_memory(self, namespace: str, memory_id: str, text: str, timestamp: Optional[str] = None) -> IngestOutcome:
        ...

    def query(self, namespace: str, query_id: str, query_text: str, k: int = 20) -> QueryOutcome:
        ...

    def close(self) -> None:
        ...
