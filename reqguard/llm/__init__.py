"""LLM access. Agents only ever talk to a model through `get_client()`."""
from __future__ import annotations

import os

from .base import LLMClient, LLMError, LLMReply, estimate_tokens
from .devai_flow import DevAIFlowClient
from .mock import MockLLM
from .openai_compat import OpenAICompatibleClient

__all__ = ["DevAIFlowClient", "LLMClient", "LLMError", "LLMReply", "MockLLM", "OpenAICompatibleClient",
           "estimate_tokens", "get_client"]


def get_client() -> LLMClient:
    """Pick the model from the environment. Default is the offline mock.

    devai  -> the eight agents run as DevAI agents inside DevAI flows (REQGUARD_DEVAI_URL)
    openai -> any OpenAI-compatible chat API (REQGUARD_LLM_BASE_URL / _API_KEY / _MODEL)
    """
    mode = os.getenv("REQGUARD_LLM", "mock").lower()
    if mode == "mock":
        return MockLLM()
    if mode == "devai":
        return DevAIFlowClient.from_env()
    if mode in ("openai", "deepseek", "real"):
        return OpenAICompatibleClient(
            base_url=os.getenv("REQGUARD_LLM_BASE_URL", ""),
            api_key=os.getenv("REQGUARD_LLM_API_KEY", ""),
            model=os.getenv("REQGUARD_LLM_MODEL", ""),
            timeout=float(os.getenv("REQGUARD_LLM_TIMEOUT", "30")),
            json_mode=os.getenv("REQGUARD_LLM_JSON_MODE", "1") != "0",
        )
    raise LLMError(f"Unknown REQGUARD_LLM value: {mode!r} (use 'mock', 'devai' or 'openai').")
