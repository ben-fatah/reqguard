"""Consistency specialist rule pack: C1 conflicting durations, C2 near-duplicates.

These rules compare requirements with each other, so they take the whole list.
"""
from __future__ import annotations

import re

from ..models import Finding, Requirement

AGENT = "consistency"

# Topics where two different time limits are a contradiction.
TOPICS = {
    "session": re.compile(r"\b(session|inactivity|log(?:ged)? ?out|timeout|time out)\b", re.IGNORECASE),
    "password reset": re.compile(r"\b(reset link|password[- ]reset)\b", re.IGNORECASE),
    "lockout": re.compile(r"\b(lock|locked|lockout)\b", re.IGNORECASE),
}
_DURATION = re.compile(r"(\d+(?:\.\d+)?)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?|days?)\b", re.IGNORECASE)
_UNIT_MIN = {"s": 1 / 60, "m": 1, "h": 60, "d": 1440}
_WORD = re.compile(r"[a-z0-9]+")
DUPLICATE_THRESHOLD = 0.85


def _minutes(value: str, unit: str) -> float:
    return float(value) * _UNIT_MIN[unit.lower()[0]]


def c1_conflicting_durations(requirements: list[Requirement]) -> list[Finding]:
    findings: list[Finding] = []
    for topic, pattern in TOPICS.items():
        timed = []
        for req in requirements:
            m = _DURATION.search(req.text)
            if m and pattern.search(req.text):
                timed.append((req, _minutes(m.group(1), m.group(2)), (m.start(), m.end())))
        if len({round(v, 4) for _, v, _ in timed}) < 2:
            continue
        for req, value, span in timed:
            others = [r.id for r, v, _ in timed if round(v, 4) != round(value, 4)]
            findings.append(Finding(req.id, AGENT, "rule", "high",
                                    f"Conflicting {topic} time limit with {', '.join(others)}.",
                                    rule_id="C1", span=span, related=others))
    return findings


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    return len(ta & tb) / len(ta | tb) if ta | tb else 0.0


def c2_near_duplicates(requirements: list[Requirement]) -> list[Finding]:
    findings: list[Finding] = []
    for i, a in enumerate(requirements):
        for b in requirements[i + 1:]:
            if jaccard(a.text, b.text) >= DUPLICATE_THRESHOLD:
                findings.append(Finding(b.id, AGENT, "rule", "low",
                                        f"Near-duplicate of {a.id}: merge them or explain the difference.",
                                        rule_id="C2", related=[a.id]))
    return findings


def check(requirements: list[Requirement]) -> list[Finding]:
    return c1_conflicting_durations(requirements) + c2_near_duplicates(requirements)
