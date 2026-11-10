"""DevAIFlowClient against a fake DevAI (httpx.MockTransport): no DevAI, no network."""
import io
import json
import logging
import zipfile
from pathlib import Path

import httpx
import pytest

from reqguard import devai
from reqguard.agents.base import load_prompt
from reqguard.env import load_env
from reqguard.llm import DevAIFlowClient, LLMError, MockLLM, get_client
from reqguard.llm.devai_flow import NO_TOOLS_LINE, devai_instructions
from reqguard.pipeline import Orchestrator
from reqguard.report import build_report

ROOT = Path(__file__).resolve().parent.parent
FLOWS, HOST = "http://flows.test", "http://host.test"
MODEL = "anthropic/claude-haiku-4.5"


@pytest.fixture(autouse=True)
def isolated_devai_home(tmp_path, monkeypatch):
    """Never read the real ~/.devai from tests."""
    monkeypatch.setenv("DEVAI_HOME", str(tmp_path / "devai-home"))


class FakeDevAI:
    """Answers like DevAI: host root, webhook start, run polling, cancel."""

    def __init__(self, statuses, output='{"requirements": []}', error=None):
        self.statuses = list(statuses)    # one status per poll; the last one repeats
        self.output, self.error = output, error
        self.webhooks, self.polls, self.cancels, self.bodies = 0, 0, 0, []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.url.host == "host.test" and path == "/":
            return httpx.Response(200, json={"ok": True, "modelId": MODEL})
        if request.method == "POST" and path == "/webhook/reqguard-extractor":
            self.webhooks += 1
            self.bodies.append(json.loads(request.read()))
            return httpx.Response(202, json={"status": "accepted", "runId": f"run-{self.webhooks}"})
        if request.method == "POST" and path.endswith("/cancel"):
            self.cancels += 1
            return httpx.Response(200, json={"ok": True})
        if request.method == "GET" and path.startswith("/api/flows/reqguard-extractor/runs/"):
            self.polls += 1
            status = self.statuses[min(self.polls - 1, len(self.statuses) - 1)]
            steps = [{"nodeType": "trigger", "output": {"message": "x"}},
                     {"nodeType": "agent", "status": status, "activity": [],
                      "output": self.output if status == "success" else None,
                      "error": self.error, "startedAt": "t0", "completedAt": "t1"}]
            return httpx.Response(200, json={"status": status, "steps": steps,
                                             "error": self.error if status == "failed" else None})
        return httpx.Response(404, json={"error": "not found"})


def make(handler, timeout=180.0):
    return DevAIFlowClient(FLOWS, HOST, timeout=timeout, poll_interval=0,
                           transport=httpx.MockTransport(handler), sleep=lambda s: None)


def test_success_returns_agent_step_output_and_global_model():
    fake = FakeDevAI(["running", "running", "success"], output='{"requirements": [{"text": "A", "line": 1}]}')
    reply = make(fake).complete("system text", "<document>\nA\n</document>", agent="extractor")
    assert reply.text == '{"requirements": [{"text": "A", "line": 1}]}'
    assert reply.model == MODEL
    assert reply.input_tokens > 0 and reply.output_tokens > 0
    assert fake.bodies == [{"message": "<document>\nA\n</document>"}]   # sent verbatim, never escaped
    assert (fake.webhooks, fake.polls) == (1, 3)


def test_failed_run_is_retried_once_then_raises():
    fake = FakeDevAI(["failed"], error="model gateway error")
    with pytest.raises(LLMError, match="model gateway error"):
        make(fake).complete("s", "u", agent="extractor")
    assert fake.webhooks == 2   # one retry, never more


def test_failed_run_then_success_on_the_retry():
    fake = FakeDevAI(["failed", "success"])
    assert make(fake).complete("s", "u", agent="extractor").text == '{"requirements": []}'
    assert fake.webhooks == 2


def test_timeout_cancels_the_run_and_is_not_retried():
    fake = FakeDevAI(["running"])
    with pytest.raises(LLMError, match="timed out"):
        make(fake, timeout=0).complete("s", "u", agent="extractor")
    assert fake.webhooks == 1 and fake.cancels == 1


