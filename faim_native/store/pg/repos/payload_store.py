"""Payload storage interfaces for FAIM.

FAIM separates vector nodes from raw payload blobs.

P2: this module defines the abstract PayloadStore API.
Concrete backends (SQLite, filesystem, S3, etc.) implement this interface
and can add compression + encryption with per-graph keys.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from faim.core.types import GraphId, PayloadRef


class PayloadStore(ABC):
    """Abstract blob store for payloads.

    Implementations are responsible for:
    - Per-graph scoping (graph_id as a first-class parameter).
    - Optional compression/encryption at rest.
    - Stable PayloadRef identifiers that can be stored in NodeRecord.
    """

    @abstractmethod
    def put_payload(
        self,
        graph_id: GraphId,
        payload_bytes: bytes,
        *,
        mime_type: str = "text/plain",
    ) -> PayloadRef:
        """Store payload bytes and return a stable PayloadRef.

        Implementations may:
        - Compress payload_bytes before writing.
        - Encrypt payload_bytes using a per-graph key.
        - Persist mime_type alongside the blob or in an auxiliary table.
        """

    @abstractmethod
    def get_payload(
        self,
        graph_id: GraphId,
        payload_ref: PayloadRef,
    ) -> bytes | None:
        """Retrieve payload bytes for a given graph_id + ref.

        Must return the *decrypted* and *decompressed* payload bytes,
        or None if the ref does not exist.
        """

    @abstractmethod
    def delete_payload(self, graph_id: GraphId, payload_ref: PayloadRef) -> None:
        """Delete payload bytes (subject to governance/retention policies).

        Implementations may:
        - Perform a physical delete, and/or
        - Mark the payload as logically deleted while keeping the bytes
          around for audit, depending on your retention policy.
        """
