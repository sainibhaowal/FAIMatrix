from __future__ import annotations

import zlib

from faim.core.types import GraphId, PayloadRef
from faim.data.storage.cipher import PayloadCipher
from faim.data.storage.payload_store import PayloadStore


class EncryptedPayloadStore(PayloadStore):
    """
    Decorator that adds compression + encryption on top of a base PayloadStore.

    Behaviour:
    - put_payload:
        payload -> zlib.compress -> cipher.encrypt -> inner.put_payload
    - get_payload:
        inner.get_payload -> cipher.decrypt -> zlib.decompress -> payload
    - delete_payload: delegated to inner
    """

    def __init__(self, inner: PayloadStore, cipher: PayloadCipher) -> None:
        self._inner = inner
        self._cipher = cipher

    def put_payload(
        self,
        graph_id: GraphId,
        payload_bytes: bytes,
        *,
        mime_type: str = "text/plain",
    ) -> PayloadRef:
        compressed = zlib.compress(payload_bytes)
        encrypted = self._cipher.encrypt(graph_id, compressed)
        return self._inner.put_payload(graph_id, encrypted, mime_type=mime_type)

    def get_payload(
        self,
        graph_id: GraphId,
        payload_ref: PayloadRef,
    ) -> bytes | None:
        raw = self._inner.get_payload(graph_id, payload_ref)
        if raw is None:
            return None
        compressed = self._cipher.decrypt(graph_id, raw)
        return zlib.decompress(compressed)

    def delete_payload(self, graph_id: GraphId, payload_ref: PayloadRef) -> None:
        self._inner.delete_payload(graph_id, payload_ref)
