"""Client that runs each ReqGuard agent as a DevAI agent inside a DevAI flow.

Every agent <name> has a DevAI agent "reqguard-<name>" (its instructions are
prompts/<name>.md + _shared.md, deployed by `python -m reqguard.devai setup`) and a
flow "reqguard-<name>": webhook trigger -> agent -> output. A call is:

    POST {REQGUARD_DEVAI_URL}/webhook/reqguard-<name>   {"message": <user message>}
    GET  {REQGUARD_DEVAI_URL}/api/flows/reqguard-<name>/runs/<runId>   (every 1 s)

The agent's reply is the "output" of the run step whose nodeType is "agent".
The `system` argument is not sent: the DevAI agent already holds the same text,
and a warning is logged if the deployed copy is out of date.

The model is a global DevAI setting, so it is read once per run from
GET {REQGUARD_DEVAI_HOST_URL}/ ("modelId") and returned as LLMReply.model.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from .base import LLMError, LLMReply, estimate_tokens

log = logging.getLogger("reqguard.devai")

DEFAULT_FLOW_URL = "http://127.0.0.1:7583"
DEFAULT_HOST_URL = "http://127.0.0.1:7588"
DEFAULT_TIMEOUT = 180.0
PREFIX = "reqguard-"
NOT_RUNNING = "DevAI is not running: open DevAI Desktop"
NO_TOOLS_LINE = "Do not use any tools. Answer only from the message."
UNKNOWN_MODEL = "devai/unknown-model"
_WAITING = {"running", "pending", "queued", "accepted"}


def devai_id(agent: str) -> str:
    """DevAI agent id and flow id for a ReqGuard agent name (they are the same)."""
    return PREFIX + agent


def devai_instructions(system: str) -> str:
    """The exact system-prompt.md deployed for an agent whose ReqGuard instructions are `system`."""
    return system.strip() + "\n\n" + NO_TOOLS_LINE + "\n"


def devai_home() -> Path:
    return Path(os.getenv("DEVAI_HOME") or Path.home() / ".devai")


class _RunFailed(Exception):
    """A DevAI run failed or the server returned 5xx: worth one retry."""


class DevAIFlowClient:
    name = "devai-flow"

    def __init__(self, base_url: str = DEFAULT_FLOW_URL, host_url: str = DEFAULT_HOST_URL,
                 timeout: float = DEFAULT_TIMEOUT, poll_interval: float = 1.0,
                 transport: httpx.BaseTransport | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        self.base_url = base_url.rstrip("/")
        self.host_url = host_url.rstrip("/")
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._sleep = sleep
        self._http = httpx.Client(timeout=15.0, transport=transport)
        self._model: str | None = None
        self._lock = threading.Lock()
        self._prompt_checked: set[str] = set()

    @classmethod
    def from_env(cls) -> "DevAIFlowClient":
        return cls(base_url=os.getenv("REQGUARD_DEVAI_URL") or DEFAULT_FLOW_URL,
                   host_url=os.getenv("REQGUARD_DEVAI_HOST_URL") or DEFAULT_HOST_URL,
                   timeout=float(os.getenv("REQGUARD_DEVAI_TIMEOUT") or DEFAULT_TIMEOUT))

    # ---- model traceability -------------------------------------------------
    def begin_run(self) -> None:
        """Called by the orchestrator at the start of each run: read DevAI's current model once."""
        with self._lock:
            self._model = self._fetch_model()

    @property
    def model(self) -> str:
        with self._lock:
            if self._model is None:
                self._model = self._fetch_model()
            return self._model

    def _fetch_model(self) -> str:
        try:
            resp = self._http.get(self.host_url + "/")
            model = resp.json().get("modelId") if resp.status_code == 200 else None
        except (httpx.HTTPError, ValueError, AttributeError):
            model = None
        if not model:
            log.warning("Could not read modelId from the DevAI host at %s", self.host_url)
        return str(model or UNKNOWN_MODEL)

    # ---- one agent call -------------------------------------------------------
    def complete(self, system: str, user: str, *, agent: str) -> LLMReply:
        fid = devai_id(agent)
        if "{{" in user:
            log.warning("%s: the message contains '{{'; DevAI's template engine may alter that text", fid)
        self._check_deployed_prompt(agent, system)
        model = self.model
        start = time.monotonic()
        log.info("%s: start", fid)
        for attempt in range(2):   # at most one retry, only for a failed run or a 5xx
            try:
                text, step = self._run_once(fid, user)
                break
            except _RunFailed as exc:
                if attempt == 1:
                    raise LLMError(f"DevAI flow {fid} failed: {exc}") from None
                log.warning("%s: %s; retrying once", fid, exc)
        log.info("%s: end after %.1f s (DevAI agent step %s -> %s)", fid, time.monotonic() - start,
                 step.get("startedAt"), step.get("completedAt"))
        return LLMReply(text, estimate_tokens(system + user), estimate_tokens(text), model)

    def _run_once(self, fid: str, user: str) -> tuple[str, dict]:
        try:
            resp = self._http.post(f"{self.base_url}/webhook/{fid}", json={"message": user})
        except httpx.ConnectError as exc:
            raise LLMError(NOT_RUNNING) from exc
        except httpx.HTTPError as exc:
            raise _RunFailed(f"network error: {exc.__class__.__name__}") from exc
        if resp.status_code == 404:
            raise LLMError(f"DevAI flow {fid!r} not found: run `python -m reqguard.devai setup`")
        if resp.status_code >= 500:
            raise _RunFailed(f"HTTP {resp.status_code} starting the run")
        if resp.status_code >= 400:
            raise LLMError(f"DevAI refused to start {fid}: HTTP {resp.status_code} {resp.text[:200]}")
        run_id = _json(resp).get("runId")
        if not run_id:
            raise LLMError(f"DevAI did not return a runId for {fid}")

        deadline = time.monotonic() + self.timeout
        while True:
            self._sleep(self.poll_interval)
            run = self._poll(fid, run_id)
            status = run.get("status") if run else None
            if status == "success":
                return self._agent_output(fid, run)
            if run is not None and status not in _WAITING:
                raise _RunFailed(f"run {run_id} ended with status {status!r}: {_run_error(run)}")
            if time.monotonic() >= deadline:
                self._cancel(fid, run_id)
                raise LLMError(f"DevAI flow {fid} timed out after {self.timeout:.0f} s (run {run_id})")

    def _poll(self, fid: str, run_id: str) -> dict | None:
        try:
            resp = self._http.get(f"{self.base_url}/api/flows/{fid}/runs/{run_id}")
        except httpx.ConnectError as exc:
            raise LLMError(NOT_RUNNING) from exc
        except httpx.HTTPError:
            return None   # a slow poll is not a failed run; the deadline still applies
        return _json(resp) if resp.status_code == 200 else None

    def _cancel(self, fid: str, run_id: str) -> None:
        try:
            self._http.post(f"{self.base_url}/api/flows/{fid}/runs/{run_id}/cancel")
        except httpx.HTTPError:
            pass

    @staticmethod
    def _agent_output(fid: str, run: dict) -> tuple[str, dict]:
        steps = [s for s in run.get("steps") or [] if s.get("nodeType") == "agent"]
        if not steps or steps[-1].get("output") is None:
            raise LLMError(f"DevAI run for {fid} finished without an agent output")
        step = steps[-1]
        if step.get("activity"):
            log.warning("%s: the DevAI agent used tools (%d activity entries)", fid, len(step["activity"]))
        out = step["output"]
        return (out if isinstance(out, str) else json.dumps(out)), step

    def _check_deployed_prompt(self, agent: str, system: str) -> None:
        """Warn once per agent if the DevAI copy of the instructions differs from prompts/*.md."""
        if agent in self._prompt_checked:
            return
        self._prompt_checked.add(agent)
        path = devai_home() / "agents" / devai_id(agent) / "instructions" / "system-prompt.md"
        try:
            deployed = path.read_text(encoding="utf-8")
        except OSError:
            return   # DevAI may run elsewhere; the flow call itself reports a missing agent
        if deployed.replace("\r\n", "\n") != devai_instructions(system):
            log.warning("%s: DevAI instructions differ from reqguard/prompts; run `python -m reqguard.devai setup`",
                        devai_id(agent))


def _json(resp: httpx.Response) -> dict[str, Any]:
    try:
        data = resp.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _run_error(run: dict) -> str:
    if run.get("error"):
        return str(run["error"])[:300]
    for step in run.get("steps") or []:
        if step.get("error"):
            return f"{step.get('nodeType')} step: {str(step['error'])[:300]}"
    return "no error message"
