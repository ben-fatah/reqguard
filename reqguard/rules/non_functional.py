"""Non-functional specialist rule pack: R1, R5."""
from __future__ import annotations

from ..models import Finding, Requirement
from .common import find_terms, has_number, joined, span_of

AGENT = "non_functional"

VAGUE_TERMS = [
    "as soon as possible", "user-friendly", "quickly", "quick", "fast", "easy", "easily",
    "efficient", "flexible", "robust", "intuitive", "seamless", "adequate", "reasonable",
    "acceptable", "highly", "many", "accurate", "securely", "simple", "scalable",
]
PERFORMANCE_TERMS = [
    "respond", "responds", "response", "load", "loads", "loading", "available", "availability",
    "performance", "concurrent", "latency", "uptime", "throughput",
]


def r1_vague_term(req: Requirement) -> list[Finding]:
    if has_number(req.text):
        return []
    hits = find_terms(req.text, VAGUE_TERMS)
    if not hits:
        return []
    return [Finding(req.id, AGENT, "rule", "medium",
                    f'Vague word "{joined(hits)}": replace it with a number and a unit.',
                    rule_id="R1", span=span_of(hits))]


def r5_unmeasured_quality(req: Requirement) -> list[Finding]:
    if has_number(req.text):
        return []
    hits = find_terms(req.text, PERFORMANCE_TERMS)
    if not hits:
        return []
    return [Finding(req.id, AGENT, "rule", "high",
                    "Performance or availability with no measurable value: add a target such as seconds, % or users.",
                    rule_id="R5", span=span_of(hits))]


RULES = [r1_vague_term, r5_unmeasured_quality]


def check(requirements: list[Requirement]) -> list[Finding]:
    return [f for req in requirements for rule in RULES for f in rule(req)]
