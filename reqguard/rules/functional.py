"""Functional specialist rule pack: R2, R3, R4, R6, F1.

Each rule takes one requirement and returns zero or more rule findings.
Rules flag *potential* problems for a human to decide; they never reject.
"""
from __future__ import annotations

import re

from ..models import Finding, Requirement
from .common import find_terms, joined, span_of

AGENT = "functional"

WEAK_MODALS = ["should", "may", "might", "could"]
OPEN_ENDED = ["and so on", "etc", "tbd", "tbc", "and/or", "including but not limited to"]
IRREGULAR_PARTICIPLES = [
    "kept", "shown", "sent", "given", "made", "done", "written", "taken", "held", "built",
    "set", "put", "read", "seen", "known", "paid", "sold", "told", "found", "chosen",
]
_PASSIVE = re.compile(
    r"\b(?:shall|must)\s+be\s+([a-z]+ed|" + "|".join(IRREGULAR_PARTICIPLES) + r")\b",
    re.IGNORECASE,
)
_HAS_ACTOR = re.compile(r"\bby\b", re.IGNORECASE)
_ACTION = re.compile(
    r"\b(?:shall|must)\s+(add|create|delete|remove|update|edit|upload|submit|register|book|save|import)\b",
    re.IGNORECASE,
)
_FAILURE_WORDS = re.compile(
    r"\b(if|when|unless|reject|rejects|error|errors|fail|fails|failed|invalid|already|duplicate|otherwise)\b",
    re.IGNORECASE,
)


def r2_weak_modal(req: Requirement) -> list[Finding]:
    hits = find_terms(req.text, WEAK_MODALS)
    if not hits:
        return []
    return [Finding(req.id, AGENT, "rule", "low",
                    f'Weak word "{joined(hits)}": say "shall" if it is required.',
                    rule_id="R2", span=span_of(hits))]


def r3_open_ended(req: Requirement) -> list[Finding]:
    hits = find_terms(req.text, OPEN_ENDED)
    if not hits:
        return []
    return [Finding(req.id, AGENT, "rule", "medium",
                    f'Open-ended wording "{joined(hits)}": list every item.',
                    rule_id="R3", span=span_of(hits))]


def r4_compound(req: Requirement) -> list[Finding]:
    hits = find_terms(req.text, ["shall", "must"])
    if len(hits) < 2:
        return []
    return [Finding(req.id, AGENT, "rule", "low",
                    "Two requirements in one sentence: split them so each can be tested and traced.",
                    rule_id="R4", span=(hits[1][0], hits[1][1]))]


def r6_passive_no_actor(req: Requirement) -> list[Finding]:
    m = _PASSIVE.search(req.text)
    if not m or _HAS_ACTOR.search(req.text):
        return []
    return [Finding(req.id, AGENT, "rule", "medium",
                    f'Passive "{m.group(0)}" with no actor: say who or what does it.',
                    rule_id="R6", span=(m.start(), m.end()))]


def f1_no_failure_path(req: Requirement) -> list[Finding]:
    m = _ACTION.search(req.text)
    if not m or _FAILURE_WORDS.search(req.text):
        return []
    return [Finding(req.id, AGENT, "rule", "medium",
                    "No failure path: what happens if the action fails or the item already exists?",
                    rule_id="F1", span=(m.start(), m.end()))]


RULES = [r2_weak_modal, r3_open_ended, r4_compound, r6_passive_no_actor, f1_no_failure_path]


def check(requirements: list[Requirement]) -> list[Finding]:
    return [f for req in requirements for rule in RULES for f in rule(req)]