def test_connection_refused_says_devai_is_not_running():
    calls = []

    def refused(request):
        calls.append(request.url.path)
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(LLMError, match="DevAI is not running: open DevAI Desktop"):
        make(refused).complete("s", "u", agent="extractor")
    assert calls.count("/webhook/reqguard-extractor") == 1


def test_missing_flow_tells_the_user_to_run_setup():
    with pytest.raises(LLMError, match="reqguard.devai setup"):
        make(FakeDevAI(["success"])).complete("s", "u", agent="judge")   # no reqguard-judge flow


def test_double_braces_log_a_warning_but_text_is_unchanged(caplog):
    fake = FakeDevAI(["success"])
    with caplog.at_level(logging.WARNING, logger="reqguard.devai"):
        make(fake).complete("s", "The {{x.output}} field", agent="extractor")
    assert "template engine" in caplog.text
    assert fake.bodies[0]["message"] == "The {{x.output}} field"


def test_model_is_read_once_per_run():
    host_calls = []

    def handler(request):
        if request.url.host == "host.test":
            host_calls.append(1)
        return FakeDevAI(["success"])(request)

    client = make(handler)
    client.begin_run()
    client.complete("s", "u", agent="extractor")
    client.complete("s", "u", agent="extractor")
    assert len(host_calls) == 1
    client.begin_run()
    assert len(host_calls) == 2


def test_get_client_selects_devai(monkeypatch):
    monkeypatch.setenv("REQGUARD_LLM", "devai")
    monkeypatch.setenv("REQGUARD_DEVAI_URL", "http://127.0.0.1:9999/")
    monkeypatch.setenv("REQGUARD_DEVAI_TIMEOUT", "42")
    client = get_client()
    assert isinstance(client, DevAIFlowClient)
    assert client.base_url == "http://127.0.0.1:9999" and client.timeout == 42


def test_usage_records_the_model_and_the_report_shows_it():
    bench = (ROOT / "benchmark" / "srs_inventory_v1.md").read_text(encoding="utf-8")
    r = Orchestrator(MockLLM()).review(text=bench)
    assert {u.model for u in r.usage} == {"mock"}
    run = {"id": 1, "created_at": "now", "source_type": "srs", "score": r.score, "grade": r.grade,
           "requirements": [], "findings": [], "tests": [], "summary": "", "dropped": [],
           "usage": [{"agent": "judge", "model": "mock"}]}
    assert "- Model: mock" in build_report(run)
    assert "- Model: not recorded" in build_report({**run, "usage": [{"agent": "judge"}]})


def test_env_loader_does_not_override_existing_variables(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("# comment\nREQGUARD_T1=from_file\nexport REQGUARD_T2=\"quoted value\"\nREQGUARD_T3=x\n\n",
                   encoding="utf-8")
    monkeypatch.delenv("REQGUARD_T1", raising=False)
    monkeypatch.delenv("REQGUARD_T2", raising=False)
    monkeypatch.setenv("REQGUARD_T3", "already set")
    applied = load_env(env)
    import os
    assert os.environ["REQGUARD_T1"] == "from_file" and os.environ["REQGUARD_T2"] == "quoted value"
    assert os.environ["REQGUARD_T3"] == "already set" and "REQGUARD_T3" not in applied
    for key in applied:
        monkeypatch.delenv(key)


def test_setup_payloads_are_least_privilege_and_use_the_exact_prompts():
    for name in devai.AGENTS:
        with zipfile.ZipFile(io.BytesIO(devai.agent_zip(name))) as z:
            meta = json.loads(z.read("agent.json"))
            prompt = z.read("instructions/system-prompt.md").decode("utf-8")
        assert prompt == devai_instructions(load_prompt(name)) and prompt.rstrip().endswith(NO_TOOLS_LINE)
        assert {t["name"] for t in meta["allowedTools"]} == {"read_file", "list_directory", "todo_read"}
        assert meta["temperature"] == 0
        flow = devai.flow_body(name)
        agent_node = next(n for n in flow["nodes"] if n["type"] == "agent")
        assert agent_node["data"]["prompt"] == "{{trigger.payload.message}}"
        assert agent_node["data"]["agentId"] == flow["id"] == f"reqguard-{name}"
        assert flow["workingDirectory"].endswith("reqguard-sandbox")
