# faim/model/llm.py
"""
FAIM Unified LLM Wrapper (P4 Standard)
--------------------------------------

This file provides a clean abstraction layer between the FAIM backend
and any LLM provider (Groq, OpenAI, Local Llama, etc).

The backend uses ONLY:

    llm.stream_chat(messages)
    llm.complete(messages)

This file connects that unified interface to our real Groq client.

If we switch to another model later:
- ONLY this file changes
- chat.py and the whole backend stay untouched
"""

from __future__ import annotations

from typing import AsyncGenerator, Dict, List, Optional

from faim.model.groq_client import GroqLLM, get_groq_llm

# ========================================================================
# UNIFIED LLM INTERFACE CLASS
# ========================================================================


class FaimLLM:
    """
    Unified LLM interface.

    This wraps whichever backend LLM we want to use:
    - GroqLLM (default)
    - OpenAI / Claude (future)
    - Local Llama.cpp (future)

    Backend code (chat.py) never needs to know which one.
    """

    def __init__(self, client: GroqLLM):
        self.client = client

    # -------------------------------------------------------------------
    # STREAM CHAT  (async generator)
    # -------------------------------------------------------------------
    async def stream_chat(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """
        Returns tokens as they are generated.
        """
        async for token in self.client.stream_chat(messages):
            yield token

    # -------------------------------------------------------------------
    # NON-STREAM COMPLETION  (fallback)
    # -------------------------------------------------------------------
    async def complete(self, messages: List[Dict[str, str]]) -> str:
        """
        Returns one full string.
        """
        return await self.client.complete(messages)


# ========================================================================
# SINGLETON FACTORY
# ========================================================================

_llm_instance: Optional[FaimLLM] = None


def get_llm() -> FaimLLM:
    """
    Returns a singleton FAIM LLM instance.

    Backend always calls:

        llm = get_llm()
        async for t in llm.stream_chat(...):
            ...
        reply = await llm.complete(...)

    This function isolates ALL backend code from provider changes.
    """
    global _llm_instance

    if _llm_instance is None:
        client = get_groq_llm()  # Real provider (Groq)
        _llm_instance = FaimLLM(client)

    return _llm_instance
