"""Agent base: instructions + one LLM call + JSON validation + one retry.

An agent = the same language model given its own instructions (prompts/<name>.md),
a typed input, and an output that must pass a validator. Agents never touch the
database or the web layer; the orchestrator persists their results.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..llm import LLMClient, LLMError
from ..models import Usage

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class AgentError(RuntimeError):
    """The agent could not produce valid output after one retry (stage becomes 'failed - retryable')."""


def load_prompt(name: str) -> str:
    shared = (PROMPTS / "_shared.md").read_text(encoding="utf-8")
    own = (PROMPTS / f"{name}.md").read_text(encoding="utf-8")
    return own.strip() + "\n\n" + shared.strip()


def parse_json(text: str) -> Any:
    cleaned = _FENCE.sub("", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in the reply")
    return json.loads(cleaned[start:end + 1])


class Agent:
    name = "agent"

    def __init__(self, llm: LLMClient, usage: Usage | None = None):
        self.llm = llm
        self.instructions = load_prompt(self.name)
        self.usage = usage or Usage(agent=self.name)

    def validate(self, data: Any) -> list[str]:          # overridden by each agent
        return [] if isinstance(data, dict) else ["output is not a JSON object"]

    def call(self, user_message: str) -> dict:
        """Ask the model, validate, retry once with the validation errors, then give up."""
        message = user_message
        problems: list[str] = []
        for attempt in range(2):
            try:
                reply = self.llm.complete(self.instructions, message, agent=self.name)
            except LLMError as exc:
                raise AgentError(str(exc)) from exc
            self.usage.calls += 1
            self.usage.input_tokens += reply.input_tokens
            self.usage.output_tokens += reply.output_tokens
            self.usage.model = reply.model
            try:
                data = parse_json(reply.text)
                problems = self.validate(data)
            except (ValueError, json.JSONDecodeError) as exc:
                problems = [f"invalid JSON: {exc}"]
            if not problems:
                return data
            message = (user_message + "\n\nYour previous reply was rejected: " + "; ".join(problems[:5]) +
                       "\nReturn ONLY the JSON object in the required shape.")
        raise AgentError(f"{self.name}: invalid output after retry ({'; '.join(problems[:3])})")


def require_list(data: Any, key: str) -> list[str]:
    if not isinstance(data, dict) or not isinstance(data.get(key), list):
        return [f'missing list "{key}"']
    return []
