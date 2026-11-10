"""Deploy and check ReqGuard's eight agents in DevAI (running locally).

    python -m reqguard.devai setup   create/update the 8 DevAI agents and their 8 flows, then verify
    python -m reqguard.devai check   list the 8 agents and 8 flows and whether each exists and is current
    python -m reqguard.devai ping    run the extractor flow on one line and print the reply and duration

Agent "reqguard-<name>": instructions = prompts/<name>.md + _shared.md (exactly what the Python
agent uses) + one line forbidding tools. Least privilege: DevAI cannot run an agent with no tools
(an empty list falls back to its full default set), so each agent gets the smallest set it allows:
read, list and the to-do planner. Its flow runs in an empty sandbox folder, so read/list see nothing.

Flow "reqguard-<name>": webhook trigger -> agent node (prompt {{trigger.payload.message}}) -> output.
Only ids starting with "reqguard-" are created or changed; other DevAI agents and flows are untouched.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import zipfile

import httpx

from .agents.base import load_prompt
from .env import load_env
from .llm.base import LLMError
from .llm.devai_flow import (NOT_RUNNING, DevAIFlowClient, devai_home, devai_id, devai_instructions)

AGENTS = {   # ReqGuard agent name -> display label
    "idea_to_srs": "Idea-to-SRS", "extractor": "Extractor", "functional": "Functional",
    "non_functional": "Non-functional", "security": "Security", "consistency": "Consistency",
    "judge": "Judge", "test_writer": "Test-writer",
}
PLACEHOLDER = "{{trigger.payload.message}}"
ALLOWED_TOOLS = [{"name": t, "requireApproval": False} for t in ("read_file", "list_directory", "todo_read")]
VERSION = "1.0.0"


def sandbox_dir():
    return devai_home() / "playground" / "reqguard-sandbox"


def system_prompt(name: str) -> str:
    return devai_instructions(load_prompt(name))


def agent_zip(name: str) -> bytes:
    meta = {
        "id": devai_id(name),
        "name": f"ReqGuard {AGENTS[name]}",
        "description": f"ReqGuard {AGENTS[name]} agent. Called by the ReqGuard orchestrator; replies with JSON only.",
        "allowedTools": ALLOWED_TOOLS,
        "temperature": 0,
        "version": VERSION,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("agent.json", json.dumps(meta, indent=2))
        z.writestr("instructions/system-prompt.md", system_prompt(name))
    return buf.getvalue()


def flow_body(name: str) -> dict:
    fid, label = devai_id(name), AGENTS[name]
    return {
        "id": fid,
        "name": f"ReqGuard {label}",
        "description": f"ReqGuard {label} agent: webhook {{\"message\": ...}} -> agent {fid} -> output.",
        "workingDirectory": str(sandbox_dir()),
        "nodes": [
            {"id": "trigger", "type": "trigger", "position": {"x": 250, "y": 50},
             "data": {"label": "Webhook", "referenceName": "trigger", "triggerType": "webhook"}},
            {"id": "agent", "type": "agent", "position": {"x": 250, "y": 200},
             "data": {"label": label, "referenceName": "agent", "prompt": PLACEHOLDER,
                      "agentId": fid, "agentName": f"ReqGuard {label}"}},
            {"id": "output", "type": "output", "position": {"x": 250, "y": 350},
             "data": {"label": "Reply", "referenceName": "reply", "format": "text"}},
        ],
        "edges": [{"id": "e1", "source": "trigger", "target": "agent"},
                  {"id": "e2", "source": "agent", "target": "output"}],
    }


class DevAI:
    def __init__(self, client: DevAIFlowClient):
        self.flow_url, self.host_url = client.base_url, client.host_url
        self.http = httpx.Client(timeout=30.0)

    def agent_ids(self) -> set[str]:
        resp = self.http.get(self.host_url + "/api/agents")
        resp.raise_for_status()
        return {a["id"] for a in resp.json().get("agents", [])}

    def flow_ids(self) -> set[str]:
        resp = self.http.get(self.flow_url + "/api/flows")
        resp.raise_for_status()
        return {f["id"] for f in resp.json()}

    def flow_data(self, fid: str) -> dict | None:
        resp = self.http.get(f"{self.flow_url}/api/flows/{fid}/data")
        return resp.json() if resp.status_code == 200 else None

    def save_agent(self, name: str) -> None:
        files = {"file": (f"{devai_id(name)}.zip", agent_zip(name), "application/zip")}
        resp = self.http.post(self.host_url + "/api/agents", files=files)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"agent {devai_id(name)}: HTTP {resp.status_code} {resp.text[:200]}")

    def save_flow(self, name: str) -> None:
        resp = self.http.put(f"{self.flow_url}/api/flows/{devai_id(name)}", json=flow_body(name))
        if resp.status_code != 200:
            raise RuntimeError(f"flow {devai_id(name)}: HTTP {resp.status_code} {resp.text[:200]}")


def status_rows(api: DevAI) -> list[dict]:
    agents, flows = api.agent_ids(), api.flow_ids()
    rows = []
    for name in AGENTS:
        fid = devai_id(name)
        prompt_file = devai_home() / "agents" / fid / "instructions" / "system-prompt.md"
        try:
            prompt_ok = prompt_file.read_text(encoding="utf-8").replace("\r\n", "\n") == system_prompt(name)
        except OSError:
            prompt_ok = False
        data = api.flow_data(fid) if fid in flows else None
        node = next((n["data"] for n in (data or {}).get("nodes", []) if n.get("type") == "agent"), {})
        flow_ok = bool(data) and data.get("workingDirectory") == str(sandbox_dir()) \
            and node.get("agentId") == fid and node.get("prompt") == PLACEHOLDER
        rows.append({"name": name, "id": fid, "agent": fid in agents, "prompt": prompt_ok,
                     "flow": fid in flows, "flow_ok": flow_ok})
    return rows


def print_rows(rows: list[dict]) -> bool:
    yn = lambda b: "yes" if b else "NO"
    print(f"{'DevAI id':<26} {'agent':<6} {'prompt current':<15} {'flow':<6} {'flow config':<11}")
    for r in rows:
        print(f"{r['id']:<26} {yn(r['agent']):<6} {yn(r['prompt']):<15} {yn(r['flow']):<6} {yn(r['flow_ok']):<11}")
    ok = all(r["agent"] and r["prompt"] and r["flow"] and r["flow_ok"] for r in rows)
    print(f"\n{sum(r['agent'] for r in rows)}/8 agents, {sum(r['flow'] for r in rows)}/8 flows",
          "- all current" if ok else "- run `python -m reqguard.devai setup`")
    return ok


def print_sandbox() -> bool:
    box = sandbox_dir()
    if not box.is_dir():
        print(f"Sandbox {box}: MISSING")
        return False
    content = list(box.iterdir())
    print(f"Sandbox {box}: {'empty' if not content else f'NOT EMPTY ({len(content)} entries) - empty it'}")
    return not content


def cmd_setup(client: DevAIFlowClient) -> int:
    api = DevAI(client)
    sandbox_dir().mkdir(parents=True, exist_ok=True)
    for name in AGENTS:
        api.save_agent(name)
        api.save_flow(name)
        print(f"saved agent + flow {devai_id(name)}")
    # PUT writes the flow file; DevAI's file watcher registers it a moment later.
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not all(devai_id(n) in api.flow_ids() for n in AGENTS):
        time.sleep(0.5)
    print("\nVerified with GET /api/agents and GET /api/flows:")
    ok = print_rows(status_rows(api))
    ok = print_sandbox() and ok
    print("Model (global DevAI setting):", client.model)
    return 0 if ok else 1


def cmd_check(client: DevAIFlowClient) -> int:
    ok = print_rows(status_rows(DevAI(client)))
    ok = print_sandbox() and ok
    print("Model (global DevAI setting):", client.model)
    return 0 if ok else 1


def cmd_ping(client: DevAIFlowClient, text: str) -> int:
    message = "<document>\n" + text + "\n</document>"
    start = time.monotonic()
    try:
        reply = client.complete(load_prompt("extractor"), message, agent="extractor")
    except LLMError as exc:
        print("Error:", exc, file=sys.stderr)
        return 1
    print(f"Flow: {devai_id('extractor')}   model: {reply.model}   duration: {time.monotonic() - start:.1f} s")
    print("Sent :", text)
    print("Reply:", reply.text)
    return 0


def main(argv: list[str] | None = None) -> int:
    load_env()
    p = argparse.ArgumentParser(prog="python -m reqguard.devai", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="create/update the 8 agents and 8 flows in DevAI")
    sub.add_parser("check", help="show whether each agent and flow exists and is current")
    ping = sub.add_parser("ping", help="run the extractor flow on one line of text")
    ping.add_argument("text", nargs="?", default="REQ-1: The system shall let a librarian add a book.")
    args = p.parse_args(argv)

    client = DevAIFlowClient.from_env()
    try:
        if args.cmd == "setup":
            return cmd_setup(client)
        if args.cmd == "check":
            return cmd_check(client)
        return cmd_ping(client, args.text)
    except httpx.ConnectError:
        print(f"Error: {NOT_RUNNING} (flows {client.base_url}, host {client.host_url})", file=sys.stderr)
        return 2
    except (httpx.HTTPError, RuntimeError) as exc:
        print("Error:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
