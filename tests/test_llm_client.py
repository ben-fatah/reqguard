"""OpenAI-compatible client against a fake HTTP server (no network, no key)."""
import json

import httpx
import pytest

from reqguard.llm import LLMError, OpenAICompatibleClient


def client(handler):
    return OpenAICompatibleClient("https://llm.example", "fake-key", "test-model",
                                  transport=httpx.MockTransport(handler))


def test_sends_model_messages_and_reads_usage():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = request.read().decode()
        return httpx.Response(200, json={"model": "test-model",
                                         "choices": [{"message": {"content": '{"ok": true}'}}],
                                         "usage": {"prompt_tokens": 12, "completion_tokens": 3}})

    reply = client(handler).complete("sys", "user", agent="extractor")
    assert reply.text == '{"ok": true}' and (reply.input_tokens, reply.output_tokens) == (12, 3)
    body = json.loads(seen["body"])
    assert seen["auth"] == "Bearer fake-key"
    assert body["model"] == "test-model" and body["temperature"] == 0
    assert [m["role"] for m in body["messages"]] == ["system", "user"]


def test_retries_once_on_server_error_then_fails(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503)

    with pytest.raises(LLMError, match="unavailable"):
        client(handler).complete("s", "u", agent="judge")
    assert len(calls) == 2


def test_client_error_is_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(401, text="bad key")

    with pytest.raises(LLMError, match="HTTP 401"):
        client(handler).complete("s", "u", agent="judge")
    assert len(calls) == 1


def test_missing_configuration():
    with pytest.raises(LLMError):
        OpenAICompatibleClient("", "", "")
