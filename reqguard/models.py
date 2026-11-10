"""Plain data objects shared by every layer. No I/O here."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Severity = Literal["high", "medium", "low"]
Source = Literal["rule", "ai"]
Kind = Literal["functional", "non_functional"]

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
AGENTS = ("functional", "non_functional", "security", "consistency")


@dataclass
class Requirement:
    id: str          # REQ-01
    text: str        # exact text, verified against the source (FR-03)
    line: int        # 1-based line where the text starts
    kind: Kind = "functional"


@dataclass
class Finding:
    req_id: str | None        # None = document-level finding
    agent: str                # functional | non_functional | security | consistency
    source: Source            # rule | ai
    severity: Severity
    problem: str
    rule_id: str | None = None
    suggestion: str | None = None   # AI rewrite, attached by the judge
    span: tuple[int, int] | None = None
    related: list[str] = field(default_factory=list)
    id: str = ""              # assigned by the judge: F-001 ...

    def key(self) -> tuple:
        return (self.req_id, self.rule_id or self.problem.strip().lower())


@dataclass
class TestCase:
    __test__ = False   # not a pytest test class
    req_id: str
    given: str
    when: str
    then: str
    id: str = ""


@dataclass
class Usage:
    agent: str
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""   # model that answered (LLMReply.model), shown in the UI and the report


@dataclass
class RunResult:
    source_type: Literal["srs", "idea"]
    source_text: str
    requirements: list[Requirement]
    dropped: list[dict]
    findings: list[Finding]
    score: int
    grade: str
    summary: str
    usage: list[Usage]
    errors: list[str]

    def to_dict(self) -> dict:
        return asdict(self)
