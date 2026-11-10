"""Judge: merges specialist output, removes duplicates, ranks, scores, summarises.

Merging and scoring are deterministic Python (testable). The LLM only writes
the short summary; if it fails, a plain summary is generated instead.
"""
from __future__ import annotations

import json
from typing import Any

from ..models import SEVERITY_ORDER, Finding, Requirement
from .base import Agent, AgentError

PENALTY = {"high": 30, "medium": 15, "low": 5}
DOC_PENALTY = {"high": 10, "medium": 5, "low": 2}


def merge(rule_findings: list[Finding], advice: list[dict]) -> list[Finding]:
    """Attach AI rewrites to matching rule findings; keep new AI findings as advisory."""
    merged = list(rule_findings)
    by_key = {(f.req_id, f.rule_id): f for f in merged if f.rule_id}
    for a in advice:
        target = by_key.get((a["req_id"], a["rule_id"])) if a["rule_id"] else None
        if target is not None:
            if a["suggestion"] and not target.suggestion:
                target.suggestion = a["suggestion"]
            continue
        merged.append(Finding(a["req_id"], a["agent"], "ai", a["severity"], a["problem"],
                              suggestion=a["suggestion"], related=a.get("related", [])))
    return dedupe(merged)


def dedupe(findings: list[Finding]) -> list[Finding]:
    seen: dict[tuple, Finding] = {}
    for f in findings:
        k = f.key()
        if k in seen:
            keep = seen[k]
            if SEVERITY_ORDER[f.severity] < SEVERITY_ORDER[keep.severity]:
                keep.severity = f.severity
            keep.suggestion = keep.suggestion or f.suggestion
        else:
            seen[k] = f
    return list(seen.values())


def rank(findings: list[Finding], requirements: list[Requirement]) -> list[Finding]:
    order = {r.id: i for i, r in enumerate(requirements)}
    ranked = sorted(findings, key=lambda f: (SEVERITY_ORDER[f.severity], f.source != "rule",
                                             order.get(f.req_id, -1), f.rule_id or ""))
    for i, f in enumerate(ranked, start=1):
        f.id = f"F-{i:03d}"
    return ranked


def score(findings: list[Finding], requirements: list[Requirement]) -> int:
    """Average per-requirement score (100 minus penalties), minus document-level penalties.

    Only rule findings count (ADR-005): they are deterministic, so the same document always
    gets the same score. AI advisory findings are shown, ranked and counted, but not scored.
    """
    if not requirements:
        return 0
    per_req = {r.id: 100 for r in requirements}
    doc_penalty = 0
    for f in findings:
        if f.source != "rule":
            continue

        if f.req_id in per_req:
            per_req[f.req_id] = max(0, per_req[f.req_id] - PENALTY[f.severity])
        elif f.req_id is None:
            doc_penalty += DOC_PENALTY[f.severity]
    return max(0, round(sum(per_req.values()) / len(per_req)) - doc_penalty)


HIGH_RISK_HIGH_RULES = 5   # this many high-severity rule findings always means "High risk"


def grade(value: int, findings: list[Finding] | None = None) -> str:
    """Grade from the score thresholds, gated by high-severity rule findings (ADR-005).

    0 high rule findings  -> score thresholds only
    1-4                   -> at most "Needs work"
    5 or more             -> "High risk"
    AI advisory findings never affect the grade, like the score.
    """
    high_rules = sum(1 for f in findings or [] if f.source == "rule" and f.severity == "high")
    if high_rules >= HIGH_RISK_HIGH_RULES:
        return "High risk"
    if value >= 90 and high_rules == 0:
        return "Ready for review"
    if value >= 70:
        return "Needs work"
    return "High risk"


def fallback_summary(findings: list[Finding], requirements: list[Requirement]) -> str:
    high = sum(1 for f in findings if f.severity == "high")
    flagged = len({f.req_id for f in findings if f.req_id})
    return (f"{len(findings)} findings across {flagged} of {len(requirements)} requirements; "
            f"{high} are high severity and should be fixed first.")


class JudgeAgent(Agent):
    name = "judge"

    def validate(self, data: Any) -> list[str]:
        if not isinstance(data, dict) or not str(data.get("summary", "")).strip():
            return ['missing "summary"']
        return []

    def run(self, rule_findings: list[Finding], advice: list[dict],
            requirements: list[Requirement]) -> tuple[list[Finding], int, str, str, str | None]:
        findings = rank(merge(rule_findings, advice), requirements)
        value = score(findings, requirements)
        payload = {"score": value, "requirements": len(requirements),
                   "findings": [{"req_id": f.req_id, "agent": f.agent, "severity": f.severity,
                                 "problem": f.problem} for f in findings[:60]]}
        error = None
        try:
            summary = str(self.call(json.dumps(payload))["summary"]).strip()
        except AgentError as exc:
            summary, error = fallback_summary(findings, requirements), str(exc)
        return findings, value, grade(value, findings), summary, error
