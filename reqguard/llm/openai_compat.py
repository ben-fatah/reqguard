"""Client for any OpenAI-compatible chat API (DeepSeek, OpenAI, a DevAI chat endpoint, Ollama...).

Configured from environment variables, never from code, so no key is ever committed:
    REQGUARD_LLM_BASE_URL   e.g. https://api.deepseek.com
    REQGUARD_LLM_API_KEY    secret, kept in .env
    REQGUARD_LLM_MODEL      e.g. deepseek-chat
"""
from __future__ import annotations

import time

import httpx

from .base import LLMError, LLMReply, estimate_tokens


class OpenAICompatibleClient:
    name = "openai-compatible"

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 30.0,
                 json_mode: bool = True, transport: httpx.BaseTransport | None = None):
        if not base_url or not api_key or not model:
            raise LLMError("REQGUARD_LLM_BASE_URL, REQGUARD_LLM_API_KEY and REQGUARD_LLM_MODEL must all be set.")
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.json_mode = json_mode
        self._http = httpx.Client(timeout=timeout, transport=transport,
                                  headers={"Authorization": f"Bearer {api_key}"})

    def complete(self, system: str, user: str, *, agent: str) -> LLMReply:
        body = {
            "model": self.model,
            "temperature": 0,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        if self.json_mode:
            body["response_format"] = {"type": "json_object"}
        last_error = ""
        for attempt in range(2):  # one retry on network or 5xx errors (NFR-07)
            try:
                resp = self._http.post(self.url, json=body)
            except httpx.HTTPError as exc:
                last_error = f"network error: {exc.__class__.__name__}"
            else:
                if resp.status_code < 500:
                    break
                last_error = f"HTTP {resp.status_code}"
            if attempt == 0:
                time.sleep(1.0)
        else:
            raise LLMError(f"LLM unavailable for {agent}: {last_error}")
        if resp.status_code != 200:
            raise LLMError(f"LLM refused the request for {agent}: HTTP {resp.status_code} {resp.text[:200]}")
        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected LLM response shape for {agent}") from exc
        usage = data.get("usage") or {}
        return LLMReply(
            text=text,
            input_tokens=int(usage.get("prompt_tokens") or estimate_tokens(system + user)),
            output_tokens=int(usage.get("completion_tokens") or estimate_tokens(text)),
            model=str(data.get("model") or self.model),
        )
