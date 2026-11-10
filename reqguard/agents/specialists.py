"""The four specialist reviewers. Each one = its Python rule pack first, then AI advice.

Rule findings are the source of truth (ADR-002). The AI may enrich a rule finding
with a rewrite (same rule_id) or add a new advisory finding (rule_id null).
AI findings that point at unknown requirement IDs are discarded.
"""
from __future__ import annotations

import json
from typing import Any

from ..models import Finding, Requirement
from ..rules import PACKS
from .base import Agent, AgentError, require_list

_SEVERITIES = {"high", "medium", "low"}


class SpecialistAgent(Agent):
    def validate(self, data: Any) -> list[str]:
        problems = require_list(data, "findings")
        if problems:
            return problems
        for f in data["findings"]:
            if not isinstance(f, dict) or not str(f.get("problem", "")).strip():
                return ['every finding needs a "problem"']
            if f.get("severity") not in _SEVERITIES:
                return ['"severity" must be high, medium or low']
        return []

    def rule_findings(self, requirements: list[Requirement]) -> list[Finding]:
        return PACKS[self.name](requirements)

    def review(self, requirements: list[Requirement]) -> tuple[list[Finding], list[dict], str | None]:
        """Return (rule findings, raw AI advice, error). An AI failure never loses rule findings (NFR-07)."""
        rules = self.rule_findings(requirements)
        payload = {
            "requirements": [{"id": r.id, "text": r.text, "kind": r.kind} for r in requirements],
            "rule_findings": [{"req_id": f.req_id, "rule_id": f.rule_id, "problem": f.problem} for f in rules],
        }
        try:
            data = self.call(json.dumps(payload))
        except AgentError as exc:
            return rules, [], str(exc)
        valid_ids = {r.id for r in requirements}
        advice = []
        for f in data["findings"]:
            rid = f.get("req_id")
            if rid is not None and rid not in valid_ids:
                continue   # the model referred to a requirement that does not exist
            advice.append({
                "req_id": rid,
                "rule_id": f.get("rule_id") or None,
                "problem": str(f["problem"]).strip(),
                "suggestion": (str(f.get("suggestion")).strip() or None) if f.get("suggestion") else None,
                "severity": f["severity"],
                "related": [x for x in (f.get("related") or []) if x in valid_ids],
                "agent": self.name,
            })
        return rules, advice, None


class FunctionalAgent(SpecialistAgent):
    name = "functional"


class NonFunctionalAgent(SpecialistAgent):
    name = "non_functional"


class SecurityAgent(SpecialistAgent):
    name = "security"


class ConsistencyAgent(SpecialistAgent):
    name = "consistency"


SPECIALISTS = (FunctionalAgent, NonFunctionalAgent, SecurityAgent, ConsistencyAgent)
