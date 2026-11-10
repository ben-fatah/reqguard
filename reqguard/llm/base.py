"""The one interface every agent uses to reach a language model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMReply:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class LLMError(RuntimeError):
    """The model could not be reached or returned an unusable response."""


class LLMClient(Protocol):
    name: str

    def complete(self, system: str, user: str, *, agent: str) -> LLMReply:
        """Send one system + user message and return the raw text reply.

        `agent` names the calling agent; real clients ignore it, the mock uses it.
        """
        ...


def estimate_tokens(text: str) -> int:
    """Rough token estimate (about 4 characters per token) when a provider gives none."""
    return max(1, len(text) // 4)
