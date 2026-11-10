"""Agents: JSON validation, one retry, hallucinated IDs, judge merge and score."""
import json

import pytest

from reqguard.agents import AgentError, ExtractorAgent, SecurityAgent, TestWriterAgent
from reqguard.agents.base import parse_json
from reqguard.agents.judge import grade, merge, rank, score
from reqguard.llm import LLMReply, MockLLM
from reqguard.models import Finding, Requirement


class ScriptedLLM:
    """Returns the given replies in order, so each test controls the model exactly."""
    name = "scripted"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.messages = []

    def complete(self, system, user, *, agent):
        self.messages.append(user)
        text = self.replies.pop(0)
        return LLMReply(text if isinstance(text, str) else json.dumps(text), 10, 5, "scripted")


REQS = [Requirement("REQ-01", "Passwords shall be stored.", 1),
        Requirement("REQ-02", "The system shall export reports as CSV files.", 2)]


def test_parse_json_strips_markdown_fences():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_agent_retries_once_then_succeeds():
    llm = ScriptedLLM("not json at all", {"requirements": [{"text": "Search shall be fast.", "line": 1}]})
    kept, _ = ExtractorAgent(llm).run("Search shall be fast.")
    assert [r.text for r in kept] == ["Search shall be fast."]
    assert len(llm.messages) == 2 and "rejected" in llm.messages[1]


def test_agent_gives_up_after_second_invalid_reply():
    llm = ScriptedLLM("nope", {"wrong_key": []})
    with pytest.raises(AgentError):
        ExtractorAgent(llm).run("Search shall be fast.")


def test_usage_is_counted():
    agent = ExtractorAgent(ScriptedLLM("bad", {"requirements": []}))
    agent.run("x")
    assert (agent.usage.calls, agent.usage.input_tokens, agent.usage.output_tokens) == (2, 20, 10)


def test_specialist_drops_findings_for_unknown_requirement_ids():
    llm = ScriptedLLM({"findings": [
        {"req_id": "REQ-99", "rule_id": None, "problem": "made up", "severity": "high"},
        {"req_id": "REQ-02", "rule_id": None, "problem": "CSV export has no access rule", "severity": "medium",
         "suggestion": "Only managers shall export reports as CSV files."}]})
    rules, advice, err = SecurityAgent(llm).review(REQS)
    assert err is None
    assert [f.rule_id for f in rules] == ["S1"]                 # rule finding from Python
    assert [a["req_id"] for a in advice] == ["REQ-02"]           # REQ-99 discarded


def test_specialist_keeps_rule_findings_when_ai_fails():
    rules, advice, err = SecurityAgent(MockLLM(fail_agents={"security"})).review(REQS)
    assert [f.rule_id for f in rules] == ["S1"] and advice == [] and "outage" in err


def test_specialist_rejects_bad_severity_then_retries():
    llm = ScriptedLLM({"findings": [{"req_id": "REQ-01", "problem": "x", "severity": "critical"}]},
                      {"findings": []})
    _, advice, err = SecurityAgent(llm).review(REQS)
    assert err is None and advice == [] and len(llm.messages) == 2


def test_test_writer_requires_given_when_then():
    llm = ScriptedLLM({"tests": [{"req_id": "REQ-02", "given": "a", "when": "b", "then": ""}]},
                      {"tests": [{"req_id": "REQ-02", "given": "a", "when": "b", "then": "a CSV file downloads"},
                                 {"req_id": "REQ-42", "given": "a", "when": "b", "then": "c"}]})
    tests = TestWriterAgent(llm).run([{"id": "REQ-02", "text": REQS[1].text}])
    assert [(t.req_id, t.then) for t in tests] == [("REQ-02", "a CSV file downloads")]


def test_merge_attaches_ai_rewrite_to_rule_finding():
    rule = Finding("REQ-01", "security", "rule", "high", "No hashing", rule_id="S1")
    advice = [{"req_id": "REQ-01", "rule_id": "S1", "problem": "same", "suggestion": "Hash them.",
               "severity": "low", "agent": "security", "related": []},
              {"req_id": "REQ-02", "rule_id": None, "problem": "No access rule", "suggestion": None,
               "severity": "medium", "agent": "security", "related": []}]
    merged = merge([rule], advice)
    assert len(merged) == 2
    assert merged[0].suggestion == "Hash them." and merged[0].severity == "high"   # rule severity wins
    assert merged[1].source == "ai"


def test_rank_orders_by_severity_and_assigns_ids():
    fs = [Finding("REQ-02", "functional", "rule", "low", "a", rule_id="R2"),
          Finding("REQ-01", "security", "rule", "high", "b", rule_id="S1")]
    ranked = rank(fs, REQS)
    assert [(f.id, f.severity) for f in ranked] == [("F-001", "high"), ("F-002", "low")]


def test_score_and_grade():
    """The score counts rule findings only (ADR-005)."""
    fs = [Finding("REQ-01", "security", "rule", "high", "b", rule_id="S1")]
    assert score(fs, REQS) == 85                      # (70 + 100) / 2
    assert score([], REQS) == 100
    assert score([Finding(None, "security", "rule", "high", "doc", rule_id="S4")], REQS) == 90
    ai_only = [Finding("REQ-02", "functional", "ai", "high", "AI-only problem"),
               Finding(None, "security", "ai", "high", "AI document-level problem")]
    assert score(ai_only, REQS) == 100                # AI advisory findings carry no penalty
    assert score(fs + ai_only, REQS) == 85
    assert score([], []) == 0
    assert (grade(90), grade(89), grade(70), grade(69)) == ("Ready for review", "Needs work", "Needs work", "High risk")


def test_score_never_negative():
    fs = [Finding("REQ-01", "security", "rule", "high", str(i), rule_id=f"X{i}") for i in range(10)]
    assert score(fs, REQS[:1]) == 0
