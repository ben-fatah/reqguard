"""Offline mock model so the whole system runs, demos and tests with no API key.

It is deterministic and clearly limited: it only produces template rewrites
for problems the rules already found. It answers in the same JSON shapes a real
model must use, so every agent, validator and the orchestrator run unchanged.
"""
from __future__ import annotations

import json
import re

from .base import LLMReply, estimate_tokens

_MODAL = re.compile(r"\b(should|may|might|could)\b", re.IGNORECASE)
_DOC = re.compile(r"<document>\n?(.*?)\n?</document>", re.DOTALL)
_REQ_LINE = re.compile(r"\b(shall|should|must|may|will)\b", re.IGNORECASE)
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)]|REQ-\d+[:.)]?)\s*")

MEASURABLE = {
    "within an acceptable time": "within 2 seconds", "in an acceptable time": "within 2 seconds",
    "highly available": "available 99.5% of each calendar month",
    "quickly": "within 2 seconds for 95% of requests", "quick": "within 2 seconds",
    "fast": "within 2 seconds for 95% of requests",
    "user-friendly": "usable by a first-time user without help in under 3 minutes",
    "easy": "possible for a first-time user without help in under 3 minutes",
    "intuitive": "usable by a first-time user without help in under 3 minutes",
    "simple": "completable in at most 3 steps",
    "many": "at least 100", "accurate": "correct to within 0.1%",
}


def _shall(text: str) -> str:
    return _MODAL.sub("shall", text, count=1)


def _rewrite(text: str, rule_id: str | None) -> str:
    t = text.rstrip(".")
    if rule_id == "R2":
        return _shall(text)
    if rule_id in ("R1", "R5"):
        out = _shall(t)
        for word, target in MEASURABLE.items():
            out = re.sub(rf"\b{re.escape(word)}\b", target, out, flags=re.IGNORECASE)
        if out == _shall(t):
            out += " [add a measurable target: number and unit]"
        return out.replace(" ,", ",").rstrip(",") + "."
    if rule_id == "R3":
        return re.sub(r",?\s*(etc\.?|tbd|tbc|and so on)", " [list every item]", t, flags=re.IGNORECASE) + "."
    if rule_id == "R4":
        parts = re.split(r"\s+and\s+(?=shall\b|must\b)", t, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            subject = re.match(r"^(.*?)\b(shall|must)\b", parts[0], re.IGNORECASE)
            subj = subject.group(1).strip() if subject else "The system"
            return f"{parts[0]}. {subj} {parts[1]}."
        return text
    if rule_id == "R6":
        return f"{t} by [the system / an administrator: name the actor]."
    if rule_id == "F1":
        return t + ". If the action fails or the item already exists, the system shall show an error message and keep the user's input."
    if rule_id == "S1":
        return "Passwords shall be stored hashed with bcrypt and a unique salt per user."
    if rule_id == "S2":
        return t + " after 15 minutes of inactivity."
    if rule_id == "S3":
        return t + ". Only authorised staff shall view it, and it shall be encrypted at rest."
    return text


def _respond(agent: str, user: str) -> dict:
    if agent == "idea_to_srs":
        idea = json.loads(user).get("idea", "").strip().rstrip(".")
        thing = idea[:80] or "the product"
        return {"title": f"Draft SRS: {thing}", "requirements": [
            {"text": "The system shall allow a visitor to register an account with an email address and a password."},
            {"text": "The system shall allow a registered user to log in with their email address and password."},
            {"text": "Passwords shall be stored."},
            {"text": f"The system shall let a logged-in user use the main feature: {thing}."},
            {"text": "The system shall allow an administrator to add, edit and remove records."},
            {"text": "The system should notify the user when their request is confirmed."},
            {"text": "The system shall respond quickly."},
            {"text": "The system shall log out a user after 15 minutes of inactivity."},
        ]}
    if agent == "extractor":
        m = _DOC.search(user)
        doc = m.group(1) if m else user
        reqs = []
        for i, line in enumerate(doc.splitlines(), start=1):
            text = _BULLET.sub("", line).strip()
            if text and not text.startswith("#") and _REQ_LINE.search(text):
                reqs.append({"text": text, "line": i})
        return {"requirements": reqs}
    if agent in ("functional", "non_functional", "security", "consistency"):
        payload = json.loads(user)
        texts = {r["id"]: r["text"] for r in payload.get("requirements", [])}
        out = []
        for f in payload.get("rule_findings", []):
            rid, rule = f.get("req_id"), f.get("rule_id")
            if rule == "S4":
                out.append({"req_id": None, "rule_id": rule, "problem": f["problem"], "severity": "high",
                            "suggestion": "Add: The system shall require users to log in with an email address and password before using any feature."})
            elif rule in ("C1", "C2"):
                out.append({"req_id": rid, "rule_id": rule, "problem": f["problem"], "severity": "medium",
                            "suggestion": "Agree one value with the stakeholder and use it in every related requirement."})
            elif rid in texts:
                out.append({"req_id": rid, "rule_id": rule, "problem": f["problem"], "severity": "medium",
                            "suggestion": _rewrite(texts[rid], rule)})
        return {"findings": out}
    if agent == "judge":
        payload = json.loads(user)
        n = len(payload.get("findings", []))
        high = sum(1 for f in payload.get("findings", []) if f.get("severity") == "high")
        return {"summary": f"{n} findings, {high} of them high severity. Fix the high-severity items first, "
                           f"then make every quality requirement measurable. (Offline mock summary.)"}
    if agent == "test_writer":
        payload = json.loads(user)
        tests = []
        for r in payload.get("requirements", []):
            text = r["text"].rstrip(".")
            action = re.split(r"\b(?:shall|must|should)\b", text, maxsplit=1, flags=re.IGNORECASE)
            what = action[1].strip() if len(action) > 1 else text
            tests.append({"req_id": r["id"], "given": "the system is running and the user has the required role",
                          "when": f"the user triggers: {what}", "then": f"the observable result satisfies: {text}"})
        return {"tests": tests}
    return {}


class MockLLM:
    """Deterministic stand-in for a real model. Set REQGUARD_LLM=openai to use a real one."""
    name = "mock"

    def __init__(self, fail_agents: set[str] | None = None, bad_json_once: set[str] | None = None):
        self.fail_agents = fail_agents or set()          # simulate an outage for these agents
        self.bad_json_once = set(bad_json_once or set())  # first reply is invalid JSON (tests the retry)
        self.calls: list[str] = []

    def complete(self, system: str, user: str, *, agent: str) -> LLMReply:
        from .base import LLMError
        self.calls.append(agent)
        if agent in self.fail_agents:
            raise LLMError(f"Mock outage for {agent}")
        if agent in self.bad_json_once:
            self.bad_json_once.discard(agent)
            text = "Sure! Here are the findings you asked for."
        else:
            text = json.dumps(_respond(agent, user))
        return LLMReply(text, estimate_tokens(system + user), estimate_tokens(text), "mock")
