"""Payload-at-rest cipher helpers for FAIM.

P2: this module lets you toggle encryption via env without breaking P0.
By default, NoopCipher is used and payloads are stored as plain bytes.
"""

from __future__ import annotations

import importlib
import os
from abc import ABC, abstractmethod
from typing import Dict, Optional, Protocol, cast, runtime_checkable

from faim.core.types import GraphId


class PayloadCipher(ABC):
    """Abstract cipher for payload-at-rest protection."""

    @abstractmethod
    def encrypt(self, graph_id: GraphId, plaintext: bytes) -> bytes:
        """Encrypt payload bytes for a given graph."""

    @abstractmethod
    def decrypt(self, graph_id: GraphId, ciphertext: bytes) -> bytes:
        """Decrypt payload bytes for a given graph."""


class NoopCipher(PayloadCipher):
    """Default cipher: no encryption, passes bytes through as-is."""

    def encrypt(self, graph_id: GraphId, plaintext: bytes) -> bytes:  # noqa: ARG002
        return plaintext

    def decrypt(self, graph_id: GraphId, ciphertext: bytes) -> bytes:  # noqa: ARG002
        return ciphertext


@runtime_checkable
class _FernetLike(Protocol):
    """Minimal interface we expect from a Fernet-like cipher."""

    def encrypt(self, data: bytes) -> bytes:  # pragma: no cover - tiny protocol
        ...

    def decrypt(self, token: bytes) -> bytes:  # pragma: no cover - tiny protocol
        ...


class FernetCipher(PayloadCipher):
    """
    Optional cipher using cryptography.fernet.Fernet.

    You must install 'cryptography' and provide keys via:
    - FAIM_GRAPH_KEY_<GRAPH_ID>  (base64 fernet key), or
    - FAIM_GRAPH_KEY_DEFAULT      (used if per-graph key is missing).
    """

    def __init__(self, default_key: Optional[bytes] = None) -> None:
        self._default_key = default_key
        # Cache of per-graph Fernet-like objects.
        self._cache: Dict[GraphId, _FernetLike] = {}

    def _load_fernet_class(self):
        """
        Dynamically import cryptography.fernet.Fernet.

        Using importlib avoids a hard import at module import time, and keeps
        static analyzers happier when the dependency is not installed.
        """
        module = importlib.import_module("cryptography.fernet")
        return module.Fernet

    def _get_fernet(self, graph_id: GraphId) -> _FernetLike:
        key_env = os.getenv(f"FAIM_GRAPH_KEY_{graph_id}")
        key_bytes: Optional[bytes]

        if key_env:
            key_bytes = key_env.encode("ascii")
        else:
            key_bytes = self._default_key

        if key_bytes is None:
            raise RuntimeError(
                f"No Fernet key configured for graph_id={graph_id!r} and no FAIM_GRAPH_KEY_DEFAULT"
            )

        f = self._cache.get(graph_id)
        if f is None:
            Fernet = self._load_fernet_class()
            f = cast(_FernetLike, Fernet(key_bytes))
            self._cache[graph_id] = f
        return f

    def encrypt(self, graph_id: GraphId, plaintext: bytes) -> bytes:
        f = self._get_fernet(graph_id)
        return f.encrypt(plaintext)

    def decrypt(self, graph_id: GraphId, ciphertext: bytes) -> bytes:
        f = self._get_fernet(graph_id)
        return f.decrypt(ciphertext)


def build_cipher_from_env() -> PayloadCipher:
    """
    Build a PayloadCipher based on env vars.

    FAIM_PAYLOAD_CIPHER:
      - "none" / "" / unset => NoopCipher (default).
      - "fernet"           => FernetCipher (requires 'cryptography').

    FAIM_GRAPH_KEY_DEFAULT (optional):
      - default fernet key for all graphs (base64 fernet key string).
    """
    mode = os.getenv("FAIM_PAYLOAD_CIPHER", "").strip().lower()
    if mode in ("", "none", "plain"):
        return NoopCipher()

    if mode == "fernet":
        default_key_env = os.getenv("FAIM_GRAPH_KEY_DEFAULT")
        default_key_bytes = default_key_env.encode("ascii") if default_key_env else None
        return FernetCipher(default_key=default_key_bytes)

    raise RuntimeError(f"Unknown FAIM_PAYLOAD_CIPHER mode: {mode!r}")
