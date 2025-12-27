# faim/model/groq_client.py
"""
Groq LLM Client for FAIM
------------------------

Provides a fully async Groq interface with:

- stream_chat(messages)  → async generator of tokens
- complete(messages)     → async single-shot response

Compatible with FAIM chat backend (P4).
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, AsyncGenerator, Dict, List, Optional, cast

try:
    from groq import Groq
    from groq.types.chat.chat_completion import ChatCompletion
    _GROQ_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    Groq = Any  # type: ignore[assignment]
    ChatCompletion = Any  # type: ignore[assignment]
    _GROQ_AVAILABLE = False

# =============================================================================
# CLIENT INITIALIZATION
# =============================================================================

_groq_client: Optional[Groq] = None

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  # or llama3-70b-8192


# =============================================================================
# HELPERS
# =============================================================================


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    if not _GROQ_AVAILABLE:
        raise RuntimeError("groq package is not installed")
    api_key = (os.getenv("GROQ_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is required")
    _groq_client = Groq(api_key=api_key)
    return _groq_client


def _normalize_messages(msgs: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Ensures role/content format is always correct for Groq.
    """
    out = []
    for m in msgs:
        out.append({"role": m["role"], "content": m["content"]})
    return out


# =============================================================================
# MAIN LLM CLIENT CLASS
# =============================================================================


class GroqLLM:
    """
    Groq-powered LLM with async streaming + fallback completion.

    Required API:
        async for tok in llm.stream_chat(messages):
            ...

        reply = await llm.complete(messages)
    """

    # ----------------------------------------------------------------------
    # TOKEN STREAMING
    # ----------------------------------------------------------------------
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Async token stream using Groq's streaming API.
        Yields **string tokens** one by one.
        """
        model = model or DEFAULT_MODEL
        msgs = _normalize_messages(messages)

        # Run blocking Groq client in a thread-safe coroutine
        def _make_stream_request() -> ChatCompletion:
            client = _get_groq_client()
            return cast(Any, client.chat.completions).create(
                messages=msgs,
                model=model,
                stream=True,
            )

        stream = await asyncio.to_thread(_make_stream_request)

        for chunk in stream:
            # Groq returns: {"choices": [{"delta": {"content": "token"}}]}
            choices = getattr(chunk, "choices", None)  # type: ignore
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)  # type: ignore
            if not delta:
                continue
            content = delta.get("content")
            if content:
                yield content

    # ----------------------------------------------------------------------
    # NON-STREAM COMPLETION (Fallback)
    # ----------------------------------------------------------------------
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> str:
        """
        Non-streaming fallback for error scenarios.
        Returns full string answer.
        """
        model = model or DEFAULT_MODEL
        msgs = _normalize_messages(messages)

        def _make_request() -> ChatCompletion:
            client = _get_groq_client()
            return cast(Any, client.chat.completions).create(
                messages=msgs,
                model=model,
                stream=False,
            )

        try:
            resp = await asyncio.to_thread(_make_request)
            return resp.choices[0].message.content or ""
        except Exception as e:
            print(f"[GroqLLM] Non-stream completion error: {e}")
            return "(LLM error: unable to complete request)"


# =============================================================================
# FACTORY
# =============================================================================

_llm_instance: Optional[GroqLLM] = None


def get_groq_llm() -> GroqLLM:
    """
    Singleton GroqLLM instance.
    """
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = GroqLLM()
    return _llm_instance
