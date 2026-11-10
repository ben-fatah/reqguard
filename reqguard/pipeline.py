"""Orchestrator: runs the agent team in a fixed order. No agent chooses the next step.

    idea? -> Idea-to-SRS -> Extractor -> grounding -> 4 specialists (parallel) -> Judge
                                                     -> human review -> Test-writer
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .agents import (SPECIALISTS, AgentError, ExtractorAgent, IdeaToSRSAgent, JudgeAgent,
                     TestWriterAgent)
from .llm import LLMClient, get_client
from .models import RunResult, TestCase, Usage

MAX_DOCUMENT_BYTES = 200_000
# The rule word lists are English (charter NG-6). A document whose letters are mostly not
# Latin would get no rule findings and a perfect score, so it is refused instead.
MIN_LATIN_LETTER_SHARE = 0.8


class PipelineError(RuntimeError):
    """A stage failed and the run cannot continue (for example extraction failed)."""


def latin_letter_share(text: str) -> float:
    """Share of the letters in `text` that are ASCII a-z / A-Z (1.0 if there are no letters)."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 1.0
    return sum(c.isascii() for c in letters) / len(letters)


def require_english(text: str) -> None:
    if latin_letter_share(text) < MIN_LATIN_LETTER_SHARE:
        raise PipelineError("ReqGuard reviews English requirements only: the document is mostly "
                            "in another language or script. Translate it to English and try again.")


class Orchestrator:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or get_client()

    def _begin_run(self) -> None:
        """Let a client refresh per-run state (DevAI reads its current global model once per run)."""
        begin = getattr(self.llm, "begin_run", None)
        if callable(begin):
            begin()

    def review(self, *, text: str | None = None, idea: str | None = None) -> RunResult:
        if bool(text and text.strip()) == bool(idea and idea.strip()):
            raise PipelineError("Give either an SRS text or an idea, not both and not neither.")
        self._begin_run()
        usage: dict[str, Usage] = {}
        errors: list[str] = []

        def u(name: str) -> Usage:
            return usage.setdefault(name, Usage(agent=name))

        source_type = "idea" if idea and idea.strip() else "srs"
        if source_type == "idea":
            try:
                text = IdeaToSRSAgent(self.llm, u("idea_to_srs")).run(idea.strip())
            except AgentError as exc:
                raise PipelineError(f"Idea-to-SRS failed: {exc}") from exc
        assert text is not None
        if len(text.encode("utf-8")) > MAX_DOCUMENT_BYTES:
            raise PipelineError("The document is larger than 200 KB.")
        require_english(text)

        try:
            requirements, dropped = ExtractorAgent(self.llm, u("extractor")).run(text)
        except AgentError as exc:
            raise PipelineError(f"Extraction failed: {exc}") from exc
        if not requirements:
            raise PipelineError("No requirements were found in the document.")

        agents = [cls(self.llm, u(cls.name)) for cls in SPECIALISTS]
        with ThreadPoolExecutor(max_workers=len(agents)) as pool:
            results = list(pool.map(lambda a: a.review(requirements), agents))
        rule_findings, advice = [], []
        for agent, (rules, adv, err) in zip(agents, results):
            rule_findings += rules
            advice += adv
            if err:
                errors.append(f"{agent.name}: AI advice unavailable, rule findings kept ({err})")

        findings, value, grade, summary, err = JudgeAgent(self.llm, u("judge")).run(rule_findings, advice,
                                                                                   requirements)
        if err:
            errors.append(f"judge: summary generated without AI ({err})")

        return RunResult(source_type=source_type, source_text=text, requirements=requirements,
                         dropped=dropped, findings=findings, score=value, grade=grade, summary=summary,
                         usage=list(usage.values()), errors=errors)

    def write_tests(self, requirements: list[dict]) -> tuple[list[TestCase], Usage]:
        self._begin_run()
        usage = Usage(agent="test_writer")
        try:
            tests = TestWriterAgent(self.llm, usage).run(requirements)
        except AgentError as exc:
            raise PipelineError(f"Test-writer failed: {exc}") from exc
        return tests, usage
